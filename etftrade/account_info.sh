#!/bin/bash
# 获取同花顺账户持仓信息, 保存到 results/account_info.json
cd /home/david/MF/trade_a50_v2
source .venv/bin/activate

RESULT_DIR=results
mkdir -p $RESULT_DIR

echo "获取账户信息..."
PORTFOLIO=$(PYTHONPATH=/home/david/MF/trade_a50_v2 python win_ctrl/ths_trader.py 2>/dev/null)

if [ -z "$PORTFOLIO" ]; then
    echo "ERROR: 无法获取持仓"
    exit 1
fi

# 保存到 results/account_info.json
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "$PORTFOLIO" | python -m json.tool > "$RESULT_DIR/account_info.json"
echo "$PORTFOLIO" | python -m json.tool > "$RESULT_DIR/account_info_${TIMESTAMP}.json"

echo "已保存:"
echo "  $RESULT_DIR/account_info.json (最新)"
echo "  $RESULT_DIR/account_info_${TIMESTAMP}.json (历史)"
echo ""
echo "$PORTFOLIO" | python -c "
import sys, json
d = json.load(sys.stdin)
print('余额: ¥%s' % '{:,.2f}'.format(d.get('balance', 0)))
pos = d.get('position', {})
total_val = sum(p.get('value', 0) for p in pos.values())
print('持仓: %d 只, 市值 ¥%s' % (len(pos), '{:,.2f}'.format(total_val)))
print('总资产: ¥%s' % '{:,.2f}'.format(d.get('balance', 0) + total_val))
print('')
for code, info in sorted(pos.items()):
    print('  %s  %6d股  均价%.3f  市值¥%s' % (
        code, info.get('quantity', 0), info.get('price', 0),
        '{:,.0f}'.format(info.get('value', 0))))
"
rm -rf home mlruns 2>/dev/null
