import unittest
import os
import sys
import json
import numpy as np
from unittest.mock import patch, MagicMock

# 添加项目根目录到sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from account.ths_account import ThsUserStockAccount
from data.a50_data import A50Data
from data.data import DataInitParam
from config.stock_codes import SSE_50_EXT

# python -m unittest test_ths_account.TestThsUserStockAccountCurHolds
class TestThsUserStockAccountCurHolds(unittest.TestCase):
    """测试ThsUserStockAccount的cur_holds方法"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 设置数据路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_path = os.path.join(current_dir, "stock_data")
        
        # 计算日期
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = datetime(2009, 1, 1)
        split_date = end_date - timedelta(days=365)
        
        self.start_date = start_date.strftime('%Y-%m-%d')
        self.end_date = end_date.strftime('%Y-%m-%d')
        self.split_date = split_date.strftime('%Y-%m-%d')
        
        # 通过A50Data类获取code2index映射
        param = DataInitParam(
            path=self.data_path,
            stock_codes=SSE_50_EXT,
            start_date=self.start_date,
            end_date=self.end_date,
            split_date=self.split_date
        )
        a50_data = A50Data(param)
        df = a50_data.get_train_data()
        
        # 从数据中获取股票列表
        stock_col = 'tic'
        assets = df[stock_col].unique()
        self.code2index = {
            stock: i for i, stock in enumerate(assets)
        }
        print(f"code2index: {self.code2index}")
        self.account = ThsUserStockAccount(self.code2index)
    
    def test_cur_holds(self):
        result = self.account.cur_holds()
        self.assertIsNotNone(result)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestThsUserStockAccountCurHolds))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("测试：同花顺股票账户 (ThsUserStockAccount)")
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
