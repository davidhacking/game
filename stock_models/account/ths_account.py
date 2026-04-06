"""
同花顺股票账户实现
通过同花顺交易接口进行实盘交易
"""

import time
import json
import os
from .user_stock_account import UserStockAccount, revert_code, remove_market, rebuild_h, get_buylist_and_selllist

# 同花顺相关导入
try:
    from utils import ths_trader
except ImportError:
    ths_trader = None

# 富途证券相关导入（用于获取价格）
try:
    from futu import OpenQuoteContext, SubType, RET_OK
    import pandas as pd
except ImportError:
    OpenQuoteContext = None
    SubType = None
    RET_OK = None
    pd = None


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


class ThsUserStockAccount(UserStockAccount):
    """
    同花顺股票账户
    通过同花顺交易接口进行实盘交易
    """
    
    def __init__(self, code2index, cache_dir="./cache"):
        """
        初始化同花顺账户
        
        Args:
            code2index: 股票代码到索引的映射字典
            cache_dir: 缓存目录路径，默认为 ./cache
        """
        super().__init__(code2index)
        self.close_dict = {}  # 收盘价字典
        self.cache_dir = cache_dir  # 缓存目录
        self.cache_file = os.path.join(cache_dir, "ths_account_cache.json")  # 缓存文件路径
        
        # 确保缓存目录存在
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def _save_cache(self, balance, position):
        """
        保存账户信息到本地缓存
        
        Args:
            balance: 资金余额
            position: 持仓信息字典
        """
        try:
            cache_data = {
                "balance": balance,
                "position": position,
                "timestamp": time.time()
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            print(f"账户信息已保存到缓存: {self.cache_file}")
        except Exception as e:
            print(f"保存缓存失败: {e}")
    
    def _load_cache(self):
        """
        从本地缓存加载账户信息
        
        Returns:
            tuple: (资金余额, 持仓信息字典) 或 (None, None)
        """
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                balance = cache_data.get("balance")
                position = cache_data.get("position")
                timestamp = cache_data.get("timestamp")
                # 将时间戳转换为可读格式
                from datetime import datetime
                timestamp_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else "未知"
                print(f"从缓存加载账户信息 (时间戳: {timestamp_str})")
                return balance, position
            else:
                print("缓存文件不存在")
                return None, None
        except Exception as e:
            print(f"加载缓存失败: {e}")
            return None, None

    def cur_holds(self):
        """
        从同花顺账户获取当前持仓信息
        如果获取失败，则从本地缓存读取
        
        Returns:
            tuple: (现金余额, 股票持仓数组)
        """
        # 尝试从同花顺接口获取信息
        balance = ths_trader.balance_info()
        qty_info = ths_trader.position_info()
        
        # 如果获取成功，保存到缓存
        if balance is not None and qty_info is not None:
            self.b = balance
            self.h = rebuild_h(self.h, self.code2index, qty_info)
            self._save_cache(balance, qty_info)
            print(f"ThsUserStockAccount cash={self.b} qty_info={qty_info} h={self.h}")
        else:
            # 获取失败，从缓存加载
            print("从同花顺接口获取信息失败，尝试从缓存加载...")
            cached_balance, cached_position = self._load_cache()
            
            if cached_balance is not None and cached_position is not None:
                self.b = cached_balance
                self.h = rebuild_h(self.h, self.code2index, cached_position)
                print(f"使用缓存数据: cash={self.b} qty_info={cached_position} h={self.h}")
            else:
                print("警告: 无法从接口或缓存获取账户信息，使用当前值")
        
        return self.b, self.h
    
    def take_action(self, date, action, **kwargs):
        """
        通过同花顺接口执行交易动作
        
        Args:
            date: 交易日期
            action: 交易动作数组
            **kwargs: 其他参数
        """
        print("close_dict=", self.close_dict)
        print("take_action=", action)
        buys, sells = get_buylist_and_selllist(action, self.code2index)
        
        # 先卖出
        for code, qty in sells.items():
            price = self.close_dict.get(revert_code(code), 0)
            price = cur_price(code)
            ths_trader.sell_stock(remove_market(code), price, int(qty))
            time.sleep(6)

        time.sleep(60)
        
        # 再买入
        for code, qty in buys.items():
            price = self.close_dict.get(revert_code(code), 0)
            price = cur_price(code)
            ths_trader.buy_stock(remove_market(code), price, int(qty))
