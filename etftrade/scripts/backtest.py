"""回测: 加载模型, 策略交易, 与 588000 Buy&Hold 对比"""
import sys
sys.path.insert(0, '/home/david/MF/trade_a50_v2')
from scripts.core import *
from scripts.core import ensemble_predict
from scripts.core import pred_to_position
from scripts.config import HORIZON_WEIGHTS, POSITION_SPEED, MIN_REBALANCE
import unicodedata


def fmt_pct(v, sign=True):
    return ('%+.2f%%' % v) if sign else ('%.2f%%' % v)

def fmt_money(v):
    return '{:,.0f}'.format(v)


def print_table(headers, rows, col_widths):
    def _dw(s):
        w = 0
        for c in str(s):
            if unicodedata.east_asian_width(c) in ('W', 'F'):
                w += 2
            else:
                w += 1
        return w
    def _center(s, w):
        s = str(s); d = _dw(s); left = (w - d) // 2; right = w - d - left
        return ' ' * left + s + ' ' * right
    def _right(s, w):
        s = str(s); d = _dw(s)
        return ' ' * (w - d - 1) + s + ' '
    def _line(l, m, r, f='─'):
        return l + m.join(f * w for w in col_widths) + r
    print(_line('┌', '┬', '┐'))
    print('│' + '│'.join(_center(h, w) for h, w in zip(headers, col_widths)) + '│')
    print(_line('├', '┼', '┤'))
    for row in rows:
        print('│' + '│'.join(_right(c, w) for c, w in zip(row, col_widths)) + '│')
    print(_line('└', '┴', '┘'))


def main(start_date=None, etf_code_override=None, initial_cash=None):
    model, meta = load_model()
    sd = start_date if start_date else meta['split_date']
    fc = meta['feature_cols']
    etf_code = etf_code_override if etf_code_override else meta.get('etf_code', DEFAULT_ETF)
    pred_stats = meta.get('pred_stats', {})

    if not pred_stats:
        print('  ERROR: No pred_stats in meta.json. Re-train with V3!')
        sys.exit(1)

    # 加载 ETF 数据
    df = load_data(etf_code, start='2015-01-01')
    df = build_features(df)
    c = df['close']
    hw = {int(k): v for k, v in meta.get('horizon_weights', HORIZON_WEIGHTS).items()}
    for days in hw:
        df['ret_%dd_fwd' % days] = c.shift(-days) / c - 1
    df['fused_target'] = sum(w * df['ret_%dd_fwd' % d] for d, w in hw.items())
    df = df.dropna(subset=fc)
    test = df[df['date'] >= sd].reset_index(drop=True)

    # ---- 策略回测 ----
    init_cash = float(initial_cash) if initial_cash else float(INITIAL_CASH)
    cash = init_cash; shares = 0; cp = 0; daily = []
    n_trades = 0; total_turnover = 0; trade_log = []
    pred_history = []

    for i, row in test.iterrows():
        p = row['close']; tv = cash + shares * p; cur = (shares * p / tv) if tv > 0 else 0

        X = row[fc].values.reshape(1, -1)
        pred_ret = ensemble_predict(model, X)[0]
        pred_history.append(pred_ret)
        if len(pred_history) > 5:
            pred_history.pop(0)
        smoothed = np.mean(pred_history)

        tgt = pred_to_position(smoothed, pred_stats)
        # 渐进调仓: 每天只走差距的 POSITION_SPEED (30%)
        step = (tgt - cur) * POSITION_SPEED
        actual_tgt = cur + step
        d = actual_tgt - cur

        if d > MIN_REBALANCE:
            bs = int(d * tv / p / LOT_SIZE) * LOT_SIZE
            if bs > 0:
                c = bs * p * (1 + BUY_COST)
                if c <= cash:
                    cp = (cp * shares + p * bs) / (shares + bs) if shares > 0 else p
                    cash -= c; shares += bs; n_trades += 1; total_turnover += bs
                    trade_log.append({'date': row['date'].strftime('%Y-%m-%d'), 'action': 'BUY', 'shares': bs, 'price': p, 'amount': round(c, 0), 'pos_after': round((shares * p / (cash + shares * p)) * 100, 1)})
        elif d < -MIN_REBALANCE:
            ss = min(int(abs(d) * tv / p / LOT_SIZE) * LOT_SIZE, shares)
            if ss > 0:
                recv = ss * p * (1 - SELL_COST)
                cash += recv; shares -= ss
                if shares == 0: cp = 0
                n_trades += 1; total_turnover += ss
                trade_log.append({'date': row['date'].strftime('%Y-%m-%d'), 'action': 'SELL', 'shares': ss, 'price': p, 'amount': round(recv, 0), 'pos_after': round((shares * p / (cash + shares * p)) * 100, 1) if (cash + shares * p) > 0 else 0})
        tv2 = cash + shares * p
        daily.append({'date': row['date'], 'value': tv2, 'price': p, 'pred_ret': pred_ret, 'smoothed': smoothed, 'target_pos': tgt, 'actual_tgt': actual_tgt,
                     'pos': (shares * p / tv2) if tv2 > 0 else 0})

    ddf = pd.DataFrame(daily).set_index('date')
    nav = ddf['value'] / init_cash
    rets = nav.pct_change().dropna()
    n_days = len(rets)

    s_ret = (nav.iloc[-1] - 1) * 100
    s_sharpe = (rets.mean() * 252 - 0.03) / (rets.std() * np.sqrt(252)) if rets.std() > 0 else 0
    pk = nav.expanding().max(); dd = (nav - pk) / pk; s_mdd = dd.min() * 100
    s_vol = rets.std() * np.sqrt(252) * 100
    s_final = ddf['value'].iloc[-1]
    avg_pos = ddf['pos'].mean() * 100
    avg_turnover = total_turnover / max(n_days, 1)

    # 基线: Buy&Hold 同一只 ETF
    bench_nav = test['close'] / test['close'].iloc[0]
    bench_nav.index = test['date']
    b_rets = bench_nav.pct_change().dropna()
    b_ret = (bench_nav.iloc[-1] - 1) * 100
    b_sharpe = (b_rets.mean() * 252 - 0.03) / (b_rets.std() * np.sqrt(252)) if b_rets.std() > 0 else 0
    b_pk = bench_nav.expanding().max(); b_mdd = ((bench_nav - b_pk) / b_pk).min() * 100
    b_vol = b_rets.std() * np.sqrt(252) * 100
    b_final = init_cash * bench_nav.iloc[-1]

    etf_name = etf_code.replace('SH.', '').replace('SZ.', '')

    # ══════ 主报告 ══════
    print()
    print('══════════════════════════════════════════════════════')
    print('  ETF %s 回测报告 (%s~)' % (etf_name, sd))
    print('══════════════════════════════════════════════════════')
    cw = [12, 14, 16, 10]
    print_table(
        ['指标', '策略', '基准(Buy&Hold)', '超额'],
        [
            ['收益率', fmt_pct(s_ret), fmt_pct(b_ret), fmt_pct(s_ret - b_ret)],
            ['夏普比率', '%.2f' % s_sharpe, '%.2f' % b_sharpe, '%+.2f' % (s_sharpe - b_sharpe)],
            ['最大回撤', fmt_pct(s_mdd, False), fmt_pct(b_mdd, False), fmt_pct(s_mdd - b_mdd)],
            ['年化波动率', fmt_pct(s_vol, False), fmt_pct(b_vol, False), ''],
            ['交易次数', '%d' % n_trades, '—', ''],
            ['日均换手', '%d 份' % avg_turnover, '—', ''],
            ['平均仓位', '%.0f%%' % avg_pos, '100%', ''],
            ['期末资产', fmt_money(s_final), fmt_money(b_final), ''],
        ],
        col_widths=cw,
    )

    # ══════ 月度 ══════
    common = nav.index.intersection(bench_nav.index)
    nav_c = nav.loc[common]; bn_c = bench_nav.loc[common]
    s_mo = nav_c.resample('ME').last().pct_change().dropna() * 100
    b_mo = bn_c.resample('ME').last().pct_change().dropna() * 100
    cm = s_mo.index.intersection(b_mo.index)
    if len(cm) > 0:
        print()
        print('──────────────────────────────────────────────────────')
        print('  月度收益对比')
        print('──────────────────────────────────────────────────────')
        rows = []
        for m in cm:
            sr = s_mo.loc[m]; br = b_mo.loc[m]
            rows.append([m.strftime('%Y-%m'), fmt_pct(sr), fmt_pct(br), fmt_pct(sr - br)])
        print_table(['月份', '策略', '基准', '超额'], rows, col_widths=[10, 12, 12, 10])

    # ══════ 季度 ══════
    s_q = nav_c.resample('QE').last().pct_change().dropna() * 100
    b_q = bn_c.resample('QE').last().pct_change().dropna() * 100
    cq = s_q.index.intersection(b_q.index)
    if len(cq) > 0:
        print()
        print('──────────────────────────────────────────────────────')
        print('  季度收益对比')
        print('──────────────────────────────────────────────────────')
        rows = []
        for q in cq:
            sr = s_q.loc[q]; br = b_q.loc[q]
            rows.append(['%dQ%d' % (q.year, q.quarter), fmt_pct(sr), fmt_pct(br), fmt_pct(sr - br)])
        print_table(['季度', '策略', '基准', '超额'], rows, col_widths=[10, 12, 12, 10])

    # ══════ 交易明细 ══════
    if trade_log:
        print()
        print('──────────────────────────────────────────────────────')
        print('  交易明细')
        print('──────────────────────────────────────────────────────')
        t_rows = []
        for t in trade_log:
            t_rows.append([
                t['date'],
                t['action'],
                '{:,}'.format(t['shares']),
                '%.3f' % t['price'],
                '{:,.0f}'.format(t['amount']),
                '%.1f%%' % t['pos_after'],
            ])
        print_table(
            ['日期', '方向', '数量(份)', '价格', '金额', '仓位'],
            t_rows,
            col_widths=[12, 8, 12, 10, 12, 8],
        )

    print()
    print('══════════════════════════════════════════════════════')

    # ══════ 保存回测数据 ══════
    daily_csv_path = os.path.join(RESULT_DIR, 'backtest_daily.csv')
    pd.DataFrame(daily).to_csv(daily_csv_path, index=False)
    print('  Daily: %s' % daily_csv_path)

    if trade_log:
        import json
        trades_json_path = os.path.join(RESULT_DIR, 'backtest_trades.json')
        with open(trades_json_path, 'w') as f:
            json.dump(trade_log, f, indent=2, ensure_ascii=False)
        print('  Trades: %s' % trades_json_path)



if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--start_date', default='20250101', help='回测起始日期, 默认 20250101')
    p.add_argument('--etf', default='SH.588000', help='ETF代码, 默认 SH.588000')
    p.add_argument('--cash', type=float, default=1000000, help='初始资金, 默认 1000000')
    args = p.parse_args()
    sd_arg = '%s-%s-%s' % (args.start_date[:4], args.start_date[4:6], args.start_date[6:])
    main(sd_arg, args.etf, args.cash)
