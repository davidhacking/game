"""
V3 预测+交易: 读取持仓 → 模型预测 → 输出买卖建议 → (可选)执行交易

执行顺序 (--execute 模式):
  1. 预测所有标的 → 确定哪些要卖, 哪些要买 (建议模式)
  2. 执行所有卖出
  3. 重新拉取账户信息 → 获取真实现金 (不依赖预估)
  4. 用真实现金重新计算买入量
  5. 执行买入
"""
import argparse, sys, json
sys.path.insert(0, '/home/david/MF/trade_a50_v2')
from scripts.core import *
from scripts.core import ensemble_predict
from scripts.core import pred_to_position
from scripts.config import BUY_LIST, SELL_THRESHOLD_PERCENTILE, HORIZON_WEIGHTS, POSITION_SPEED, MIN_REBALANCE


def _code_to_futu(code):
    """纯数字 → FutuOpenD: 600000→SH.600000, 000100→SZ.000100"""
    code = str(code).strip()
    if code.startswith('6'):
        return 'SH.' + code
    elif code.startswith('0') or code.startswith('3'):
        return 'SZ.' + code
    return 'SH.' + code


def _futu_to_num(futu_code):
    return futu_code.split('.')[-1] if '.' in futu_code else futu_code


def _predict_stock(model, feat_cols, futu_code):
    """预测单只股票, 返回 (smoothed_pred, price, date_str) or (None,None,None)"""
    try:
        df = load_data(futu_code, start='2015-01-01')
        if len(df) < 130:
            return None, None, None
        df = build_features(df)
        c = df['close']
        for days in HORIZON_WEIGHTS:
            df['ret_%dd_fwd' % days] = c.shift(-days) / c - 1
        df['fused_target'] = sum(w * df['ret_%dd_fwd' % d] for d, w in HORIZON_WEIGHTS.items())
        df = df.dropna(subset=feat_cols)
        if len(df) < 5:
            return None, None, None
        recent = df.tail(5)
        X = recent[feat_cols].values
        preds = ensemble_predict(model, X)
        return float(np.mean(preds)), float(df.iloc[-1]['close']), df.iloc[-1]['date'].strftime('%Y-%m-%d')
    except Exception as e:
        print('  [WARN] %s predict failed: %s' % (futu_code, e))
        return None, None, None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--portfolio', help='JSON file')
    p.add_argument('--execute', action='store_true', help='自动执行交易')
    args = p.parse_args()

    # ── 读取持仓 ──
    if args.portfolio:
        with open(args.portfolio) as f: data = json.load(f)
    elif not sys.stdin.isatty():
        data = json.load(sys.stdin)
    else:
        print('Usage: echo \'{"balance":1000000,"position":{}}\' | python scripts/predict.py')
        sys.exit(1)

    cash = float(data.get('balance', 0))
    pos_info = data.get('position', {})

    # ── 加载模型 ──
    model, meta = load_model()
    feat_cols = meta['feature_cols']
    pred_stats = meta.get('pred_stats', {})
    if not pred_stats:
        print('  ERROR: No pred_stats. Re-train with V3!'); sys.exit(1)

    sell_threshold = pred_stats.get(SELL_THRESHOLD_PERCENTILE, pred_stats.get('p25', 0))
    buy_list_nums = [_futu_to_num(c) for c in BUY_LIST]

    # ── 分类持仓 ──
    buy_positions = {}
    other_positions = {}
    for code, info in pos_info.items():
        if any(bl in code for bl in buy_list_nums):
            buy_positions[code] = info
        else:
            other_positions[code] = info

    total_pos_value = sum(info.get('value', 0) for info in pos_info.values())
    total_asset = cash + total_pos_value

    sells = []   # (code, futu_code, shares, amount, pred, price, reason)
    buys = []    # (code, futu_code, shares, amount, pred, price)
    holds = []   # (code, futu_code, shares, amount, pred, price)
    skips = []   # (code, futu_code, shares, amount)

    # ══════════════════════════════════════════════════
    # Step 1: BUY_LIST 标的 — 预测, 需要减仓的先卖
    # ══════════════════════════════════════════════════
    buy_list_predictions = {}  # futu_code -> (smoothed, price, target_pos, etf_shares)

    for futu_code in BUY_LIST:
        etf_num = _futu_to_num(futu_code)
        etf_shares = 0; etf_cost = 0
        for code, info in buy_positions.items():
            if etf_num in code:
                etf_shares = info.get('quantity', 0)
                etf_cost = info.get('price', 0)

        smoothed, price, ds = _predict_stock(model, feat_cols, futu_code)
        if smoothed is None:
            print('  [WARN] %s: predict failed' % futu_code)
            continue

        pos_value = etf_shares * price
        current_pos = pos_value / total_asset if total_asset > 0 else 0
        target_pos = pred_to_position(smoothed, pred_stats)
        buy_list_predictions[futu_code] = (smoothed, price, target_pos, etf_shares)

        diff = target_pos - current_pos
        step = diff * POSITION_SPEED
        if step < -MIN_REBALANCE:
            # 需要减仓 → 渐进卖出
            sell_shares = min(int(abs(step) * total_asset / price / LOT_SIZE) * LOT_SIZE, etf_shares)
            if sell_shares > 0:
                sell_amount = sell_shares * price
                sells.append((etf_num, futu_code, sell_shares, sell_amount, smoothed, price, '仓位调整'))
                cash += sell_amount * (1 - SELL_COST)  # 回笼资金

    # ══════════════════════════════════════════════════
    # Step 2: 其他持仓 — 预测跌的卖出
    # ══════════════════════════════════════════════════
    for code, info in other_positions.items():
        qty = info.get('quantity', 0)
        if qty <= 0:
            continue

        futu_code = _code_to_futu(code)
        smoothed, price, ds = _predict_stock(model, feat_cols, futu_code)

        if smoothed is None:
            skips.append((code, futu_code, qty, info.get('value', 0)))
            continue

        cur_price = price if price > 0 else info.get('price', 0)
        value = qty * cur_price

        if smoothed < sell_threshold:
            sells.append((code, futu_code, qty, value, smoothed, cur_price, '模型预测跌'))
            cash += value * (1 - SELL_COST)  # 回笼资金
        else:
            holds.append((code, futu_code, qty, value, smoothed, cur_price))

    # ══════════════════════════════════════════════════
    # Step 3: BUY_LIST 标的 — 用实际可用现金买入
    # ══════════════════════════════════════════════════
    for futu_code in BUY_LIST:
        if futu_code not in buy_list_predictions:
            continue
        smoothed, price, target_pos, etf_shares = buy_list_predictions[futu_code]
        etf_num = _futu_to_num(futu_code)

        # 重新计算: 卖出后的总资产和当前仓位
        # 当前持仓可能已被 Step 1 减仓
        sold_shares = sum(s[2] for s in sells if s[0] == etf_num)
        actual_shares = etf_shares - sold_shares
        actual_pos_value = actual_shares * price
        actual_total = cash + actual_pos_value + sum(
            h[3] for h in holds) + sum(
            s[3] for s in skips)
        current_pos = actual_pos_value / actual_total if actual_total > 0 else 0

        diff = target_pos - current_pos
        step = diff * POSITION_SPEED
        if step > MIN_REBALANCE:
            buy_shares = int(step * actual_total / price / LOT_SIZE) * LOT_SIZE
            buy_amount = buy_shares * price * (1 + BUY_COST)
            # 确保不超过可用现金
            while buy_amount > cash and buy_shares >= LOT_SIZE:
                buy_shares -= LOT_SIZE
                buy_amount = buy_shares * price * (1 + BUY_COST)
            if buy_shares > 0:
                buys.append((etf_num, futu_code, buy_shares, buy_shares * price, smoothed, price))
                cash -= buy_amount
        elif step >= -MIN_REBALANCE:
            # 不需要买也不需要卖 → HOLD
            holds.append((etf_num, futu_code, actual_shares, actual_pos_value, smoothed, price))

    # ══════════════════════════════════════════════════
    # 输出报告
    # ══════════════════════════════════════════════════
    print()
    print('═' * 62)
    print('  交易建议 | 总资产: %s  现金: %s' % (
        '{:,.0f}'.format(total_asset), '{:,.0f}'.format(data.get('balance', 0))))
    print('═' * 62)

    if sells:
        print()
        print('  ── 卖出 (先执行) ──')
        for code, futu, shares, amount, pred, price, reason in sells:
            pred_str = '%+.3f%%' % (pred * 100) if pred is not None else '?'
            print('  [SELL] %s  %6d股  ¥%10s  价格%.3f  pred=%s  (%s)' % (
                code.ljust(8), shares, '{:,.0f}'.format(amount), price, pred_str, reason))
        sell_total = sum(s[3] for s in sells)
        print('  ── 卖出合计: ¥%s (回笼资金)' % '{:,.0f}'.format(sell_total))

    if buys:
        print()
        print('  ── 买入 (卖出后执行) ──')
        for code, futu, shares, amount, pred, price in buys:
            pred_str = '%+.3f%%' % (pred * 100) if pred is not None else '?'
            print('  [BUY]  %s  %6d份  ¥%10s  价格%.3f  pred=%s' % (
                code.ljust(8), shares, '{:,.0f}'.format(amount), price, pred_str))

    if holds:
        print()
        print('  ── 持有 ──')
        for code, futu, shares, amount, pred, price in holds:
            pred_str = '%+.3f%%' % (pred * 100) if pred is not None else '?'
            print('  [HOLD] %s  %6d股  ¥%10s  pred=%s' % (
                code.ljust(8), shares, '{:,.0f}'.format(amount), pred_str))

    if skips:
        print()
        print('  ── 跳过 (数据不足) ──')
        for code, futu, shares, amount in skips:
            print('  [SKIP] %s  %6d股  ¥%10s' % (code.ljust(8), shares, '{:,.0f}'.format(amount)))

    print()
    print('  卖出阈值: pred < %s (%.4f)' % (SELL_THRESHOLD_PERCENTILE, sell_threshold))
    print('  预计剩余现金: ¥%s' % '{:,.0f}'.format(cash))
    print('═' * 62)

    # ── 保存 JSON ──
    output = {
        'total_asset': round(total_asset, 2),
        'cash_before': round(data.get('balance', 0), 2),
        'cash_after': round(cash, 2),
        'sells': [{'code': s[0], 'shares': s[2], 'amount': round(s[3], 2), 'pred': round(s[4], 6) if s[4] else None, 'price': round(s[5], 3), 'reason': s[6]} for s in sells],
        'buys': [{'code': b[0], 'shares': b[2], 'amount': round(b[3], 2), 'pred': round(b[4], 6) if b[4] else None, 'price': round(b[5], 3)} for b in buys],
        'holds': [{'code': h[0], 'shares': h[2], 'pred': round(h[4], 6) if h[4] else None} for h in holds],
    }
    json_path = os.path.join(RESULT_DIR, 'predict_latest.json')
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print('  Output: %s' % json_path)

    # ══════════════════════════════════════════════════
    # --execute: 执行交易
    #   1. 执行卖出
    #   2. 重新拉取账户 (获取真实现金)
    #   3. 用真实现金重新预测买入
    #   4. 执行买入
    # ══════════════════════════════════════════════════
    if args.execute and (buys or sells):
        print()
        print('  执行交易...')
        from win_ctrl.ths_trader import buy_stock, sell_stock, get_account_info
        import time

        # ── Step 1: 执行所有卖出 ──
        if sells:
            print()
            print('  ── Step 1: 执行卖出 ──')
            for code, futu, shares, amount, pred, price, reason in sells:
                print('  → SELL %s %d股 @%.3f (%s)' % (code, shares, price, reason))
                sell_stock(code, price, shares)
            print('  卖出完成, 等待3秒...')
            time.sleep(3)

        # ── Step 2: 重新拉取账户信息 (真实现金) ──
        print()
        print('  ── Step 2: 重新拉取账户信息 ──')
        try:
            real_account = get_account_info()
            real_cash = float(real_account.get('balance', 0))
            real_pos = real_account.get('position', {})
            print('  真实现金: ¥%s (预估: ¥%s)' % (
                '{:,.0f}'.format(real_cash), '{:,.0f}'.format(cash)))

            # 保存卖出后的账户快照
            snapshot_path = os.path.join(RESULT_DIR, 'account_after_sell.json')
            with open(snapshot_path, 'w') as f:
                json.dump(real_account, f, indent=2, ensure_ascii=False)
            print('  账户快照: %s' % snapshot_path)
        except Exception as e:
            print('  [WARN] 拉取账户失败: %s, 用预估现金继续' % e)
            real_cash = cash
            real_pos = pos_info

        # ── Step 3: 用真实现金重新预测买入 ──
        if buys:
            print()
            print('  ── Step 3: 用真实现金重新计算买入 ──')
            new_buys = []
            for futu_code in BUY_LIST:
                if futu_code not in buy_list_predictions:
                    continue
                smoothed, price, target_pos, _ = buy_list_predictions[futu_code]
                etf_num = _futu_to_num(futu_code)

                # 从真实持仓中获取当前持股数
                real_etf_shares = 0
                for rcode, rinfo in real_pos.items():
                    if etf_num in rcode:
                        real_etf_shares = rinfo.get('quantity', 0)

                # 用真实数据计算
                real_pos_value = real_etf_shares * price
                real_total = real_cash + sum(v.get('value', 0) for v in real_pos.values())
                current_pos = real_pos_value / real_total if real_total > 0 else 0

                diff = target_pos - current_pos
                step = diff * POSITION_SPEED
                if step > MIN_REBALANCE:
                    buy_shares = int(step * real_total / price / LOT_SIZE) * LOT_SIZE
                    buy_amount = buy_shares * price * (1 + BUY_COST)
                    while buy_amount > real_cash and buy_shares >= LOT_SIZE:
                        buy_shares -= LOT_SIZE
                        buy_amount = buy_shares * price * (1 + BUY_COST)
                    if buy_shares > 0:
                        new_buys.append((etf_num, futu_code, buy_shares, buy_shares * price, smoothed, price))
                        real_cash -= buy_amount
                        print('  重新计算: BUY %s %d份 @%.3f (真实现金)' % (etf_num, buy_shares, price))

            # ── Step 4: 执行买入 ──
            if new_buys:
                print()
                print('  ── Step 4: 执行买入 ──')
                for code, futu, shares, amount, pred, price in new_buys:
                    print('  → BUY  %s %d份 @%.3f' % (code, shares, price))
                    buy_stock(code, price, shares)

        print()
        print('  交易执行完毕')

    print()


if __name__ == '__main__':
    main()
