"""
用户股票账户基类模块
提供账户抽象基类和通用工具函数
"""

from abc import ABC, abstractmethod
import numpy as np
import pandas as pd


def create_dataframes(daily_profits, index2date):
    """
    创建收益统计的DataFrame
    
    Args:
        daily_profits: 每只股票的每日收益字典 {stock_code: [profit1, profit2, ...]}
        index2date: 索引到日期的映射 {index: date}
    
    Returns:
        df_1: 包含stock_code, date, profits三列的DataFrame
        df_2: 包含stock_code, total_profit两列的DataFrame（按总收益降序排列）
    """
    # 创建一个空列表，用于存储每只股票的三列数据（stock_code, date, profits）
    data_list_1 = []
    # 创建一个空字典，用于存储每只股票的总收益（stock_code, total_profit）
    total_profits_dict = {}

    for stock_code, daily_profit_list in daily_profits.items():
        for i, profit in enumerate(daily_profit_list):
            date = index2date[i]
            data_list_1.append([stock_code, date, profit])

            if stock_code not in total_profits_dict:
                total_profits_dict[stock_code] = profit
            else:
                total_profits_dict[stock_code] += profit

    # 创建第一个DataFrame，包含stock_code, date, profits三列
    df_1 = pd.DataFrame(data_list_1, columns=["stock_code", "date", "profits"])

    # 创建第二个DataFrame，包含stock_code, total_profit两列
    df_2 = pd.DataFrame(list(total_profits_dict.items()), columns=["stock_code", "total_profit"])
    df_2 = df_2.sort_values(by="total_profit", ascending=False)
    return df_1, df_2


def revert_code(code):
    """
    反转股票代码格式
    例如：SH.600000 -> 600000.SH
    
    Args:
        code: 股票代码
    
    Returns:
        str: 反转后的股票代码
    """
    parts = code.split('.')
    return f"{parts[1]}.{parts[0]}"


def remove_market(code):
    """
    移除股票代码中的市场标识
    例如：SH.600000 -> 600000
    
    Args:
        code: 股票代码
    
    Returns:
        str: 不含市场标识的股票代码
    """
    parts = code.split('.')
    return f"{parts[1]}"


def rebuild_h(h, code2index, qty_info):
    """
    根据持仓信息重建持仓数组
    
    Args:
        h: 原持仓数组
        code2index: 股票代码到索引的映射
        qty_info: 持仓信息字典 {code: qty}
    
    Returns:
        np.array: 新的持仓数组
    """
    new_h = np.zeros_like(h)
    for code, qty in qty_info.items():
        if code in code2index:
            index = code2index[code]
            new_h[index] = qty
    return new_h


def get_buylist_and_selllist(action, code2index):
    """
    从交易动作中提取买入和卖出列表
    
    Args:
        action: 交易动作数组
        code2index: 股票代码到索引的映射
    
    Returns:
        tuple: (买入列表字典, 卖出列表字典)
    """
    import json
    
    buylist = {}
    selllist = {}

    for code, index in code2index.items():
        qty = action[index]
        reverted_code = revert_code(code)

        if qty > 0:
            buylist[reverted_code] = qty
        elif qty < 0:
            selllist[reverted_code] = abs(qty)
    
    print('selllist=', json.dumps(selllist))
    print('buylist=', json.dumps(buylist))
    
    return buylist, selllist


class UserStockAccount(ABC):
    """
    用户股票账户抽象基类
    定义了股票账户的基本接口和通用功能
    """
    
    def __init__(self, code2index):
        """
        初始化账户
        
        Args:
            code2index: 股票代码到索引的映射字典
        """
        self.code2index = code2index  # 股票代码到index的映射
        self.b = 0  # 当前剩余现金
        self.h = np.zeros(len(code2index), dtype=float)  # 股票持有数量
        self.closings = np.zeros(len(code2index), dtype=float)  # 收盘价
        self.action_history = []  # 交易记录
        self.h_history = []  # 股票持有数量历史
        self.b_history = []  # 剩余现金历史
        self.closings_history = []  # 收盘价历史
        self.total_assets_history = []  # 总资产历史
        self.profits_history = []  # 每日收益
    
    @abstractmethod
    def cur_holds(self):
        """
        获取当前持仓信息
        
        Returns:
            tuple: (现金余额, 股票持仓数组)
        """
        raise ValueError("not implemented")
    
    @abstractmethod
    def take_action(self, action, **kwargs):
        """
        执行交易动作
        
        Args:
            action: 交易动作数组
            **kwargs: 其他参数
        """
        raise ValueError("not implemented")
    
    def statisic(self):
        """
        统计每只股票的收益情况
        
        计算逻辑：
        前一条价格p1，前一天持仓h1
        当天价格p2，当天持仓h2，当日买卖数量n（n为负数表示卖出，并且买卖价格为p2）
        则当日该股票的收益为：p2 * h1 - p1 * h1
        
        Returns:
            tuple: (每日收益DataFrame, 总收益DataFrame)
        """
        num_days = len(self.closings_history)
        daily_profits = {}
        index2date = {}
        
        for code, index in self.code2index.items():
            daily_profits[code] = []
            for i in range(1, num_days):
                p1 = self.closings_history[i - 1][index]
                h1 = self.h_history[i - 1][index]
                p2 = self.closings_history[i][index]
                h2 = self.h_history[i][index]
                n = self.action_history[i][1][index]
                index2date[i-1] = self.action_history[i][0]
                daily_profits[code].append(p2 * h1 - p1 * h1)
        
        return create_dataframes(daily_profits, index2date)
