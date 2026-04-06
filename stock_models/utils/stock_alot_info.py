import multiprocessing
import pandas as pd
import numpy as np
from futu import *
from futu.common import *


def revert_code(code):
    """将股票代码格式从 'A.B' 转换为 'B.A'"""
    parts = code.split('.')
    return f"{parts[1]}.{parts[0]}"


class StockAlotInfo:
    """股票每手股数信息单例类
    
    用于管理股票的每手股数（lot_size）和股票名称到代码的映射。
    使用单例模式确保全局只有一个实例。
    采用延迟加载策略，在首次访问数据时才从API获取。
    
    Attributes:
        alot_info: 股票代码到每手股数的映射字典
        name2code: 股票名称到代码的映射字典
    """
    _instance = None
    _lock = multiprocessing.Lock()
    
    def __init__(self):
        """初始化实例，但不立即加载数据"""
        self.alot_info = None
        self.name2code = None
    
    def load_data(self):
        """延迟加载股票信息，从富途API获取数据"""
        if self.alot_info is not None:
            return
        
        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        ret, data = quote_ctx.get_user_security("stock_rl")
        if ret == RET_OK:
            data['code'] = data['code'].apply(revert_code)
            self.alot_info = pd.Series(data.lot_size.values, index=data.code).to_dict()
            self.name2code = pd.Series(data.name.values, index=data.code).to_dict()
            print(f"成功加载股票信息: 共 {len(self.alot_info)} 只股票")
            print(f"股票代码示例: {list(self.alot_info.keys())[:5]}")
        else:
            print('error:', data)
            self.alot_info = {}
            self.name2code = {}
        quote_ctx.close()


    @classmethod
    def get_instance(cls):
        """获取单例实例（线程安全）"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance.load_data()  # 初始化数据
        return cls._instance
    
    def set(self, code, alot):
        """设置指定股票代码的每手股数"""
        self.alot_info[code] = alot
    
    def get(self, code):
        """获取指定股票代码的每手股数
        
        Args:
            code: 股票代码
            
        Returns:
            每手股数，如果找不到则返回默认值100
        """
        if code not in self.alot_info:
            print(f"error: can not find code {code} in stock_rl")
            return 100
        return self.alot_info[code]
    
    def batch_get(self, codes):
        """批量获取多个股票代码的每手股数
        
        Args:
            codes: 股票代码列表或数组
            
        Returns:
            numpy数组，包含每个股票的每手股数，找不到的返回默认值100
        """
        values = [self.alot_info.get(code, 100) for code in codes]
        return np.array(values, dtype=int)
    
    def set_name_code(self, name, code):
        """设置股票名称到代码的映射"""
        self.name2code[name] = code
    
    def get_code_by_name(self, name):
        """根据股票名称获取股票代码
        
        Args:
            name: 股票名称
            
        Returns:
            股票代码，如果找不到则返回0
        """
        if name not in self.name2code:
            print(f"error: can not find name {name} in stock_rl")
            return 0
        return self.name2code[name]
