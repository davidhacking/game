import requests
import json
import argparse
import time
import pandas as pd
from futu import *
from futu.common import *
from utils.stock_alot_info import revert_code

base_url = "http://127.0.0.1:5555/"

def balance_info():
    url = base_url + "balance_info"
    try:
        response = requests.get(url)
        response.raise_for_status()
        rt = response.text
        response_text = rt.replace("'", '"')
        # print("balance_info rsp: " + response_text)
        data = json.loads(response_text)
        return data["可用金额"]
    except Exception as e:
        print(f"balance_info failed: {e}")
        return None

def today_trades():
    url = base_url + "today_trades"
    try:
        response = requests.get(url)
        response.raise_for_status()
        rt = response.text
        response_text = rt.replace("'", '"')
        data = json.loads(response_text)
        buys = dict()
        sells = dict()
        for item in data:
            code = item['证券代码']
            num = item['成交数量']
            market = 'SH' if item['交易市场'] == '上海' else 'SZ'
            if item['买卖'] == '证券卖出':
                sells[market + "." + code] = sells.get(market + "." + code, 0) + num
            else:
                buys[market + "." + code] = buys.get(market + "." + code, 0) + num
        return {'buy': buys, 'sell': sells}
    except Exception as e:
        print(f"today_trades failed: {e}")

# 今日委托
def today_entrusts():
    url = base_url + "today_entrusts"
    try:
        response = requests.get(url)
        response.raise_for_status()
        rt = response.text
        print(rt)
        return rt
    except Exception as e:
        print(f"today_entrusts failed: {e}")

def position_info():
    url = base_url + "position_info"
    try:
        response = requests.get(url)
        response.raise_for_status()
        rt = response.text
        response_text = rt.replace("'", '"')
        # print("position_info rsp: " + response_text)
        data = json.loads(response_text)
        res = {}
        for item in data:
            market = 'SH' if item['交易市场'] == '上海' else 'SZ'
            res[item['证券代码'] + "." + market] = item['实际数量']
        
        # 如果返回空字典或所有持仓数量都为0，返回None
        if not res or all(qty == 0 for qty in res.values()):
            return None
        
        return res
    except Exception as e:
        print(f"position_info failed: {e}")
        return None

def buy_stock(code, price, qty):
    buy_info = f"buy?code={code}&qty={qty}&price={price}"
    url = base_url + buy_info
    print("buy_stock=", buy_info)
    try:
        response = requests.get(url)
        response.raise_for_status()
        rt = response.text
        print('buy_stock return=', rt)
        return
    except Exception as e:
        print(f"buy_stock failed: {e}")

def sell_stock(code, price, qty):
    sell_info = f"sell?code={code}&qty={qty}&price={price}"
    url = base_url + f"sell?code={code}&qty={qty}&price={price}"
    print("sell_stock=", sell_info)
    try:
        response = requests.get(url)
        response.raise_for_status()
        rt = response.text
        print('sell_stock return=', rt)
        return 0
    except Exception as e:
        print(f"sell_stock failed: {e}")
        return -1

def test():
    url = base_url + f"test"
    try:
        response = requests.get(url)
        response.raise_for_status()
        rt = response.text
        return rt
    except Exception as e:
        print(f"sell_stock failed: {e}")


def cur_price(code):
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    ret_sub, err_message = quote_ctx.subscribe([code], [SubType.RT_DATA], subscribe_push=False)
    if ret_sub == RET_OK:
        ret, data = quote_ctx.get_rt_data(code)
        if ret == RET_OK:
            data['time'] = pd.to_datetime(data['time'])
            filtered_df = data[data['code'] == code]
            latest_record = filtered_df.loc[filtered_df['time'].idxmax()]
            print(f"cur_price {code} {latest_record['cur_price']}")
            return latest_record['cur_price']
        else:
            return 0
    else:
        print('subscription failed', err_message)
    quote_ctx.close()
    return 0

def remove_market(code):
    parts = code.split('.')
    return f"{parts[1]}"

def complete_trade():
    """before call this func, you should revert order in ths"""
    res = today_trades()
    with open("/home/david/MF/github/StockRL/utils/selllist.json", 'r') as file:
        need_sell = json.load(file)
    with open("/home/david/MF/github/StockRL/utils/buylist.json", 'r') as file:
        need_buy = json.load(file)
    incomplete_buys = {}
    incomplete_sells = {}
    print(f"today_trades={res}")
    if len(res['buy'].keys()) == 0 and len(res['sell'].keys()) == 0:
        return
    for stock_code, amount in need_buy.items():
        if stock_code not in res['buy']:
            incomplete_buys[stock_code] = need_buy[stock_code]
        elif stock_code in res['buy'] and res['buy'][stock_code] != amount:
            incomplete_buys[stock_code] = amount - res['buy'][stock_code]

    for stock_code, amount in need_sell.items():
        if stock_code not in res['sell']:
            incomplete_sells[stock_code] = need_sell[stock_code]
        elif stock_code in res['sell'] and res['sell'][stock_code] != amount:
            incomplete_sells[stock_code] = amount - res['sell'][stock_code]
    print(f"incomplete_sells{len(incomplete_sells.keys())}={incomplete_sells}")
    print(f"incomplete_buys{len(incomplete_buys.keys())}={incomplete_buys}")
    time.sleep(30)
    i = 0
    for code, qty in incomplete_sells.items():
        price = cur_price(code)
        i += 1
        print(f"i={i}")
        sell_stock(remove_market(code), price, int(qty))
    time.sleep(60)
    i = 0
    for code, qty in incomplete_buys.items():
        price = cur_price(code)
        i += 1
        print(f"i={i}")
        buy_stock(remove_market(code), price, int(qty))
    print("finish")

def total_asset():
    """
    计算总资产 = 资金余额 + 持仓市值
    
    Returns:
        dict: 包含以下字段的JSON对象
            - total_asset: 总资产金额
            - balance: 资金余额
            - position: 持仓信息字典 {股票代码: {"quantity": 数量, "price": 价格, "value": 市值}}
            - cur_price: 各股票当前价格字典 {股票代码: 价格}
    """
    try:
        # 获取资金余额
        balance = balance_info()
        if balance is None:
            print("获取资金余额失败")
            balance = 0
        
        # 获取持仓信息
        positions = position_info()
        if positions is None:
            print("获取持仓信息失败")
            return {
                "total_asset": balance,
                "balance": balance,
                "position": {},
                "cur_price": {}
            }
        
        # 计算持仓市值和构建返回数据
        position_value = 0
        position_detail = {}
        price_dict = {}
        
        for stock_code, quantity in positions.items():
            # 获取当前股票价格
            price = cur_price(revert_code(stock_code))
            price_dict[stock_code] = price
            
            if price > 0:
                stock_value = price * quantity
                position_value += stock_value
                position_detail[stock_code] = {
                    "quantity": quantity,
                    "price": price,
                    "value": stock_value
                }
                print(f"持仓: {stock_code}, 数量: {quantity}, 价格: {price}, 市值: {stock_value}")
            else:
                print(f"获取股票 {stock_code} 价格失败")
                position_detail[stock_code] = {
                    "quantity": quantity,
                    "price": 0,
                    "value": 0
                }
        
        # 计算总资产
        total = balance + position_value
        print(f"资金余额: {balance}, 持仓市值: {position_value}, 总资产: {total}")
        
        return {
            "total_asset": total,
            "balance": balance,
            "position": position_detail,
            "cur_price": price_dict
        }
        
    except Exception as e:
        print(f"total_asset failed: {e}")
        return {
            "total_asset": 0,
            "balance": 0,
            "position": {},
            "cur_price": {}
        }
