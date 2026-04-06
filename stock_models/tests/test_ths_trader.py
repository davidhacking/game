import unittest
import os
import sys
import json

# 添加项目根目录到sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.ths_trader import position_info, balance_info, total_asset
from utils.transaction import TransactionManager


class TestThsBalance(unittest.TestCase):
    """测试balance_info函数"""
    # python -m unittest test_ths_trader.TestThsBalance.test_balance_info
    def test_balance_info(self):
        """测试获取资金余额信息并输出JSON结果"""
        print("\n" + "="*60)
        print("测试：获取资金余额信息")
        print("="*60)
        
        try:
            # 调用balance_info函数
            result = balance_info()
            
            # 输出返回的结果
            print("\n资金余额:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("="*60)
            
            # 验证返回结果不为None
            self.assertIsNotNone(result)
            
            print("\n✓ 获取资金余额信息成功!")
            
        except Exception as e:
            self.fail(f"获取资金余额信息失败: {str(e)}")


class TestThsPosition(unittest.TestCase):
    """测试position_info函数"""
    # python -m unittest test_ths_trader.TestThsPosition.test_position_info
    def test_position_info(self):
        """测试获取持仓信息并输出JSON结果"""
        print("\n" + "="*60)
        print("测试：获取持仓信息")
        print("="*60)
        
        try:
            # 调用position_info函数
            result = position_info()
            
            # 输出返回的JSON结果
            print("\n持仓信息:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("="*60)
            
            # 验证返回结果不为None
            self.assertIsNotNone(result)
            
            print("\n✓ 获取持仓信息成功!")
            
        except Exception as e:
            self.fail(f"获取持仓信息失败: {str(e)}")


class TestThsTotalAsset(unittest.TestCase):
    """测试total_asset函数"""
    # python -m unittest test_ths_trader.TestThsTotalAsset.test_total_asset
    def test_total_asset(self):
        """测试获取总资产信息并输出JSON结果"""
        print("\n" + "="*60)
        print("测试：获取总资产信息")
        print("="*60)
        
        try:
            # 调用total_asset函数
            result = total_asset()
            
            # 输出返回的JSON结果
            print("\n总资产信息:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("="*60)
            
            # 验证返回结果不为None
            self.assertIsNotNone(result)
            
            # 验证返回结果包含必要的字段
            self.assertIn("total_asset", result)
            self.assertIn("balance", result)
            self.assertIn("position", result)
            self.assertIn("cur_price", result)
            
            # 验证数据类型
            self.assertIsInstance(result["total_asset"], (int, float))
            self.assertIsInstance(result["balance"], (int, float))
            self.assertIsInstance(result["position"], dict)
            self.assertIsInstance(result["cur_price"], dict)
            
            print("\n✓ 获取总资产信息成功!")
            
        except Exception as e:
            self.fail(f"获取总资产信息失败: {str(e)}")


class TestThsTraderBySac(unittest.TestCase):
    """测试使用SAC模型进行交易"""
    # python -m unittest test_ths_trader.TestThsTraderBySac.test_trader_by_sac
    def test_trader_by_sac(self):
        """测试通过SAC模型预测并执行交易"""
        print("\n" + "="*60)
        print("测试：使用SAC模型进行交易")
        print("="*60)
        
        try:
            # 导入必要的模块
            from account.ths_account import ThsUserStockAccount
            from rl_agent.stock_agent import StockAgent
            from rl_agent.rl_agent import RLAgentParam
            from data.a50_data import A50Data
            from data.data import DataInitParam
            from config.stock_codes import SSE_50_EXT
            from datetime import datetime, timedelta
            import numpy as np
            
            print("\n步骤1: 初始化数据和账户")
            print("-" * 60)
            
            # 初始化数据
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, "stock_data")
            model_save_dir = os.path.join(current_dir, "models")
            
            end_date = datetime.now()
            start_date = datetime(2009, 1, 1)
            split_date = end_date - timedelta(days=365)
            
            param = DataInitParam(
                path=data_path,
                stock_codes=SSE_50_EXT,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                split_date=split_date.strftime('%Y-%m-%d')
            )
            a50_data = A50Data(param)
            a50_data.update()
            test_data = a50_data.get_test_data()
            
            # 获取code2index映射
            stock_col = "tic"
            assets = test_data[stock_col].unique()
            code2index = {stock: i for i, stock in enumerate(assets)}
            
            print(f"股票数量: {len(assets)}")
            print(f"股票列表: {list(assets)[:5]}... (显示前5个)")
            
            # 初始化同花顺账户
            ths_account = ThsUserStockAccount(code2index=code2index)
            
            print("\n步骤2: 获取当前持仓信息")
            print("-" * 60)
            
            # 获取当前持仓
            balance, holdings = ths_account.cur_holds()
            
            print(f"当前余额: ￥{balance:,.2f}")
            print(f"持仓数组长度: {len(holdings)}")
            print(f"持仓详情: {holdings}")
            
            print("\n步骤3: 加载SAC模型")
            print("-" * 60)
            
            # 检查模型文件是否存在
            model_path = os.path.join(model_save_dir, "sac_stock_agent")
            if not os.path.exists(model_path + ".zip"):
                print(f"⚠ SAC模型文件不存在: {model_path}.zip")
                print("请先运行 test_all_models.py 训练模型")
                self.skipTest("SAC模型文件不存在，跳过测试")
                return
            
            # 创建一个临时环境用于加载模型（不需要真正使用）
            from environments.env import StockLearningEnv
            from config import get_env_params
            
            env_params = get_env_params(print_verbosity=100, random_start=False)
            temp_env = StockLearningEnv(df=test_data, **env_params)
            temp_env, _ = temp_env.get_sb_env()
            
            # 加载SAC模型
            agent_param = RLAgentParam(
                model_name="SAC",
                policy="MlpPolicy",
                model_path=model_path
            )
            agent = StockAgent(env=temp_env, param=agent_param)
            agent.load()
            
            print(f"✓ SAC模型加载成功")
            
            print("\\n步骤4: 构建observation并进行预测")
            print("-" * 60)
            
            # 构建observation
            # observation = [balance] + holdings + price_info
            # 获取最新的价格信息（使用test_data的最后一天数据）
            latest_date = test_data['date'].max()
            latest_data = test_data[test_data['date'] == latest_date]
            
            # 按照code2index的顺序获取价格信息
            # 使用env_params中定义的INFORMATION_COLS
            from config.env_params import INFORMATION_COLS
            daily_information_cols = INFORMATION_COLS
            price_info = []
            for stock in assets:
                stock_data = latest_data[latest_data[stock_col] == stock]
                if not stock_data.empty:
                    for col in daily_information_cols:
                        price_info.append(stock_data[col].values[0])
                else:
                    # 如果没有数据，填充0
                    price_info.extend([0] * len(daily_information_cols))
            
            # 构建完整的observation
            observation = np.array([balance] + list(holdings) + price_info, dtype=np.float32)
            
            print(f"Observation维度: {observation.shape}")
            print(f"  - 余额维度: 1")
            print(f"    余额值: ￥{balance:,.2f}")
            print(f"  - 持仓维度: {len(holdings)}")
            print(f"    持仓详情: {holdings[:5]}... (显示前5个)" if len(holdings) > 5 else f"    持仓详情: {holdings}")
            print(f"    持仓总量: {sum(holdings)}")
            print(f"  - 价格信息维度: {len(price_info)}")
            print(f"    股票数量: {len(assets)}")
            print(f"    每只股票特征数: {len(daily_information_cols)}")
            print(f"    特征列表: {daily_information_cols}")
            print(f"    价格信息样例(前{min(10, len(price_info))}个): {price_info[:10]}")
            print(f"  - Observation总维度: {len(observation)} (1 + {len(holdings)} + {len(price_info)})")
            
            # 使用模型预测
            action, _ = agent.predict(observation, deterministic=True)
            
            print(f"\n预测的action:")
            print(f"  - Action维度: {action.shape}")
            print(f"  - Action范围: [{action.min():.4f}, {action.max():.4f}]")
            print(f"  - Action详情: {action}")
            
            print("\n步骤5: 执行交易动作")
            print("-" * 60)
            
            # 更新账户的收盘价信息（用于计算交易价格）
            closings = []
            for stock in assets:
                stock_data = latest_data[latest_data[stock_col] == stock]
                if not stock_data.empty:
                    closings.append(stock_data['close'].values[0])
                else:
                    closings.append(0)

            ths_account.close_dict = {
                stock: price for stock, price in zip(assets, closings)
            }

            print(f"收盘价信息已更新")
            
            # 通过transaction.py的get_transactions函数转换为实际交易股数
            print(f"\n转换actions为实际交易股数...")
            print(f"  - 原始action范围: [{action.min():.4f}, {action.max():.4f}]")
            
            # 使用TransactionManager类的get_transactions方法
            transaction_manager = TransactionManager(
                actions=action,
                cash_on_hand=balance,
                holdings=holdings,
                hmax=5000,
                code2index=code2index,
                normalize_buy_sell=True
            )
            transactions = transaction_manager.get_transactions()
            
            print(f"  - 转换后transactions范围: [{transactions.min():.0f}, {transactions.max():.0f}]")
            print(f"  交易详情（按股票）:")
            print(f"  {'股票代码':<12} {'当前持仓':<10} {'交易数量':<10} {'收盘价':<10} {'操作':<8}")
            print(f"  {'-'*60}")
            
            buy_count = 0
            sell_count = 0
            hold_count = 0
            total_buy_cost = 0.0
            total_sell_cost = 0.0
            
            for i, (stock, trans, holding, price) in enumerate(zip(assets, transactions, holdings, closings)):
                if trans > 0:
                    operation = "买入"
                    buy_count += 1
                    # 计算买入费用：交易金额 = 数量 * 价格
                    total_buy_cost += trans * price
                elif trans < 0:
                    operation = "卖出"
                    sell_count += 1
                    # 计算卖出费用：交易金额 = 数量 * 价格（trans为负数，取绝对值）
                    total_sell_cost += abs(trans) * price
                else:
                    operation = "持有"
                    hold_count += 1
                    continue  # 跳过持有不变的股票
                
                print(f"  {stock:<12} {holding:<10.0f} {trans:<10.0f} {price:<10.2f} {operation:<8}")
            
            print(f"  {'-'*60}")
            print(f"  汇总: 买入 {buy_count} 只, 卖出 {sell_count} 只, 持有 {hold_count} 只")
            print(f"  买入总费用: ￥{total_buy_cost:,.2f}")
            print(f"  卖出总费用: ￥{total_sell_cost:,.2f}")
            
            print(f"\n步骤5.1: 检查交易可行性")
            print("-" * 60)
            
            # 使用 get_spend_and_rest_money 检查交易是否可行
            spend, costs, coh = transaction_manager.get_spend_and_rest_money(transactions)
            
            print(f"交易可行性分析:")
            print(f"  - 当前余额: ￥{balance:,.2f}")
            print(f"  - 卖出收入: ￥{coh - balance:,.2f}")
            print(f"  - 卖出后现金: ￥{coh:,.2f}")
            print(f"  - 买入花费: ￥{spend:,.2f}")
            print(f"  - 交易手续费: ￥{costs:,.2f}")
            print(f"  - 剩余现金: ￥{coh - spend - costs:,.2f}")
            
            # 判断交易是否可行
            if spend + costs > coh:
                print(f"\n⚠ 警告: 资金不足，无法完成全部交易!")
                print(f"  需要: ￥{spend + costs:,.2f}")
                print(f"  可用: ￥{coh:,.2f}")
                print(f"  缺口: ￥{spend + costs - coh:,.2f}")
                
                # 先执行卖出操作以释放资金
                print(f"\n步骤5.2: 先执行卖出操作")
                print("-" * 60)
                
                # 只保留卖出操作（负数）
                sell_only_transactions = np.array([t if t < 0 else 0 for t in transactions])
                
                sell_count_only = sum(1 for t in sell_only_transactions if t < 0)
                print(f"将先执行 {sell_count_only} 只股票的卖出操作")
                
                # 执行卖出操作
                ths_account.take_action(
                    date=latest_date,
                    action=sell_only_transactions
                )
                
                print(f"✓ 卖出操作执行完成!")
                print(f"\n注意: 由于资金不足，买入操作未执行")
                print("="*60)
                
                # 获取卖出后的持仓信息
                new_balance, new_holdings = ths_account.cur_holds()
                print(f"\n卖出后余额: ￥{new_balance:,.2f}")
                print(f"卖出后持仓: {new_holdings}")
                
                return
            else:
                print(f"\n✓ 资金充足，可以执行交易")
            
            print(f"\n准备执行交易...")

            # 执行交易（使用转换后的transactions）
            ths_account.take_action(
                date=latest_date,
                action=transactions
            )

            print(f"\n✓ 交易执行完成!")

            print("\n步骤6: 验证结果")
            print("-" * 60)

            # 再次获取持仓信息验证
            new_balance, new_holdings = ths_account.cur_holds()

            print(f"交易后余额: ￥{new_balance:,.2f}")
            print(f"交易后持仓: {new_holdings}")

            # 验证
            self.assertIsNotNone(action)
            self.assertIsNotNone(transactions)
            self.assertEqual(len(action), len(assets))
            self.assertEqual(len(transactions), len(assets))

            print("\n" + "="*60)
            print("✓ SAC模型交易测试成功!")
            print("="*60)
            
        except Exception as e:
            import traceback
            print(f"\n✗ 测试失败: {str(e)}")
            print(traceback.format_exc())
            self.fail(f"SAC模型交易测试失败: {str(e)}")


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestThsBalance))
    suite.addTests(loader.loadTestsFromTestCase(TestThsPosition))
    suite.addTests(loader.loadTestsFromTestCase(TestThsTotalAsset))
    suite.addTests(loader.loadTestsFromTestCase(TestThsTraderBySac))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("测试：同花顺交易接口")
    print("=" * 60)
    print()
    
    # 运行测试
    result = run_tests()
    
    print()
    print("=" * 60)
    print("测试完成")
    print(f"运行: {result.testsRun}, 成功: {result.testsRun - len(result.failures) - len(result.errors)}, "
          f"失败: {len(result.failures)}, 错误: {len(result.errors)}")
    print("=" * 60)
