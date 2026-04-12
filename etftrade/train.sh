#!/bin/bash
cd /home/david/MF/trade_a50_v2
source .venv/bin/activate
# 用法: ./train.sh [split_date]
# 例: ./train.sh 20250101
PYTHONPATH=/home/david/MF/trade_a50_v2 python scripts/train.py --split_date ${1:-20250101}
rm -rf home mlruns 2>/dev/null
