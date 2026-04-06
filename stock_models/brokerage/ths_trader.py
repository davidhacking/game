import easytrader
import requests
import json
from pywinauto import Application

from flask import Flask, request

app = Flask(__name__)
base_url = "http://127.0.0.1:5555/"

@app.route('/hello')
def hello():
    return "ok!"

@app.route('/balance_info')
def get_balance_info():
    user = easytrader.use('ths')
    user.connect(r"C:\同花顺软件\同花顺\xiadan.exe")
    return str(user.balance)

@app.route('/today_entrusts')
def get_today_entrusts():
    user = easytrader.use('ths')
    user.connect(r"C:\同花顺软件\同花顺\xiadan.exe")
    return str(user.today_entrusts)

@app.route('/today_trades')
def get_today_trades():
    user = easytrader.use('ths')
    user.connect(r"C:\同花顺软件\同花顺\xiadan.exe")
    return str(user.today_trades)

@app.route('/position_info')
def get_position_info():
    user = easytrader.use('ths')
    user.connect(r"C:\同花顺软件\同花顺\xiadan.exe")
    return str(user.position)

@app.route('/buy')
def handle_buy():
    code = request.args.get('code')
    qty = int(request.args.get('qty'))
    price = float(request.args.get('price'))
    user = easytrader.use('ths')
    user.connect(r"C:\同花顺软件\同花顺\xiadan.exe")
    res = user.buy(code, price=price, amount=qty)
    return json.dumps(res)

@app.route('/sell')
def handle_sell():
    code = request.args.get('code')
    qty = int(request.args.get('qty'))
    price = float(request.args.get('price'))
    user = easytrader.use('ths')
    user.connect(r"C:\同花顺软件\同花顺\xiadan.exe")
    res = user.sell(code, price=price, amount=qty)
    return json.dumps(res)

@app.route('/test')
def handle_test():
    user = easytrader.use('ths')
    user.connect(r"C:\同花顺软件\同花顺\xiadan.exe")
    user._app.top_window().print_control_identifiers()
    return "test"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5555)