import unittest
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

# 添加项目根目录到sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from environments.env import StockLearningEnv
from rl_agent.stock_agent import StockAgent
from rl_agent.rl_agent import RLAgentParam
from config import get_env_params
from data.a50_data import A50Data
from data.data import DataInitParam
from utils.stock_alot_info import StockAlotInfo


class TestCurrentDayAction(unittest.TestCase):
    """测试当天股票数据预测actions"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 设置模型路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.models_dir = os.path.join(current_dir, "models")
        
        # 默认模型名称（可修改）
        self.model_name = "PPO"  # 可选: "PPO", "A2C", "DDPG", "TD3", "SAC"
        self.model_path = os.path.join(self.models_dir, f"{self.model_name.lower()}_stock_agent")
        
        # 设置数据路径并初始化A50Data
        self.data_path = os.path.join(current_dir, "cur_stock_data")
        
        # 获取今天的日期（使用'%Y%m%d'格式以匹配StockInfoMgr的要求）
        today = datetime.now().strftime('%Y%m%d')
        StockAlotInfo.get_instance().load_data()

        self.param = DataInitParam(
            path=self.data_path,
            stock_codes=None,  # 使用默认的SSE_50股票代码
            start_date=today,  # 从今天开始
            split_date=today,  # 从今天开始
            end_date=today     # 到今天结束
        )
        self.a50_data = A50Data(self.param)
        
        print(f"\n使用模型: {self.model_name}")
        print(f"模型路径: {self.model_path}")
        print(f"数据路径: {self.data_path}")
    
    def load_stock_data(self):
        """创建示例股票数据（通过A50Data获取最新的真实股票数据）"""
        try:
            # 更新数据以获取最新的股票信息
            print("\n正在获取最新股票数据...")
            self.a50_data.update()
            
            # 获取最新的股票数据
            latest_data = self.a50_data.stock_mgr.get_latest_stock_info()
            
            if latest_data.empty:
                print("⚠ 无法获取最新数据，使用示例数据")
                return self._create_fallback_sample_data()
            
            print(f"\n获取到最新股票数据:")
            print(f"日期: {latest_data['date'].iloc[0]}")
            print(f"股票数量: {latest_data['tic'].nunique()}")
            print(f"\n数据预览:")
            print(latest_data.head(10))
            
            return latest_data
            
        except Exception as e:
            print(f"✗ 获取A50数据失败: {str(e)}")
            print("使用示例数据代替")

    def predict_actions(self, stock_data, model_name="PPO", model_path=None):
        """
        使用模型预测当天股票的交易actions
        
        Args:
            stock_data: DataFrame，包含当天的股票数据
            model_name: 模型名称，可选 "PPO", "A2C", "DDPG", "TD3", "SAC"
            model_path: 模型文件路径，如果为None则使用默认路径
        
        Returns:
            raw_actions: numpy array，模型预测的原始交易动作（范围[-1, 1]）
            transactions: numpy array，经过get_transactions转换后的实际交易股数
            stock_codes: list，股票代码列表
        """
        if model_path is None:
            model_path = self.model_path
        
        # 检查模型是否存在
        if not os.path.exists(f"{model_path}.zip"):
            raise FileNotFoundError(f"模型文件不存在: {model_path}.zip")
        
        # 创建环境参数
        env_params = get_env_params(print_verbosity=1000, random_start=False)
        
        # 创建环境（使用当天数据）
        raw_env = StockLearningEnv(df=stock_data, **env_params)
        
        # 获取stable_baselines3兼容的环境
        env, obs = raw_env.get_sb_env()
        
        # 创建Agent参数
        agent_param = RLAgentParam(
            model_name=model_name,
            policy="MlpPolicy",
            model_path=model_path
        )
        
        # 初始化Agent并加载模型
        agent = StockAgent(env=env, param=agent_param)
        agent.load()
        
        # 预测原始actions（范围[-1, 1]）
        raw_actions, _ = agent.predict(obs, deterministic=True)
        
        # 通过环境的get_transactions方法转换为实际交易股数
        # 需要访问原始环境（非向量化环境）
        original_env = env.envs[0]
        transactions = original_env.get_transactions(raw_actions[0])
        
        # 获取股票代码列表
        stock_codes = stock_data['tic'].unique().tolist()
        
        return raw_actions[0], transactions, stock_codes

    # python -m unittest test_cur_action.TestCurrentDayAction.test_predict_current_day_actions
    def test_predict_current_day_actions(self):
        """测试预测当天股票的交易actions"""
        print("\n" + "="*60)
        print("测试：预测当天股票交易actions")
        print("="*60)
        
        # 1. 准备当天的股票数据
        # 可以选择使用示例数据或真实数据
        stock_data = self.load_stock_data()

        # 2. 检查模型是否存在
        if not os.path.exists(f"{self.model_path}.zip"):
            self.skipTest(f"模型文件不存在: {self.model_path}.zip，请先训练模型")
        
        # 3. 使用模型预测actions
        try:
            raw_actions, transactions, stock_codes = self.predict_actions(
                stock_data=stock_data,
                model_name=self.model_name,
                model_path=self.model_path
            )
            
            # 4. 输出预测结果
            print("\n" + "="*60)
            print("预测结果:")
            print("="*60)
            print(f"模型: {self.model_name}")
            print(f"日期: {stock_data['date'].iloc[0]}")
            print(f"\n股票数量: {len(stock_codes)}")
            print(f"Raw Actions维度: {raw_actions.shape}")
            print(f"Transactions维度: {transactions.shape}")
            print("\n详细Actions:")
            print(f"{'序号':<4} {'股票代码':<12} {'原始Action':<15} {'实际交易股数':<15} {'操作类型':<10}")
            print("-" * 70)
            
            for i, (code, raw_action, transaction) in enumerate(zip(stock_codes, raw_actions, transactions)):
                action_type = "买入" if transaction > 0 else ("卖出" if transaction < 0 else "持有")
                print(f"{i+1:<4} {code:<12} {raw_action:>14.4f} {transaction:>14.0f} {action_type:<10}")
            
            print("="*60)
            
            # 5. 统计信息
            buy_count = np.sum(transactions > 0)
            sell_count = np.sum(transactions < 0)
            hold_count = np.sum(transactions == 0)
            
            print(f"\n操作统计:")
            print(f"  买入: {buy_count} 只股票")
            print(f"  卖出: {sell_count} 只股票")
            print(f"  持有: {hold_count} 只股票")
            print("="*60)
            
            # 6. 验证结果
            self.assertIsNotNone(raw_actions)
            self.assertIsNotNone(transactions)
            self.assertEqual(len(raw_actions), len(stock_codes))
            self.assertEqual(len(transactions), len(stock_codes))
            
            print("\n✓ 预测成功!")
            
        except Exception as e:
            self.fail(f"预测失败: {str(e)}")

def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCurrentDayAction)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("测试：当天股票数据预测Actions")
    print("=" * 60)
    print()
    
    # 运行测试
    result = run_tests()
    
    print()
    print("=" * 60)
    print("测试完成")
    print(f"运行: {result.testsRun}, 成功: {result.testsRun - len(result.failures) - len(result.errors)}, "
          f"失败: {len(result.failures)}, 错误: {len(result.errors)}, 跳过: {len(result.skipped)}")
    print("=" * 60)
