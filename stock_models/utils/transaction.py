"""
交易相关工具函数
"""

import numpy as np
from futu import OpenQuoteContext, SubType, RET_OK
import pandas as pd
from utils.stock_alot_info import StockAlotInfo, revert_code


def buy_cost_pct_func(total):
    """买入手续费计算函数"""
    return 0


def sell_cost_pct_func(total):
    """卖出手续费计算函数"""
    return total * 0.0005


def fixed_fee_func(total):
    """固定费用计算函数"""
    fee = total * 0.0002854
    return max(5, fee)


def cur_price(code):
    """
    获取股票当前价格
    
    Args:
        code: 股票代码（格式：600000.SH）
    
    Returns:
        float: 当前价格
    """
    print(f"cur_price {code}")
    # 将股票代码转换为富途API格式（600000.SH -> SH.600000）
    futu_code = revert_code(code)
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    ret_sub, err_message = quote_ctx.subscribe([futu_code], [SubType.RT_DATA], subscribe_push=False)
    if ret_sub == RET_OK:
        ret, data = quote_ctx.get_rt_data(futu_code)
        if ret == RET_OK:
            data['time'] = pd.to_datetime(data['time'])
            filtered_df = data[data['code'] == futu_code]
            latest_record = filtered_df.loc[filtered_df['time'].idxmax()]
            quote_ctx.close()
            return latest_record['cur_price']
        else:
            quote_ctx.close()
            return 0
    else:
        print('subscription failed', err_message)
        quote_ctx.close()
        return 0


class TransactionManager:
    """
    交易管理器类，负责处理交易相关的计算
    """
    
    def __init__(self, actions: np.ndarray, cash_on_hand: float, holdings: np.ndarray, 
                 hmax: int = 5000,
                 code2index: dict = None, normalize_buy_sell: bool = True,
                 buy_cost_pct: float = 3e-3, sell_cost_pct: float = 3e-3,
                 fixed_fee: float = 0, use_func: bool = True):
        """
        初始化交易管理器
        
        Args:
            actions: 动作数组，范围在[-1, 1]之间
            cash_on_hand: 当前现金
            holdings: 当前持仓数组
            hmax: 最大持仓数量
            code2index: 股票代码到索引的映射字典
            normalize_buy_sell: 是否按每手股数归一化买卖数量
            buy_cost_pct: 买入手续费比例
            sell_cost_pct: 卖出手续费比例
            fixed_fee: 固定费用
            use_func: 是否使用函数计算手续费
        """
        self.actions = actions
        self.cash_on_hand = cash_on_hand
        self.holdings = holdings
        self.hmax = hmax
        self.normalize_buy_sell = normalize_buy_sell
        self.buy_cost_pct = buy_cost_pct
        self.sell_cost_pct = sell_cost_pct
        self.fixed_fee = fixed_fee
        self.use_func = use_func
        
        # 构建 closings：获取所有股票的当前价格
        if code2index is None:
            self.code2index = {
                '000100.SZ': 0, '600000.SH': 1, '600009.SH': 2, '600016.SH': 3, '600028.SH': 4,
                '600030.SH': 5, '600031.SH': 6, '600036.SH': 7, '600048.SH': 8, '600050.SH': 9,
                '600104.SH': 10, '600196.SH': 11, '600276.SH': 12, '600309.SH': 13, '600519.SH': 14,
                '600547.SH': 15, '600570.SH': 16, '600585.SH': 17, '600588.SH': 18, '600690.SH': 19,
                '600703.SH': 20, '600745.SH': 21, '600887.SH': 22, '600918.SH': 23, '601012.SH': 24,
                '601066.SH': 25, '601088.SH': 26, '601138.SH': 27, '601166.SH': 28, '601186.SH': 29,
                '601211.SH': 30, '601236.SH': 31, '601288.SH': 32, '601318.SH': 33, '601319.SH': 34,
                '601336.SH': 35, '601398.SH': 36, '601601.SH': 37, '601628.SH': 38, '601668.SH': 39,
                '601688.SH': 40, '601816.SH': 41, '601818.SH': 42, '601857.SH': 43, '601888.SH': 44,
                '601933.SH': 45, '603160.SH': 46, '603259.SH': 47, '603288.SH': 48, '603501.SH': 49,
                '603986.SH': 50
            }
        else:
            self.code2index = code2index
        
        # 获取所有股票代码（按索引顺序）
        index2code = {v: k for k, v in code2index.items()}
        codes = [index2code[i] for i in range(len(code2index))]
        
        # 获取当前价格
        self.closings = np.array([cur_price(code) for code in codes])
    
    def get_transactions(self) -> np.ndarray:
        """
        获取实际交易的股数
        
        Returns:
            np.ndarray: 实际交易的股数数组
        """
        # 将动作乘以最大持仓数量
        actions = self.actions * self.hmax
        
        # 收盘价为 0 的不进行交易
        actions = np.where(self.closings > 0, actions, 0)
        
        # 去除被除数为 0 的警告
        out = np.zeros_like(actions)
        zero_or_not = self.closings != 0
        actions = np.divide(actions, self.closings, out=out, where=zero_or_not)
        
        # 如果需要按每手股数归一化
        if self.normalize_buy_sell:
            # 获取所有股票代码（按索引顺序）
            index2code = {v: k for k, v in self.code2index.items()}
            codes = [index2code[i] for i in range(len(self.code2index))]
            # 获取每手股数信息
            assets_alot = StockAlotInfo.get_instance().batch_get(codes)
            actions = np.sign(actions) * (np.abs(actions) // assets_alot) * assets_alot
        
        # 不能卖的比持仓的多
        actions = np.maximum(actions, -np.array(self.holdings))
        
        # 将 -0 的值全部置为 0
        actions[actions == -0] = 0
        
        return actions
    
    def get_spend_and_rest_money(self, transactions: np.ndarray):
        """
        计算交易花费和剩余现金
        
        Args:
            transactions: 交易股数数组
        
        Returns:
            tuple: (spend, costs, coh) - 买入花费、总手续费、剩余现金
        """
        sells = -np.clip(transactions, -np.inf, 0)
        proceeds = np.dot(sells, self.closings)
        
        if self.use_func:
            costs = sell_cost_pct_func(proceeds) + fixed_fee_func(proceeds)
        else:
            costs = proceeds * self.sell_cost_pct + self.fixed_fee
        
        coh = self.cash_on_hand + proceeds  # 计算现金的数量
        buys = np.clip(transactions, 0, np.inf)
        spend = np.dot(buys, self.closings)
        
        if self.use_func:
            costs += buy_cost_pct_func(spend) + fixed_fee_func(spend)
        else:
            costs += spend * self.buy_cost_pct + self.fixed_fee
        
        return spend, costs, coh
