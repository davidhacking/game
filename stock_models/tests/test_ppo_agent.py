import unittest
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from utils.stock_alot_info import StockAlotInfo

# 添加项目根目录到sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from data.a50_data import A50Data
from data.data import DataInitParam, StockCodeList
from environments.env import StockLearningEnv
from rl_agent.stock_agent import StockAgent
from rl_agent.rl_agent import RLAgentParam
from config import get_env_params


class TestPPOAgent(unittest.TestCase):
    """PPO算法的测试用例"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 设置数据路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_path = os.path.join(current_dir, "stock_data")
        
        # 计算日期：从2009年开始的数据用于训练，最近一年用于回测
        end_date = datetime.now()
        start_date = datetime(2009, 1, 1)  # 从2009年开始
        split_date = end_date - timedelta(days=365)   # 最近一年作为测试集
        
        # 格式化日期
        self.start_date = start_date.strftime('%Y-%m-%d')
        self.end_date = end_date.strftime('%Y-%m-%d')
        self.split_date = split_date.strftime('%Y-%m-%d')
        
        print(f"\n数据日期范围:")
        print(f"  开始日期: {self.start_date}")
        print(f"  分割日期: {self.split_date}")
        print(f"  结束日期: {self.end_date}")
        print(f"  训练集: {self.start_date} 到 {self.split_date}")
        print(f"  测试集: {self.split_date} 到 {self.end_date}")
        
        # 创建测试用的DataInitParam
        self.param = DataInitParam(
            path=self.data_path,
            stock_codes=None,  # 使用默认的SSE_50股票代码
            start_date=self.start_date,
            end_date=self.end_date,
            split_date=self.split_date
        )
        
        # 初始化A50Data实例
        try:
            self.a50_data = A50Data(self.param)
            print(f"✓ 数据初始化成功")
            
            # 调用update()更新最新数据
            print("正在更新最新数据...")
            self.a50_data.update()
        except Exception as e:
            print(f"✗ 数据初始化失败: {e}")
            if "stock_data" in str(e) or "文件" in str(e):
                self.skipTest(f"数据文件不存在，跳过所有测试: {e}")
            else:
                raise
        
        # 设置模型保存路径
        self.model_path = os.path.join(current_dir, "models", "ppo_stock_agent")
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        StockAlotInfo.get_instance().load_data()
    
    def test_ppo_init(self):
        """测试PPO Agent初始化"""
        train_data = self.a50_data.get_train_data()
        
        if train_data.empty:
            self.skipTest("训练数据为空，跳过测试")
        
        # 创建训练环境
        env_params = get_env_params(print_verbosity=1000, random_start=True)
        train_env = StockLearningEnv(df=train_data, **env_params)
        
        # 创建PPO Agent参数
        agent_param = RLAgentParam(
            model_name="PPO",
            policy="MlpPolicy",
            total_timesteps=1000,  # 测试用较小的步数
            verbose=1,
            model_path=self.model_path
        )
        
        # 初始化PPO Agent
        agent = StockAgent(env=train_env, param=agent_param)
        
        self.assertIsNotNone(agent)
        self.assertIsNotNone(agent.model)
        print("✓ PPO Agent初始化测试通过")
    
    def test_ppo_train(self):
        """测试PPO Agent训练"""
        train_data = self.a50_data.get_train_data()
        
        if train_data.empty:
            self.skipTest("训练数据为空，跳过测试")
        
        print(f"\n训练数据大小: {len(train_data)} 条记录")
        print(f"训练数据日期范围: {train_data['date'].min()} 到 {train_data['date'].max()}")
        
        # 创建训练环境
        env_params = get_env_params(print_verbosity=1000, random_start=True)
        train_env = StockLearningEnv(df=train_data, **env_params)
        
        # 获取stable_baselines3兼容的环境
        train_env, _ = train_env.get_sb_env()
        
        # 创建PPO Agent参数
        agent_param = RLAgentParam(
            model_name="PPO",
            policy="MlpPolicy",
            total_timesteps=200000,  # 训练步数
            verbose=1,
            log_interval=10,
            model_path=self.model_path
        )
        
        # 初始化PPO Agent
        agent = StockAgent(env=train_env, param=agent_param)
        
        # 训练模型
        print("\n开始训练PPO模型...")
        agent.train()
        
        # 验证模型已保存
        self.assertTrue(os.path.exists(f"{self.model_path}.zip"))
        print(f"✓ PPO模型训练完成并已保存到: {self.model_path}.zip")

    # python -m unittest test_ppo_agent.TestPPOAgent.test_ppo_backtest
    def test_ppo_backtest(self):
        """测试PPO Agent回测"""
        test_data = self.a50_data.get_test_data()
        
        if test_data.empty:
            self.skipTest("测试数据为空，跳过测试")
        
        print(f"\n回测数据大小: {len(test_data)} 条记录")
        print(f"回测数据日期范围: {test_data['date'].min()} 到 {test_data['date'].max()}")
        
        # 检查模型是否存在
        if not os.path.exists(f"{self.model_path}.zip"):
            self.skipTest("模型文件不存在，请先运行训练测试")
        
        # 创建测试环境
        env_params = get_env_params(print_verbosity=100, random_start=False)
        test_env = StockLearningEnv(df=test_data, **env_params)
        
        # 获取stable_baselines3兼容的环境
        test_env, _ = test_env.get_sb_env()
        
        # 创建PPO Agent参数
        agent_param = RLAgentParam(
            model_name="PPO",
            policy="MlpPolicy",
            model_path=self.model_path
        )
        
        # 初始化PPO Agent并加载模型
        agent = StockAgent(env=test_env, param=agent_param)
        agent.load()
        
        # 执行回测
        print("\n开始回测PPO模型...")
        df_account_value, df_actions = agent.backtest(deterministic=True)
        
        # 验证回测结果
        self.assertIsNotNone(df_account_value)
        self.assertIsNotNone(df_actions)
        
        if df_account_value is not None:
            print("\n回测结果统计:")
            initial_value = df_account_value['total_assets'].iloc[0]
            final_value = df_account_value['total_assets'].iloc[-1]
            total_return = (final_value - initial_value) / initial_value * 100
            
            print(f"  初始资产: ￥{initial_value:,.2f}")
            print(f"  最终资产: ￥{final_value:,.2f}")
            print(f"  总收益率: {total_return:.2f}%")
            
            # 保存回测结果
            result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
            os.makedirs(result_dir, exist_ok=True)
            
            account_value_path = os.path.join(result_dir, "ppo_account_value.csv")
            actions_path = os.path.join(result_dir, "ppo_actions.csv")
            
            df_account_value.to_csv(account_value_path, index=False)
            df_actions.to_csv(actions_path, index=False)
            
            print(f"\n回测结果已保存:")
            print(f"  账户价值: {account_value_path}")
            print(f"  交易动作: {actions_path}")
        
        print("✓ PPO模型回测完成")

    # python -m unittest test_ppo_agent.TestPPOAgent.test_ppo_full_pipeline
    def test_ppo_full_pipeline(self):
        """测试PPO完整流程：训练 + 回测"""
        train_data = self.a50_data.get_train_data()
        test_data = self.a50_data.get_test_data()
        
        if train_data.empty or test_data.empty:
            self.skipTest("训练或测试数据为空，跳过测试")
        
        print("\n" + "="*60)
        print("开始PPO完整流程测试：训练 + 回测")
        print("="*60)
        
        # ========== 训练阶段 ==========
        print("\n【第一阶段：模型训练】")
        print(f"训练数据: {len(train_data)} 条记录")
        print(f"日期范围: {train_data['date'].min()} 到 {train_data['date'].max()}")
        
        env_params = get_env_params(print_verbosity=1000, random_start=True)
        train_env = StockLearningEnv(df=train_data, **env_params)
        train_env, _ = train_env.get_sb_env()
        
        agent_param = RLAgentParam(
            model_name="PPO",
            policy="MlpPolicy",
            total_timesteps=200000,  # 完整流程使用更多训练步数
            verbose=1,
            log_interval=10,
            model_path=self.model_path
        )
        
        agent = StockAgent(env=train_env, param=agent_param)
        agent.train()
        print("✓ 训练阶段完成")
        
        # ========== 回测阶段 ==========
        print("\n【第二阶段：模型回测】")
        print(f"回测数据: {len(test_data)} 条记录")
        print(f"日期范围: {test_data['date'].min()} 到 {test_data['date'].max()}")
        
        env_params = get_env_params(print_verbosity=100, random_start=False)
        test_env = StockLearningEnv(df=test_data, **env_params)
        test_env, _ = test_env.get_sb_env()
        
        # 重新创建agent并加载训练好的模型
        test_agent_param = RLAgentParam(
            model_name="PPO",
            policy="MlpPolicy",
            model_path=self.model_path
        )
        test_agent = StockAgent(env=test_env, param=test_agent_param)
        test_agent.load()
        
        df_account_value, df_actions = test_agent.backtest(deterministic=True)
        
        # 输出最终结果
        if df_account_value is not None:
            print("\n" + "="*60)
            print("【最终回测结果】")
            print("="*60)
            
            initial_value = df_account_value['total_assets'].iloc[0]
            final_value = df_account_value['total_assets'].iloc[-1]
            total_return = (final_value - initial_value) / initial_value * 100
            max_value = df_account_value['total_assets'].max()
            min_value = df_account_value['total_assets'].min()
            max_drawdown = (max_value - min_value) / max_value * 100
            
            print(f"初始资产: ￥{initial_value:,.2f}")
            print(f"最终资产: ￥{final_value:,.2f}")
            print(f"总收益率: {total_return:.2f}%")
            print(f"最大资产: ￥{max_value:,.2f}")
            print(f"最小资产: ￥{min_value:,.2f}")
            print(f"最大回撤: {max_drawdown:.2f}%")
            print("="*60)
            
            # 保存结果
            result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
            os.makedirs(result_dir, exist_ok=True)
            
            df_account_value.to_csv(os.path.join(result_dir, "ppo_full_account_value.csv"), index=False)
            df_actions.to_csv(os.path.join(result_dir, "ppo_full_actions.csv"), index=False)
            
            print(f"\n结果已保存到: {result_dir}")
        
        print("\n✓ PPO完整流程测试通过")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPPOAgent)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("开始测试 PPO Agent")
    print("=" * 60)
    print(f"数据路径: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stock_data')}")
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