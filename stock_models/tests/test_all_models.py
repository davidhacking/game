import unittest
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import multiprocessing as mp
from typing import Tuple, Optional
import traceback

# 添加项目根目录到sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from data.a50_data import A50Data
from data.a50_index_data import A50IndexData
from data.data import DataInitParam, StockCodeList
from environments.env import StockLearningEnv
from rl_agent.stock_agent import StockAgent
from rl_agent.rl_agent import RLAgentParam
from config import get_env_params
from config.model_params import MODEL_PARAMS
from config.stock_codes import SSE_50_EXT
from utils.stock_alot_info import StockAlotInfo


def train_single_model(model_name: str, train_data: pd.DataFrame,
                      model_save_dir: str, total_timesteps: int = 200000) -> Tuple[bool, str]:
    """
    在独立进程中训练单个模型
    
    Args:
        model_name: 模型名称（A2C, PPO, DDPG, TD3, SAC）
        train_data: 训练数据DataFrame
        model_save_dir: 模型保存目录
        total_timesteps: 训练步数
        
    Returns:
        Tuple[bool, str]: (是否成功, 消息)
    """
    try:
        print(f"\n{'='*60}")
        print(f"训练模型: {model_name}")
        print(f"{'='*60}")
        print(f"训练数据: {len(train_data)} 条记录")
        print(f"日期范围: {train_data['date'].min()} 到 {train_data['date'].max()}")
        
        # 设置模型保存路径
        model_path = os.path.join(model_save_dir, f"{model_name.lower()}_stock_agent")
        
        # 创建训练环境
        env_params = get_env_params(print_verbosity=1000, random_start=True)
        train_env = StockLearningEnv(df=train_data, **env_params)
        train_env, _ = train_env.get_sb_env()
        
        # 创建Agent参数
        agent_param = RLAgentParam(
            model_name=model_name,
            policy="MlpPolicy",
            total_timesteps=total_timesteps,
            verbose=1,
            log_interval=10,
            model_path=model_path
        )
        
        # 训练模型
        agent = StockAgent(env=train_env, param=agent_param)
        agent.train()
        print(f"✓ {model_name} 训练完成")
        
        return True, f"{model_name}: 训练成功"
        
    except Exception as e:
        error_msg = f"{model_name}: 训练失败 - {str(e)}\n{traceback.format_exc()}"
        print(f"\n✗ {error_msg}")
        return False, error_msg


def backtest_single_model(model_name: str, test_data: pd.DataFrame,
                         model_save_dir: str, result_dir: str) -> Tuple[bool, str, Optional[dict]]:
    """
    在独立进程中回测单个模型
    
    Args:
        model_name: 模型名称（A2C, PPO, DDPG, TD3, SAC）
        test_data: 测试数据DataFrame
        model_save_dir: 模型保存目录
        result_dir: 结果保存目录
        
    Returns:
        Tuple[bool, str, Optional[dict]]: (是否成功, 消息, 回测结果字典)
    """
    try:
        print(f"\n{'='*60}")
        print(f"回测模型: {model_name}")
        print(f"{'='*60}")
        print(f"回测数据: {len(test_data)} 条记录")
        print(f"日期范围: {test_data['date'].min()} 到 {test_data['date'].max()}")
        
        # 设置模型路径
        model_path = os.path.join(model_save_dir, f"{model_name.lower()}_stock_agent")
        
        # 检查模型文件是否存在
        if not os.path.exists(model_path + ".zip"):
            return False, f"{model_name}: 模型文件不存在", None
        
        # 创建回测环境
        env_params = get_env_params(print_verbosity=100, random_start=False)
        test_env = StockLearningEnv(df=test_data, **env_params)
        test_env, _ = test_env.get_sb_env()
        
        # 创建agent并加载训练好的模型
        test_agent_param = RLAgentParam(
            model_name=model_name,
            policy="MlpPolicy",
            model_path=model_path
        )
        test_agent = StockAgent(env=test_env, param=test_agent_param)
        test_agent.load()
        
        # 执行回测
        df_account_value, df_actions = test_agent.backtest(deterministic=True)
        
        # 计算回测结果
        if df_account_value is not None and not df_account_value.empty:
            initial_value = df_account_value['total_assets'].iloc[0]
            final_value = df_account_value['total_assets'].iloc[-1]
            total_return = (final_value - initial_value) / initial_value * 100
            max_value = df_account_value['total_assets'].max()
            min_value = df_account_value['total_assets'].min()
            max_drawdown = (max_value - min_value) / max_value * 100
            
            results = {
                'model_name': model_name,
                'initial_value': initial_value,
                'final_value': final_value,
                'total_return': total_return,
                'max_value': max_value,
                'min_value': min_value,
                'max_drawdown': max_drawdown
            }
            
            print(f"\n【{model_name} - 回测结果】")
            print(f"初始资产: ￥{initial_value:,.2f}")
            print(f"最终资产: ￥{final_value:,.2f}")
            print(f"总收益率: {total_return:.2f}%")
            print(f"最大资产: ￥{max_value:,.2f}")
            print(f"最小资产: ￥{min_value:,.2f}")
            print(f"最大回撤: {max_drawdown:.2f}%")
            
            # 保存结果
            os.makedirs(result_dir, exist_ok=True)
            
            df_account_value.to_csv(
                os.path.join(result_dir, f"{model_name.lower()}_account_value.csv"), 
                index=False
            )
            df_actions.to_csv(
                os.path.join(result_dir, f"{model_name.lower()}_actions.csv"), 
                index=False
            )
            
            print(f"✓ {model_name} 回测完成")
            return True, f"{model_name}: 回测成功", results
        else:
            return False, f"{model_name}: 回测结果为空", None
            
    except Exception as e:
        error_msg = f"{model_name}: 回测失败 - {str(e)}\n{traceback.format_exc()}"
        print(f"\n✗ {error_msg}")
        return False, error_msg, None


class TestAllModels(unittest.TestCase):
    """测试所有强化学习模型的完整流程"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 设置数据路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_path = os.path.join(current_dir, "stock_data")
        
        # 计算日期
        end_date = datetime.now()
        start_date = datetime(2009, 1, 1)
        split_date = end_date - timedelta(days=365)
        
        self.start_date = start_date.strftime('%Y-%m-%d')
        self.end_date = end_date.strftime('%Y-%m-%d')
        self.split_date = split_date.strftime('%Y-%m-%d')
        
        # 设置模型保存目录
        self.model_save_dir = os.path.join(current_dir, "models")
        os.makedirs(self.model_save_dir, exist_ok=True)
        
        # 设置结果保存目录
        self.result_dir = os.path.join(current_dir, "results")
        os.makedirs(self.result_dir, exist_ok=True)
        
        StockAlotInfo.get_instance().load_data()
        
        # 初始化A50Data实例
        param = DataInitParam(
            path=self.data_path,
            stock_codes=SSE_50_EXT,
            start_date=self.start_date,
            end_date=self.end_date,
            split_date=self.split_date
        )
        self.a50_data = A50Data(param)

        print(f"\n{'='*60}")
        print("测试配置信息")
        print(f"{'='*60}")
        print(f"数据路径: {self.data_path}")
        print(f"模型保存路径: {self.model_save_dir}")
        print(f"结果保存路径: {self.result_dir}")
        print(f"开始日期: {self.start_date}")
        print(f"分割日期: {self.split_date}")
        print(f"结束日期: {self.end_date}")
        print(f"训练集: {self.start_date} 到 {self.split_date}")
        print(f"测试集: {self.split_date} 到 {self.end_date}")
        print(f"{'='*60}")

    # python -m unittest tests.test_all_models.TestAllModels.test_01_data_preparation
    def test_01_data_preparation(self):
        """测试1：数据获取和准备"""
        print(f"\n{'='*60}")
        print("测试1：数据获取和准备")
        print(f"{'='*60}")
        
        # 调用update()更新最新数据
        print("正在更新最新数据...")
        self.a50_data.update()
        
        train_data = self.a50_data.get_train_data()
        test_data = self.a50_data.get_test_data()
        
        # 验证数据
        self.assertFalse(train_data.empty, "训练数据不应为空")
        self.assertFalse(test_data.empty, "测试数据不应为空")
        
        print(f"✓ 数据加载完成")
        print(f"  训练数据: {len(train_data)} 条记录")
        print(f"  测试数据: {len(test_data)} 条记录")
        print(f"  训练日期范围: {train_data['date'].min()} 到 {train_data['date'].max()}")
        print(f"  测试日期范围: {test_data['date'].min()} 到 {test_data['date'].max()}")
        print(f"{'='*60}")
        
    # python -m unittest tests.test_all_models.TestAllModels.test_02_model_training
    def test_02_model_training(self):
        """测试2：模型训练"""
        print(f"\n{'='*60}")
        print("测试2：模型训练")
        print(f"{'='*60}")
        
        # 确保数据已更新
        self.a50_data.update()
        train_data = self.a50_data.get_train_data()
        
        self.assertIsNotNone(train_data, "训练数据不应为None")
        self.assertFalse(train_data.empty, "训练数据不应为空")
        
        print(f"训练数据: {len(train_data)} 条记录")
        print(f"日期范围: {train_data['date'].min()} 到 {train_data['date'].max()}")
        
        # 获取所有模型名称
        model_names = [name.upper() for name in MODEL_PARAMS.keys()]
        print(f"\n准备训练 {len(model_names)} 个模型: {', '.join(model_names)}")
        
        # 设置训练步数
        total_timesteps = 200000
        
        # 使用multiprocessing并发训练所有模型
        success_count = 0
        failed_models = []
        
        # 创建进程池
        with mp.Pool(processes=min(len(model_names), mp.cpu_count())) as pool:
            # 准备参数列表
            tasks = [
                (model_name, train_data, self.model_save_dir, total_timesteps)
                for model_name in model_names
            ]
            
            # 并发执行训练
            print(f"\n开始并发训练 {len(model_names)} 个模型...")
            results = pool.starmap(train_single_model, tasks)
            
            # 统计结果
            for success, message in results:
                if success:
                    success_count += 1
                    print(f"✓ {message}")
                else:
                    failed_models.append(message)
                    print(f"✗ {message}")
        
        # 输出训练结果汇总
        print(f"\n{'='*60}")
        print("模型训练结果汇总")
        print(f"{'='*60}")
        print(f"成功: {success_count}/{len(model_names)}")
        if failed_models:
            print(f"失败的模型:")
            for msg in failed_models:
                print(f"  - {msg}")
        print(f"{'='*60}")
        
        # 断言至少有一个模型训练成功
        self.assertGreater(success_count, 0, "至少应有一个模型训练成功")
        
    # python -m unittest test_all_models.TestAllModels.test_03_model_backtest
    def test_03_model_backtest(self):
        """测试3：模型回测"""
        print(f"\n{'='*60}")
        print("测试3：模型回测")
        print(f"{'='*60}")
        
        # 确保数据已更新
        self.a50_data.update()
        test_data = self.a50_data.get_test_data()
        
        self.assertIsNotNone(test_data, "测试数据不应为None")
        self.assertFalse(test_data.empty, "测试数据不应为空")
        
        print(f"回测数据: {len(test_data)} 条记录")
        print(f"日期范围: {test_data['date'].min()} 到 {test_data['date'].max()}")
        
        # 获取所有已训练的模型
        model_names = [name.upper() for name in MODEL_PARAMS.keys()]
        print(f"\n准备回测 {len(model_names)} 个模型: {', '.join(model_names)}")
        
        # 回测所有模型
        success_count = 0
        failed_models = []
        all_results = []
        
        for model_name in model_names:
            try:
                print(f"\n{'='*60}")
                print(f"回测模型: {model_name}")
                print(f"{'='*60}")
                
                # 检查模型文件是否存在
                model_path = os.path.join(self.model_save_dir, f"{model_name.lower()}_stock_agent")
                if not os.path.exists(model_path + ".zip"):
                    print(f"⚠ 模型文件不存在: {model_path}.zip，跳过回测")
                    failed_models.append(f"{model_name}: 模型文件不存在")
                    continue
                
                # 创建回测环境
                env_params = get_env_params(print_verbosity=100, random_start=False)
                test_env = StockLearningEnv(df=test_data, **env_params)
                test_env, _ = test_env.get_sb_env()
                
                # 创建agent并加载训练好的模型
                test_agent_param = RLAgentParam(
                    model_name=model_name,
                    policy="MlpPolicy",
                    model_path=model_path
                )
                test_agent = StockAgent(env=test_env, param=test_agent_param)
                test_agent.load()
                
                # 执行回测
                df_account_value, df_actions = test_agent.backtest(deterministic=True)
                
                # 计算回测结果
                if df_account_value is not None and not df_account_value.empty:
                    initial_value = df_account_value['total_assets'].iloc[0]
                    final_value = df_account_value['total_assets'].iloc[-1]
                    total_return = (final_value - initial_value) / initial_value * 100
                    max_value = df_account_value['total_assets'].max()
                    min_value = df_account_value['total_assets'].min()
                    max_drawdown = (max_value - min_value) / max_value * 100
                    
                    results = {
                        'model_name': model_name,
                        'initial_value': initial_value,
                        'final_value': final_value,
                        'total_return': total_return,
                        'max_value': max_value,
                        'min_value': min_value,
                        'max_drawdown': max_drawdown
                    }
                    all_results.append(results)
                    
                    print(f"\n【{model_name} - 回测结果】")
                    print(f"初始资产: ￥{initial_value:,.2f}")
                    print(f"最终资产: ￥{final_value:,.2f}")
                    print(f"总收益率: {total_return:.2f}%")
                    print(f"最大资产: ￥{max_value:,.2f}")
                    print(f"最小资产: ￥{min_value:,.2f}")
                    print(f"最大回撤: {max_drawdown:.2f}%")
                    
                    # 保存结果
                    df_account_value.to_csv(
                        os.path.join(self.result_dir, f"{model_name.lower()}_account_value.csv"),
                        index=False
                    )
                    df_actions.to_csv(
                        os.path.join(self.result_dir, f"{model_name.lower()}_actions.csv"),
                        index=False
                    )
                    
                    print(f"✓ {model_name} 回测完成")
                    success_count += 1
                else:
                    failed_models.append(f"{model_name}: 回测结果为空")
                    
            except Exception as e:
                error_msg = f"{model_name}: 回测失败 - {str(e)}"
                print(f"✗ {error_msg}")
                failed_models.append(error_msg)
                traceback.print_exc()
        
        # 计算A50指数Baseline
        print(f"\n{'='*60}")
        print("计算A50指数Baseline")
        print(f"{'='*60}")
        baseline_result = self._calculate_a50_baseline(test_data)
        
        # 保存汇总结果
        if all_results:
            # 将baseline添加到结果列表
            if baseline_result:
                all_results.insert(0, baseline_result)  # 将baseline放在第一行
            
            summary_df = pd.DataFrame(all_results)
            summary_path = os.path.join(self.result_dir, "all_models_summary.csv")
            summary_df.to_csv(summary_path, index=False)
            
            print(f"\n{'='*60}")
            print("模型性能对比（含A50指数Baseline）")
            print(f"{'='*60}")
            print(summary_df.to_string(index=False))
            print(f"\n汇总结果已保存到: {summary_path}")
        
        # 输出回测结果汇总
        print(f"\n{'='*60}")
        print("模型回测结果汇总")
        print(f"{'='*60}")
        print(f"成功: {success_count}/{len(model_names)}")
        if failed_models:
            print(f"失败的模型:")
            for msg in failed_models:
                print(f"  - {msg}")
        print(f"{'='*60}")
        
        # 断言至少有一个模型回测成功
        self.assertGreater(success_count, 0, "至少应有一个模型回测成功")

    # python -m unittest test_all_models.TestAllModels.test_all_models_with_multiprocessing
    def test_all_models_with_multiprocessing(self):
        """完整流程测试：按顺序执行test_01、test_02、test_03"""
        model_names = [name.upper() for name in MODEL_PARAMS.keys()]
        
        print(f"\n{'='*60}")
        print(f"完整流程测试 {len(model_names)} 个模型: {', '.join(model_names)}")
        print(f"按顺序执行: test_01 → test_02 → test_03")
        print(f"{'='*60}")
        
        # ========== 阶段1：数据准备 ==========
        print(f"\n{'='*60}")
        print("阶段1：执行 test_01_data_preparation")
        print(f"{'='*60}")
        self.test_01_data_preparation()
        
        # ========== 阶段2：模型训练 ==========
        print(f"\n{'='*60}")
        print("阶段2：执行 test_02_model_training")
        print(f"{'='*60}")
        self.test_02_model_training()
        
        # ========== 阶段3：模型回测 ==========
        print(f"\n{'='*60}")
        print("阶段3：执行 test_03_model_backtest")
        print(f"{'='*60}")
        self.test_03_model_backtest()
        
        print(f"\n{'='*60}")
        print("完整流程测试完成")
        print(f"{'='*60}")
        print("✓ 所有阶段已成功执行")
    
    def _calculate_a50_baseline(self, test_data: pd.DataFrame) -> Optional[dict]:
        """
        计算A50指数作为baseline的统计数据
        
        Args:
            test_data: 测试数据DataFrame
            
        Returns:
            Optional[dict]: baseline结果字典，如果计算失败则返回None
        """
        try:
            # 创建A50IndexData实例获取指数数据
            index_param = DataInitParam(
                path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "index_data", "a50_index.csv"),
                stock_codes=None,
                start_date=self.start_date,
                end_date=self.end_date,
                split_date=self.split_date
            )
            
            a50_index_data = A50IndexData(index_param)
            a50_index_data.update()
            index_test_data = a50_index_data.get_test_data()
            
            if index_test_data.empty:
                print("⚠ A50指数测试数据为空，跳过baseline计算")
                return None
            
            # 获取测试期间的指数数据
            initial_close = index_test_data['close'].iloc[0]
            final_close = index_test_data['close'].iloc[-1]
            max_close = index_test_data['close'].max()
            min_close = index_test_data['close'].min()
            
            # 计算收益率和最大回撤
            total_return = (final_close - initial_close) / initial_close * 100
            max_drawdown = (max_close - min_close) / max_close * 100
            
            # 假设初始资产为100000（与模型训练时的初始资产一致）
            initial_value = 100000
            final_value = initial_value * (1 + total_return / 100)
            max_value = initial_value * (max_close / initial_close)
            min_value = initial_value * (min_close / initial_close)
            
            baseline_result = {
                'model_name': 'A50_INDEX_BASELINE',
                'initial_value': initial_value,
                'final_value': final_value,
                'total_return': total_return,
                'max_value': max_value,
                'min_value': min_value,
                'max_drawdown': max_drawdown
            }
            
            print(f"\n{'='*60}")
            print("【A50指数Baseline表现】")
            print(f"{'='*60}")
            print(f"初始点位: {initial_close:.2f}")
            print(f"最终点位: {final_close:.2f}")
            print(f"总收益率: {total_return:.2f}%")
            print(f"最大点位: {max_close:.2f}")
            print(f"最小点位: {min_close:.2f}")
            print(f"最大回撤: {max_drawdown:.2f}%")
            print(f"\n换算为资产表现（初始资产￥{initial_value:,.2f}）:")
            print(f"最终资产: ￥{final_value:,.2f}")
            print(f"最大资产: ￥{max_value:,.2f}")
            print(f"最小资产: ￥{min_value:,.2f}")
            print(f"{'='*60}")
            
            # 保存baseline数据
            baseline_path = os.path.join(self.result_dir, "a50_baseline.csv")
            index_test_data.to_csv(baseline_path, index=False)
            print(f"✓ A50指数Baseline数据已保存到: {baseline_path}")
            
            return baseline_result
            
        except Exception as e:
            print(f"⚠ 计算A50指数Baseline失败: {str(e)}")
            print(f"  这不会影响模型测试结果，但无法提供baseline对比")
            return None


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAllModels)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    # 设置multiprocessing启动方法（对于某些平台很重要）
    mp.set_start_method('spawn', force=True)
    
    print("=" * 60)
    print("开始测试所有强化学习模型")
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
