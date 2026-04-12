#!/bin/bash
cd /home/david/MF/trade_a50_v2
source .venv/bin/activate

EXECUTE_FLAG=""
# 检查是否有 --execute 参数
for arg in "$@"; do
    if [ "$arg" = "--execute" ]; then
        EXECUTE_FLAG="--execute"
    fi
done

if [ -n "$1" ] && [ -f "$1" ]; then
    PYTHONPATH=/home/david/MF/trade_a50_v2 python scripts/predict.py --portfolio "$1" $EXECUTE_FLAG
elif [ ! -t 0 ]; then
    PYTHONPATH=/home/david/MF/trade_a50_v2 python scripts/predict.py $EXECUTE_FLAG
else
    echo "Fetching portfolio from THS..."
    PORTFOLIO=$(PYTHONPATH=/home/david/MF/trade_a50_v2 python win_ctrl/ths_trader.py 2>/dev/null)
    if [ -n "$PORTFOLIO" ]; then
        echo "$PORTFOLIO" | PYTHONPATH=/home/david/MF/trade_a50_v2 python scripts/predict.py $EXECUTE_FLAG
    else
        echo "ERROR: 无法获取持仓"
        exit 1
    fi
fi
rm -rf home mlruns 2>/dev/null
