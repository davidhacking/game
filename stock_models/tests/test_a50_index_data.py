import unittest
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# 添加项目根目录到sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from data.a50_index_data import A50IndexData
from data.data import DataInitParam


class TestA50IndexData(unittest.TestCase):
    """A50IndexData类的测试用例"""
    
    def setUp(self):
        """测试前的准备工作 - 只初始化一次数据"""
        # 设置默认的数据路径为当前文件夹/index_data
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_path = os.path.join(current_dir, "index_data", "a50_index.csv")
        
        # 计算日期：最近一年用于回测baseline
        end_date = datetime.now()
        start_date = datetime(2009, 1, 1)  # 从2009年开始
        split_date = end_date - timedelta(days=365)   # 最近一年作为测试集
        
        # 格式化日期
        self.start_date = start_date.strftime('%Y-%m-%d')
        self.end_date = end_date.strftime('%Y-%m-%d')
        self.split_date = split_date.strftime('%Y-%m-%d')
        
        # 创建测试用的DataInitParam
        self.param = DataInitParam(
            path=self.data_path,
            stock_codes=None,  # A50IndexData不使用stock_codes参数
            start_date=self.start_date,
            end_date=self.end_date,
            split_date=self.split_date
        )
        
        # 初始化A50IndexData实例
        try:
            self.a50_index_data = A50IndexData(self.param)
            print(f"✓ A50指数数据初始化成功")
            print(f"  数据日期范围: {self.start_date} 到 {self.end_date}")
            print(f"  测试集(Baseline): {self.split_date} 到 {self.end_date}")
            
            # 调用update()更新最新数据
            print("正在更新最新数据...")
            self.a50_index_data.update()
        except Exception as e:
            print(f"✗ A50指数数据初始化失败: {e}")
            if "连接" in str(e) or "富途" in str(e):
                self.skipTest(f"富途API连接失败，跳过所有测试: {e}")
            else:
                raise

    # python -m unittest test_a50_index_data.TestA50IndexData.test_debug
    def test_debug(self):
        """测试debug方法"""
        # 调用debug方法，应该不会抛出异常
        print("\n--- Debug输出 ---")
        self.a50_index_data.debug()
        print("--- Debug输出结束 ---\n")
        print("✓ Debug方法测试通过")
    
    # python -m unittest test_a50_index_data.TestA50IndexData.test_baseline_statistics
    def test_baseline_statistics(self):
        """测试A50指数Baseline统计数据"""
        test_data = self.a50_index_data.get_test_data()
        
        if test_data.empty:
            self.skipTest("测试数据为空，跳过测试")
        
        print(f"\n回测数据大小: {len(test_data)} 条记录")
        print(f"回测数据日期范围: {test_data['date'].min()} 到 {test_data['date'].max()}")
        
        # 获取测试期间的指数数据
        initial_close = test_data['close'].iloc[0]
        final_close = test_data['close'].iloc[-1]
        max_close = test_data['close'].max()
        min_close = test_data['close'].min()
        
        # 计算收益率和最大回撤
        total_return = (final_close - initial_close) / initial_close * 100
        max_drawdown = (max_close - min_close) / max_close * 100
        
        # 打印Baseline统计数据
        print("\n" + "="*60)
        print("【A50指数Baseline表现】")
        print("="*60)
        print(f"初始点位: {initial_close:.2f}")
        print(f"最终点位: {final_close:.2f}")
        print(f"总收益率: {total_return:.2f}%")
        print(f"最大点位: {max_close:.2f}")
        print(f"最小点位: {min_close:.2f}")
        print(f"最大回撤: {max_drawdown:.2f}%")
        print("="*60)
        
        # 保存baseline结果
        result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
        os.makedirs(result_dir, exist_ok=True)
        
        baseline_path = os.path.join(result_dir, "a50_baseline.csv")
        test_data.to_csv(baseline_path, index=False)
        
        print(f"\nBaseline数据已保存到: {baseline_path}")
        print("✓ A50指数Baseline统计完成")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestA50IndexData)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("开始测试 A50IndexData 类")
    print("=" * 60)
    print(f"数据路径: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index_data', 'a50_index.csv')}")
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
