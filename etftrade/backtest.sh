#!/bin/bash
cd /home/david/MF/trade_a50_v2
source .venv/bin/activate
# 用法: ./backtest.sh [开始日期] [ETF代码] [初始资金]
# 例: ./backtest.sh 20260101 SH.588000 500000
# 默认: split_date/ETF from meta.json, 资金100万
PYTHONPATH=/home/david/MF/trade_a50_v2 python scripts/backtest.py ${1:+--start_date $1} ${2:+--etf $2} ${3:+--cash $3}
rm -rf home mlruns 2>/dev/null
