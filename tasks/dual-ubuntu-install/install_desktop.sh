#!/bin/bash
#
# 为 Ubuntu2 安装完整桌面环境
# 用法：./install_desktop.sh
# 前提：Ubuntu2 已启动并可通过 SSH 连接
#

set -e

REMOTE="david@192.168.1.2"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }

# ============================================================
info "1. 确认当前在 Ubuntu2"
echo ""

ssh -t "$REMOTE" "hostname && cat /etc/os-release | head -2"

echo ""
read -p "确认是 ubuntu2？(yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "请先启动进入 Ubuntu2。"
    exit 1
fi

# ============================================================
echo ""
info "2. 安装完整桌面环境（需要较长时间，请耐心等待）"
warn "预计下载 2-3GB，安装 15-30 分钟"
echo ""

ssh -t "$REMOTE" "
sudo apt update && \
sudo DEBIAN_FRONTEND=noninteractive apt install -y ubuntu-desktop && \
echo '桌面环境安装完成'
"

# ============================================================
echo ""
info "3. 设置默认启动到图形界面"
echo ""

ssh -t "$REMOTE" "
sudo systemctl set-default graphical.target
echo '已设置为图形界面启动'
"

# ============================================================
echo ""
info "4. 安装完成，重启生效"
echo ""

read -p "现在重启？(yes/no): " REBOOT
if [ "$REBOOT" = "yes" ]; then
    ssh -t "$REMOTE" "sudo reboot"
    echo ""
    info "已重启，等待系统启动后会进入桌面登录界面"
else
    echo ""
    info "稍后手动重启即可：ssh -t $REMOTE \"sudo reboot\""
fi
