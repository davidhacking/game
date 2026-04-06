import unittest
import os
import sys
import pandas as pd

# 添加项目根目录到sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from data.a50_data import A50Data
from data.data import DataInitParam, StockCodeList


class TestA50Data(unittest.TestCase):
    """A50Data类的测试用例"""
    
    def setUp(self):
        """测试前的准备工作 - 只初始化一次数据"""
        # 设置默认的数据路径为当前文件夹/stock_data
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_path = os.path.join(current_dir, "stock_data")
        
        # 创建测试用的DataInitParam
        self.param = DataInitParam(
            path=self.data_path,
            stock_codes=None  # 使用默认的SSE_50股票代码，其他参数使用默认值
        )
        
        # 初始化A50Data实例（只拉取一次数据）
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
    
    def test_init(self):
        """测试A50Data初始化"""
        self.assertIsNotNone(self.a50_data)
        self.assertIsNotNone(self.a50_data.stock_mgr)
        print("✓ A50Data初始化测试通过")
    
    def test_get_train_data(self):
        """测试获取训练数据"""
        train_data = self.a50_data.get_train_data()
        
        self.assertIsNotNone(train_data)
        self.assertIsInstance(train_data, pd.DataFrame)
        
        if not train_data.empty:
            # 检查是否包含必要的列
            self.assertIn('date', train_data.columns)
            print(f"✓ 训练数据获取成功，共 {len(train_data)} 条记录")
        else:
            print("⚠ 训练数据为空")
    
    def test_get_test_data(self):
        """测试获取测试数据"""
        test_data = self.a50_data.get_test_data()
        
        self.assertIsNotNone(test_data)
        self.assertIsInstance(test_data, pd.DataFrame)
        
        if not test_data.empty:
            # 检查是否包含必要的列
            self.assertIn('date', test_data.columns)
            print(f"✓ 测试数据获取成功，共 {len(test_data)} 条记录")
        else:
            print("⚠ 测试数据为空")
    
    def test_data_split(self):
        """测试训练集和测试集的数据分割"""
        train_data = self.a50_data.get_train_data()
        test_data = self.a50_data.get_test_data()
        
        self.assertIsNotNone(train_data)
        self.assertIsNotNone(test_data)
        
        # 验证训练集和测试集没有重叠
        if not train_data.empty and not test_data.empty:
            train_dates = set(train_data['date'].unique())
            test_dates = set(test_data['date'].unique())
            overlap = train_dates & test_dates
            self.assertEqual(len(overlap), 0, "训练集和测试集存在日期重叠")
            print(f"✓ 数据分割正确，训练集 {len(train_dates)} 天，测试集 {len(test_dates)} 天，无重叠")

    # 在tests目录下执行: python -m unittest test_a50_data.TestA50Data.test_debug
    def test_debug(self):
        """测试debug方法"""
        # 调用debug方法，应该不会抛出异常
        print("\n--- Debug输出 ---")
        self.a50_data.debug()
        print("--- Debug输出结束 ---\n")
        print("✓ Debug方法测试通过")

def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestA50Data)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("开始测试 A50Data 类")
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
