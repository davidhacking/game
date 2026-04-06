#!/usr/bin/env python3
"""
训练脚本：更新数据并训练所有强化学习模型
用法：
    python train.py
    python train.py --models SAC PPO
    python train.py --timesteps 100000
    python train.py --models SAC --timesteps 50000 --no-update
"""

import os
import sys
import argparse
import multiprocessing as mp
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import traceback

# 将当前目录添加到 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def parse_args():
    parser = argparse.ArgumentParser(description="训练股票强化学习模型")
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="指定要训练的模型列表，如 --models SAC PPO。默认训练全部模型（A2C PPO DDPG TD3 SAC）",
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=200000,
        help="训练步数，默认 200000",
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
        help="数据保存目录，默认 tests/stock_data",
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default=None,
        help="模型保存目录，默认 tests/models",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2009-01-01",
        help="训练数据起始日期，默认 2009-01-01",
    )
    parser.add_argument(
        "--split-days",
        type=int,
        default=365,
        help="测试集天数（从今天往前推），默认 365 天",
    )
    return parser.parse_args()


def train_model(model_name: str, train_data, model_save_dir: str, total_timesteps: int) -> Tuple[bool, str]:
    """在独立进程中训练单个模型"""
    try:
        from data.a50_data import A50Data
        from environments.env import StockLearningEnv
        from rl_agent.stock_agent import StockAgent
        from rl_agent.rl_agent import RLAgentParam
        from config import get_env_params

        print(f"\n{'='*60}")
        print(f"训练模型: {model_name}")
        print(f"{'='*60}")
        print(f"训练数据: {len(train_data)} 条记录")
        print(f"日期范围: {train_data['date'].min()} 到 {train_data['date'].max()}")

        model_path = os.path.join(model_save_dir, f"{model_name.lower()}_stock_agent")

        env_params = get_env_params(print_verbosity=1000, random_start=True)
        train_env = StockLearningEnv(df=train_data, **env_params)
        train_env, _ = train_env.get_sb_env()

        agent_param = RLAgentParam(
            model_name=model_name,
            policy="MlpPolicy",
            total_timesteps=total_timesteps,
            verbose=1,
            log_interval=10,
            model_path=model_path,
        )

        agent = StockAgent(env=train_env, param=agent_param)
        agent.train()

        print(f"✓ {model_name} 训练完成，已保存到 {model_path}.zip")
        return True, f"{model_name}: 训练成功"

    except Exception as e:
        msg = f"{model_name}: 训练失败 - {str(e)}\n{traceback.format_exc()}"
        print(f"✗ {msg}")
        return False, msg


def main():
    args = parse_args()

    # ---------- 路径设置 ----------
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.join(script_dir, "tests")
    data_dir = args.data_dir or os.path.join(tests_dir, "stock_data")
    model_dir = args.model_dir or os.path.join(tests_dir, "models")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)

    # ---------- 日期计算 ----------
    end_date = datetime.now()
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    split_date = end_date - timedelta(days=args.split_days)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    split_str = split_date.strftime("%Y-%m-%d")

    print("=" * 60)
    print("股票模型训练")
    print("=" * 60)
    print(f"数据目录:   {data_dir}")
    print(f"模型目录:   {model_dir}")
    print(f"训练区间:   {start_str} → {split_str}")
    print(f"测试区间:   {split_str} → {end_str}")
    print(f"训练步数:   {args.timesteps}")
    print("=" * 60)

    # ---------- 加载 / 更新数据 ----------
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
        print("\n正在更新数据（通过 tushare）...")
        a50_data.update()

    train_data = a50_data.get_train_data()
    if train_data is None or train_data.empty:
        print("✗ 训练数据为空，请检查 tushare token 或网络连接")
        sys.exit(1)

    print(f"\n✓ 训练数据加载完成: {len(train_data)} 条记录")
    print(f"  日期范围: {train_data['date'].min()} 到 {train_data['date'].max()}")

    # ---------- 确定要训练的模型 ----------
    from config.model_params import MODEL_PARAMS

    all_model_names = [name.upper() for name in MODEL_PARAMS.keys()]
    if args.models:
        model_names = [m.upper() for m in args.models]
        invalid = [m for m in model_names if m.lower() not in MODEL_PARAMS]
        if invalid:
            print(f"✗ 不支持的模型: {invalid}，支持: {all_model_names}")
            sys.exit(1)
    else:
        model_names = all_model_names

    print(f"\n准备训练 {len(model_names)} 个模型: {', '.join(model_names)}")

    # ---------- 并发训练 ----------
    mp.set_start_method("spawn", force=True)

    tasks = [(name, train_data, model_dir, args.timesteps) for name in model_names]

    success_count = 0
    failed_models = []

    with mp.Pool(processes=min(len(model_names), mp.cpu_count())) as pool:
        results = pool.starmap(train_model, tasks)

    for success, message in results:
        if success:
            success_count += 1
        else:
            failed_models.append(message)

    # ---------- 结果汇总 ----------
    print("\n" + "=" * 60)
    print("训练结果汇总")
    print("=" * 60)
    print(f"成功: {success_count}/{len(model_names)}")
    if failed_models:
        print("失败的模型:")
        for msg in failed_models:
            print(f"  - {msg}")
    print("=" * 60)

    if success_count == 0:
        sys.exit(1)
    print(f"\n模型已保存到: {model_dir}")


if __name__ == "__main__":
    main()
