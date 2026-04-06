"""
富途证券股票账户实现
通过富途OpenAPI进行实盘或模拟交易
"""

import time
import pandas as pd
from .user_stock_account import UserStockAccount, revert_code, rebuild_h, get_buylist_and_selllist

# 富途证券相关导入
try:
    from futu import *
    from futu.common import *
except ImportError:
    # 如果导入失败，定义空的占位符以避免NameError
    OpenSecTradeContext = None
    OpenQuoteContext = None
    TrdMarket = None
    SecurityFirm = None
    TrdSide = None
    TrdEnv = None
    SubType = None
    RET_OK = None


def buy_cn_stock(code, price, qty, flag):
    """
    通过富途API买卖股票
    
    Args:
        code: 股票代码
        price: 价格
        qty: 数量
        flag: True表示买入，False表示卖出
    """
    print(f"buy_cn_stock code={code} qty={qty} price={price}, flag={flag}")
    trd_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.CN, host='127.0.0.1', port=11111, 
                                   security_firm=SecurityFirm.FUTUSECURITIES)
    ret, data = trd_ctx.unlock_trade('')  # 若使用真实账户下单，需先对账户进行解锁
    if ret != RET_OK:
        print("unlock_trade ret=", ret)
        trd_ctx.close()
        return
    
    trd_side = TrdSide.BUY if flag else TrdSide.SELL
    ret, data = trd_ctx.place_order(price=price, qty=qty, code=code, trd_side=trd_side, 
                                     trd_env=TrdEnv.REAL)
    if ret != RET_OK:
        print(f"buy place_order code={code} ret={ret}")
    
    trd_ctx.close()
    time.sleep(5)


def cur_price(code):
    """
    获取股票当前价格
    
    Args:
        code: 股票代码
    
    Returns:
        float: 当前价格
    """
    print(f"cur_price {code}")
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    ret_sub, err_message = quote_ctx.subscribe([code], [SubType.RT_DATA], subscribe_push=False)
    if ret_sub == RET_OK:
        ret, data = quote_ctx.get_rt_data(code)
        if ret == RET_OK:
            data['time'] = pd.to_datetime(data['time'])
            filtered_df = data[data['code'] == code]
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


class FutuUserStockAccount(UserStockAccount):
    """
    富途证券股票账户
    通过富途OpenAPI进行实盘或模拟交易
    """
    
    def __init__(self, code2index):
        """
        初始化富途账户
        
        Args:
            code2index: 股票代码到索引的映射字典
        """
        super().__init__(code2index)
        self.close_dict = {}  # 收盘价字典

    def cur_holds(self):
        """
        从富途账户获取当前持仓信息
        
        Returns:
            tuple: (现金余额, 股票持仓数组)
        """
        trd_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.HK, host='127.0.0.1', port=11111,
                                       security_firm=SecurityFirm.FUTUSECURITIES)
        ret, data = trd_ctx.accinfo_query(trd_env=TrdEnv.REAL)
        if ret != RET_OK:
            print("accinfo_query ret=", ret)
            trd_ctx.close()
            return self.b, self.h
        
        self.b = data["cash"][0]
        ret, data = trd_ctx.position_list_query()
        if ret != RET_OK:
            print("position_list_query error:", data)
            trd_ctx.close()
            return self.b, self.h
        
        # 检查持仓列表是否为空
        if data.shape[0] > 0:
            data['code'] = data['code'].apply(revert_code)
            qty_info = pd.Series(data.qty.values, index=data.code).to_dict()
            self.h = rebuild_h(self.h, self.code2index, qty_info)
            print(f"FutuUserStockAccount cash={self.b} qty_info={qty_info} h={self.h}")
        else:
            print(f"FutuUserStockAccount cash={self.b} 持仓为空")
        
        trd_ctx.close()
        return self.b, self.h
    
    def take_action(self, date, action, **kwargs):
        """
        通过富途API执行交易动作
        
        Args:
            date: 交易日期
            action: 交易动作数组
            **kwargs: 其他参数
        """
        print("close_dict=", self.close_dict)
        buys, sells = get_buylist_and_selllist(action, self.code2index)
        
        # 先卖出
        for code, qty in sells.items():
            price = self.close_dict.get(revert_code(code), 0)
            price = cur_price(code)
            buy_cn_stock(code, price, qty, False)
        
        # 再买入
        for code, qty in buys.items():
            price = self.close_dict.get(revert_code(code), 0)
            price = cur_price(code)
            buy_cn_stock(code, price, qty, True)
