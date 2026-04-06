"""
本地模拟股票账户实现
用于回测和模拟交易
"""

import numpy as np
from .user_stock_account import UserStockAccount


class LocalUserStockAccount(UserStockAccount):
    """
    本地模拟股票账户
    用于回测和模拟交易
    """
    
    def __init__(self, code2index):
        """
        初始化本地账户
        
        Args:
            code2index: 股票代码到索引的映射字典
        """
        super().__init__(code2index)
        self.b = 1e6  # 初始资金100万

    def cur_holds(self):
        """
        获取当前持仓信息
        
        Returns:
            tuple: (现金余额, 股票持仓数组)
        """
        return self.b, self.h
    
    def take_action(self, date, action, **kwargs):
        """
        执行交易动作
        
        Args:
            date: 交易日期
            action: 交易动作数组（正数表示买入，负数表示卖出）
            **kwargs: 包含spend（花费）、costs（手续费）、cash_and_sell_stock_money（可用资金）、closings（收盘价）
        """
        # 初始化历史记录
        if len(self.action_history) == 0:
            self.action_history.append(None)
            self.h_history.append(self.h)
            self.b_history.append(self.b)
            self.total_assets_history.append(self.b)
            self.closings_history.append(self.closings)
            self.profits_history.append(0)
        
        spend, costs, coh = kwargs["spend"], kwargs["costs"], kwargs["cash_and_sell_stock_money"]
        self.closeings = kwargs["closings"]
        
        # 检查资金是否充足
        flag = (spend + costs) > coh
        self.action_history.append((date, action, flag, spend, costs, coh))
        
        # 如果资金充足，执行交易
        if not flag:
            self.h = self.h + action
            self.b = coh - spend - costs
        
        # 更新历史记录
        self.h_history.append(self.h)
        self.b_history.append(self.b)
        self.closings_history.append(self.closeings)
        self.total_assets_history.append(self.b + np.dot(self.h, self.closeings))
        self.profits_history.append(self.total_assets_history[-1] - self.total_assets_history[-2])
