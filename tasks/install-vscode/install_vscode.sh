#!/usr/bin/env bash
set -euo pipefail

echo "========================================="
echo "  VS Code 安装脚本 - Ubuntu 22.04 x86_64"
echo "========================================="

# ---------- 检查是否已安装 ----------
if command -v code &>/dev/null; then
    echo "VS Code 已安装: $(code --version | head -1)"
    echo "无需重复安装"
    exit 0
fi

# ---------- 1. 安装依赖 & 添加 GPG 密钥 ----------
echo ""
echo "[1/3] 安装依赖并添加微软 GPG 密钥..."
sudo apt update
sudo apt install -y wget gpg apt-transport-https

wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /tmp/packages.microsoft.gpg
sudo install -D -o root -g root -m 644 /tmp/packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg
rm -f /tmp/packages.microsoft.gpg

# ---------- 2. 添加 APT 仓库 ----------
echo ""
echo "[2/3] 添加微软 APT 仓库..."
echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" | \
    sudo tee /etc/apt/sources.list.d/vscode.list > /dev/null

# ---------- 3. 安装 VS Code ----------
echo ""
echo "[3/3] 安装 VS Code..."
sudo apt update
sudo apt install -y code

# ---------- 验证 ----------
echo ""
echo "========================================="
if command -v code &>/dev/null; then
    echo "  ✅ VS Code 安装成功！"
    echo "  版本: $(code --version | head -1)"
    echo ""
    echo "  启动: code"
    echo "  打开项目: code /path/to/project"
else
    echo "  ❌ 安装失败，请检查错误信息"
fi
echo "========================================="
