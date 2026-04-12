#!/bin/bash
cd /home/david/MF/trade_a50_v2
source .venv/bin/activate
echo "获取持仓..."
PORTFOLIO=$(PYTHONPATH=/home/david/MF/trade_a50_v2 python win_ctrl/ths_trader.py 2>/dev/null)
if [ -z "$PORTFOLIO" ]; then
    echo "ERROR: 无法获取持仓"
    exit 1
fi
echo "$PORTFOLIO" | PYTHONPATH=/home/david/MF/trade_a50_v2 python scripts/predict.py --execute
rm -rf home mlruns 2>/dev/null
