#!/usr/bin/env python3
"""
预测脚本：加载训练好的模型，输出当前的买/卖/持有列表
用法：
    python predict.py
    python predict.py --model SAC
    python predict.py --model PPO --no-update
    python predict.py --models SAC PPO  # 多模型投票
    python predict.py --output json     # 以 JSON 格式输出

输出说明：
    基于最新一天的行情数据 + 全仓现金状态（默认初始资金 1,000,000）构建 observation，
    模型预测 action（范围 -1~1），转换为实际交易股数后输出买卖列表。
    注意：这里不连接真实券商账户，持仓全部假设为 0（全现金状态），
    仅用于判断模型对当前行情的看法（哪些股应买入/卖出）。
"""

import os
import sys
import argparse
import json
from datetime import datetime, timedelta

# 将当前目录添加到 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def parse_args():
    parser = argparse.ArgumentParser(description="预测当前买卖列表")
    parser.add_argument(
        "--model",
        type=str,
        default="SAC",
        help="指定单个模型（A2C/PPO/DDPG/TD3/SAC），默认 SAC",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="指定多个模型进行投票，如 --models SAC PPO TD3",
    )
    parser.add_argument(
        "--no-update",
        action="store_true",
        help="跳过数据更新，直接使用已有数据",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="数据目录，默认 tests/stock_data",
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default=None,
        help="模型目录，默认 tests/models",
    )
    parser.add_argument(
        "--initial-amount",
        type=float,
        default=1_000_000,
        help="初始资金（用于构建 observation），默认 1,000,000",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2009-01-01",
        help="数据起始日期，默认 2009-01-01",
    )
    parser.add_argument(
        "--split-days",
        type=int,
        default=365,
        help="测试集天数，默认 365",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["table", "json"],
        default="table",
        help="输出格式：table（默认）或 json",
    )
    return parser.parse_args()


def load_and_predict(model_name: str, test_data, model_dir: str, initial_amount: float):
    """
    加载模型并预测当前动作

    Returns:
        dict: {
            'buy':  [(code, shares, price), ...],
            'sell': [(code, shares, price), ...],
            'hold': [code, ...],
            'raw_action': np.ndarray,
        }
    """
    import numpy as np
    from environments.env import StockLearningEnv
    from rl_agent.stock_agent import StockAgent
    from rl_agent.rl_agent import RLAgentParam
    from config import get_env_params
    from config.env_params import INFORMATION_COLS

    model_path = os.path.join(model_dir, f"{model_name.lower()}_stock_agent")
    if not os.path.exists(model_path + ".zip"):
        raise FileNotFoundError(
            f"模型文件不存在: {model_path}.zip\n"
            f"请先运行 train.py 训练模型"
        )

    # ---------- 构建环境（仅用于加载模型） ----------
    env_params = get_env_params(
        print_verbosity=100,
        random_start=False,
        initial_amount=initial_amount,
    )
    env = StockLearningEnv(df=test_data, **env_params)
    sb_env, _ = env.get_sb_env()

    # ---------- 加载模型 ----------
    agent_param = RLAgentParam(
        model_name=model_name,
        policy="MlpPolicy",
        model_path=model_path,
    )
    agent = StockAgent(env=sb_env, param=agent_param)
    agent.load()

    # ---------- 构建 observation ----------
    # observation = [balance] + [holdings * n_stocks] + [technical_features * n_stocks]
    stock_col = "tic"
    assets = test_data[stock_col].unique().tolist()
    n_stocks = len(assets)

    # 全现金状态：余额 = initial_amount，持仓全为 0
    balance = initial_amount
    holdings = np.zeros(n_stocks, dtype=np.float32)

    # 获取最新一天的价格 + 技术指标
    latest_date = test_data["date"].max()
    latest_data = test_data[test_data["date"] == latest_date]

    price_info = []
    closings = []
    for stock in assets:
        stock_row = latest_data[latest_data[stock_col] == stock]
        if not stock_row.empty:
            row = stock_row.iloc[0]
            for col in INFORMATION_COLS:
                price_info.append(float(row[col]) if col in row.index else 0.0)
            closings.append(float(row["close"]) if "close" in row.index else 0.0)
        else:
            price_info.extend([0.0] * len(INFORMATION_COLS))
            closings.append(0.0)

    closings = np.array(closings, dtype=np.float32)
    observation = np.array(
        [balance] + list(holdings) + price_info, dtype=np.float32
    )

    print(f"  [{model_name}] Observation 维度: {observation.shape}  "
          f"(1 余额 + {n_stocks} 持仓 + {len(price_info)} 特征)")
    print(f"  [{model_name}] 最新行情日期: {latest_date}")

    # ---------- 预测 ----------
    action, _ = agent.predict(observation, deterministic=True)

    # ---------- 转换为实际股数（简化版，不调用 futu 实时接口） ----------
    from config.env_params import ENV_PARAMS
    hmax = env_params.get("hmax", ENV_PARAMS["hmax"])

    # action * hmax = 交易金额（元）
    # 交易金额 / 收盘价 = 股数
    raw_shares = action * hmax
    out = np.zeros_like(raw_shares)
    nonzero = closings != 0
    shares = np.divide(raw_shares, closings, out=out, where=nonzero)

    # 按 100 手取整（A 股每手 100 股）
    lot_size = 100
    shares = np.sign(shares) * (np.abs(shares) // lot_size) * lot_size

    # 卖出不超过持仓（这里持仓全为 0，所以卖出会被清零）
    shares = np.maximum(shares, -holdings)

    # ---------- 整理结果 ----------
    code2index = {stock: i for i, stock in enumerate(assets)}
    buy_list = []
    sell_list = []
    hold_list = []

    for i, stock in enumerate(assets):
        s = int(shares[i])
        price = float(closings[i])
        if s > 0:
            buy_list.append({"code": stock, "shares": s, "price": price, "amount": s * price})
        elif s < 0:
            sell_list.append({"code": stock, "shares": abs(s), "price": price, "amount": abs(s) * price})
        else:
            hold_list.append(stock)

    return {
        "model": model_name,
        "date": latest_date,
        "buy": buy_list,
        "sell": sell_list,
        "hold": hold_list,
        "raw_action": action,
    }


def print_result_table(result: dict):
    """以表格形式打印结果"""
    print(f"\n{'='*70}")
    print(f"模型: {result['model']}  |  行情日期: {result['date']}")
    print(f"{'='*70}")

    if result["buy"]:
        print(f"\n📈 买入列表（共 {len(result['buy'])} 只）：")
        print(f"  {'股票代码':<14} {'买入股数':>10} {'参考价':>10} {'估算金额':>14}")
        print(f"  {'-'*52}")
        for item in sorted(result["buy"], key=lambda x: -x["amount"]):
            print(f"  {item['code']:<14} {item['shares']:>10,} {item['price']:>10.2f} {item['amount']:>14,.0f}")
        total_buy = sum(i["amount"] for i in result["buy"])
        print(f"  {'合计':<14} {'':<10} {'':<10} {total_buy:>14,.0f}")
    else:
        print("\n📈 买入列表：（无）")

    if result["sell"]:
        print(f"\n📉 卖出列表（共 {len(result['sell'])} 只）：")
        print(f"  {'股票代码':<14} {'卖出股数':>10} {'参考价':>10} {'估算金额':>14}")
        print(f"  {'-'*52}")
        for item in sorted(result["sell"], key=lambda x: -x["amount"]):
            print(f"  {item['code']:<14} {item['shares']:>10,} {item['price']:>10.2f} {item['amount']:>14,.0f}")
        total_sell = sum(i["amount"] for i in result["sell"])
        print(f"  {'合计':<14} {'':<10} {'':<10} {total_sell:>14,.0f}")
    else:
        print("\n📉 卖出列表：（无）")

    print(f"\n⏸  持有不动（共 {len(result['hold'])} 只）：{', '.join(result['hold'][:10])}"
          + ("..." if len(result["hold"]) > 10 else ""))
    print(f"{'='*70}")


def merge_votes(results: list) -> dict:
    """多模型投票：买入/卖出票数超过一半的股票才执行"""
    from collections import Counter
    import numpy as np

    all_codes = set()
    for r in results:
        for item in r["buy"]:
            all_codes.add(item["code"])
        for item in r["sell"]:
            all_codes.add(item["code"])
        all_codes.update(r["hold"])

    buy_votes = Counter()
    sell_votes = Counter()
    buy_shares = {}
    sell_shares = {}

    for r in results:
        for item in r["buy"]:
            buy_votes[item["code"]] += 1
            buy_shares.setdefault(item["code"], []).append(item)
        for item in r["sell"]:
            sell_votes[item["code"]] += 1
            sell_shares.setdefault(item["code"], []).append(item)

    threshold = len(results) / 2
    date = results[0]["date"]

    final_buy = []
    final_sell = []
    for code in all_codes:
        if buy_votes[code] > threshold:
            # 取各模型平均股数
            items = buy_shares[code]
            avg_shares = int(np.mean([i["shares"] for i in items]) // 100 * 100)
            price = items[0]["price"]
            if avg_shares > 0:
                final_buy.append({"code": code, "shares": avg_shares, "price": price, "amount": avg_shares * price})
        elif sell_votes[code] > threshold:
            items = sell_shares[code]
            avg_shares = int(np.mean([i["shares"] for i in items]) // 100 * 100)
            price = items[0]["price"]
            if avg_shares > 0:
                final_sell.append({"code": code, "shares": avg_shares, "price": price, "amount": avg_shares * price})

    final_hold = [c for c in all_codes if c not in {i["code"] for i in final_buy} and c not in {i["code"] for i in final_sell}]

    return {
        "model": f"VOTE({','.join(r['model'] for r in results)})",
        "date": date,
        "buy": final_buy,
        "sell": final_sell,
        "hold": sorted(final_hold),
        "raw_action": None,
    }


def main():
    args = parse_args()

    # ---------- 路径设置 ----------
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.join(script_dir, "tests")
    data_dir = args.data_dir or os.path.join(tests_dir, "stock_data")
    model_dir = args.model_dir or os.path.join(tests_dir, "models")

    # ---------- 日期计算 ----------
    end_date = datetime.now()
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    split_date = end_date - timedelta(days=args.split_days)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    split_str = split_date.strftime("%Y-%m-%d")

    print("=" * 60)
    print("股票模型预测")
    print("=" * 60)
    print(f"数据目录:   {data_dir}")
    print(f"模型目录:   {model_dir}")
    print(f"初始资金:   ¥{args.initial_amount:,.0f}（用于构建状态，假设全现金）")
    print("=" * 60)

    # ---------- 加载数据 ----------
    from data.a50_data import A50Data
    from data.data import DataInitParam
    from config.stock_codes import SSE_50_EXT
    from utils.stock_alot_info import StockAlotInfo

    StockAlotInfo.get_instance().load_data()

    param = DataInitParam(
        path=data_dir,
        stock_codes=SSE_50_EXT,
        start_date=start_str,
        end_date=end_str,
        split_date=split_str,
    )
    a50_data = A50Data(param)

    if args.no_update:
        print("\n跳过数据更新（--no-update）")
    else:
        print("\n正在更新数据...")
        a50_data.update()

    test_data = a50_data.get_test_data()
    if test_data is None or test_data.empty:
        print("✗ 测试数据为空，请检查 tushare token 或先运行 train.py")
        sys.exit(1)

    print(f"\n✓ 数据加载完成，最新日期: {test_data['date'].max()}")

    # ---------- 确定要使用的模型 ----------
    model_names = args.models if args.models else [args.model]
    model_names = [m.upper() for m in model_names]

    # ---------- 预测 ----------
    results = []
    for model_name in model_names:
        try:
            print(f"\n正在使用 {model_name} 模型预测...")
            result = load_and_predict(model_name, test_data, model_dir, args.initial_amount)
            results.append(result)
        except FileNotFoundError as e:
            print(f"⚠ {e}")
        except Exception as e:
            import traceback
            print(f"✗ {model_name} 预测失败: {e}")
            traceback.print_exc()

    if not results:
        print("\n✗ 所有模型预测失败")
        sys.exit(1)

    # ---------- 输出结果 ----------
    if args.output == "json":
        # JSON 格式输出
        output = []
        for r in results:
            output.append({
                "model": r["model"],
                "date": r["date"],
                "buy": r["buy"],
                "sell": r["sell"],
                "hold": r["hold"],
            })
        if len(results) > 1:
            merged = merge_votes(results)
            output.append({
                "model": merged["model"],
                "date": merged["date"],
                "buy": merged["buy"],
                "sell": merged["sell"],
                "hold": merged["hold"],
            })
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # 表格格式输出
        for r in results:
            print_result_table(r)

        if len(results) > 1:
            print(f"\n{'*'*70}")
            print("多模型投票结果（超过半数模型同意才执行）")
            print(f"{'*'*70}")
            merged = merge_votes(results)
            print_result_table(merged)


if __name__ == "__main__":
    main()
