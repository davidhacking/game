#!/bin/bash
# 关闭 Mac 休眠/关屏，防止长时间脚本运行被中断
# 用法：sudo ./disable_sleep.sh

set -e

echo "正在关闭休眠和自动关屏..."

# 电池供电
sudo pmset -b sleep 0
sudo pmset -b displaysleep 0
sudo pmset -b disksleep 0
sudo pmset -b standby 0
sudo pmset -b powernap 0

# 接电源
sudo pmset -c sleep 0
sudo pmset -c displaysleep 0
sudo pmset -c disksleep 0
sudo pmset -c standby 0
sudo pmset -c powernap 0

echo ""
echo "当前设置："
pmset -g custom
echo ""
echo "✓ 休眠和关屏已关闭"
echo "  运行完脚本后请执行: sudo ./restore_sleep.sh"
