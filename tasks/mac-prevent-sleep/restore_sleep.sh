#!/bin/bash
# 恢复 Mac 原始休眠/关屏设置（2026-04-05 备份）
# 用法：sudo ./restore_sleep.sh

set -e

echo "正在恢复原始电源设置..."

# 电池供电
sudo pmset -b sleep 1
sudo pmset -b displaysleep 15
sudo pmset -b disksleep 10
sudo pmset -b hibernatemode 3
sudo pmset -b standby 1
sudo pmset -b powernap 1
sudo pmset -b lowpowermode 1
sudo pmset -b ttyskeepawake 1
sudo pmset -b lessbright 1
sudo pmset -b tcpkeepalive 1
sudo pmset -b womp 0
sudo pmset -b networkoversleep 0

# 接电源
sudo pmset -c sleep 1
sudo pmset -c displaysleep 10
sudo pmset -c disksleep 10
sudo pmset -c hibernatemode 3
sudo pmset -c standby 1
sudo pmset -c powernap 1
sudo pmset -c lowpowermode 1
sudo pmset -c ttyskeepawake 1
sudo pmset -c tcpkeepalive 1
sudo pmset -c womp 1
sudo pmset -c networkoversleep 0

echo ""
echo "当前设置："
pmset -g custom
echo ""
echo "✓ 已恢复原始电源设置"
