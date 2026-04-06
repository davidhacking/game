"""
单元测试：测试 StockAlotInfo 类的 batch_get 功能
"""
import sys
import os
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import unittest
import numpy as np
from unittest.mock import patch, MagicMock
from utils.stock_alot_info import StockAlotInfo
from config.stock_codes import SSE_50
import pandas as pd

# python -m unittest test_stock_alot_info.TestStockAlotInfo
class TestStockAlotInfo(unittest.TestCase):
    """测试 StockAlotInfo 类的 batch_get 方法"""
    
    def setUp(self):
        """每个测试前重置单例实例"""
        StockAlotInfo._instance = None
    
    def tearDown(self):
        """每个测试后清理单例实例"""
        StockAlotInfo._instance = None
    
    @patch('utils.stock_alot_info.OpenQuoteContext')
    def test_batch_get_with_sse50_codes(self, mock_quote_ctx):
        """测试使用上证50股票代码批量获取每手股数"""
        # 模拟富途API返回的数据
        mock_ctx_instance = MagicMock()
        mock_quote_ctx.return_value = mock_ctx_instance
        
        # 获取上证50股票代码列表
        stock_codes = SSE_50.get_string_list()
        
        # 创建模拟数据，为每个股票设置不同的 lot_size
        mock_data = pd.DataFrame({
            'code': stock_codes,
            'lot_size': [100 * (i + 1) for i in range(len(stock_codes))],  # 100, 200, 300, ...
            'name': [f'股票{i}' for i in range(len(stock_codes))]
        })
        
        mock_ctx_instance.get_user_security.return_value = (0, mock_data)  # RET_OK = 0
        
        # 获取实例并测试 batch_get
        stock_info = StockAlotInfo.get_instance()
        
        # 测试批量获取前5个股票的 lot_size
        test_codes = stock_codes[:5]
        result = stock_info.batch_get(test_codes)
        
        # 验证结果
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), 5)
        self.assertEqual(result.dtype, int)
        
        # 验证返回的值是否正确
        expected = np.array([100, 100, 100, 100, 100], dtype=int)
        np.testing.assert_array_equal(result, expected)
        
        print(f"✓ 成功测试前5个股票代码: {test_codes}")
        print(f"✓ 返回的每手股数: {result}")
    
    @patch('utils.stock_alot_info.OpenQuoteContext')
    def test_batch_get_with_missing_codes(self, mock_quote_ctx):
        """测试批量获取时包含不存在的股票代码"""
        # 模拟富途API返回的数据
        mock_ctx_instance = MagicMock()
        mock_quote_ctx.return_value = mock_ctx_instance
        
        stock_codes = SSE_50.get_string_list()[:3]  # 只使用前3个
        
        mock_data = pd.DataFrame({
            'code': stock_codes,
            'lot_size': [100, 200, 300],
            'name': ['股票1', '股票2', '股票3']
        })
        
        mock_ctx_instance.get_user_security.return_value = (0, mock_data)
        
        stock_info = StockAlotInfo.get_instance()
        
        # 测试包含不存在的代码
        test_codes = stock_codes + ['999999.SH', '888888.SZ']
        result = stock_info.batch_get(test_codes)
        
        # 验证结果：前3个是实际值，后2个是默认值100
        expected = np.array([100, 100, 100, 100, 100], dtype=int)
        np.testing.assert_array_equal(result, expected)
        
        print(f"✓ 成功测试包含不存在代码的情况")
        print(f"✓ 返回的每手股数: {result}")
    
    @patch('utils.stock_alot_info.OpenQuoteContext')
    def test_batch_get_all_sse50_codes(self, mock_quote_ctx):
        """测试批量获取所有上证50股票代码"""
        # 模拟富途API返回的数据
        mock_ctx_instance = MagicMock()
        mock_quote_ctx.return_value = mock_ctx_instance
        
        stock_codes = SSE_50.get_string_list()
        
        # 为所有股票设置相同的 lot_size = 100
        mock_data = pd.DataFrame({
            'code': stock_codes,
            'lot_size': [100] * len(stock_codes),
            'name': [f'股票{i}' for i in range(len(stock_codes))]
        })
        
        mock_ctx_instance.get_user_security.return_value = (0, mock_data)
        
        stock_info = StockAlotInfo.get_instance()
        result = stock_info.batch_get(stock_codes)
        
        # 验证结果
        self.assertEqual(len(result), len(stock_codes))
        self.assertTrue(np.all(result == 100))
        
        print(f"✓ 成功测试所有{len(stock_codes)}个上证50股票代码")
        print(f"✓ 所有股票的每手股数均为: 100")


if __name__ == '__main__':
    unittest.main()
