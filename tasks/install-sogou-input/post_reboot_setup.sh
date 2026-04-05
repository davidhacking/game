#!/usr/bin/env bash
set -euo pipefail

echo "========================================="
echo "  搜狗输入法 - 重启后配置脚本"
echo "========================================="

FCITX_PROFILE="$HOME/.config/fcitx/profile"

# ---------- 1. 检查 fcitx 是否运行 ----------
echo ""
echo "[1/3] 检查 fcitx 运行状态..."
if ! pgrep -x fcitx > /dev/null; then
    echo "fcitx 未运行，尝试启动..."
    fcitx -r -d
    sleep 2
fi

if pgrep -x fcitx > /dev/null; then
    echo "✅ fcitx 正在运行"
else
    echo "❌ fcitx 启动失败，请检查安装是否正确"
    exit 1
fi

# ---------- 2. 检查搜狗是否已安装 ----------
echo ""
echo "[2/3] 检查搜狗输入法..."
if dpkg -l sogoupinyin &>/dev/null; then
    echo "✅ 搜狗输入法已安装"
else
    echo "❌ 搜狗输入法未安装，请先运行 install_sogou.sh"
    exit 1
fi

# ---------- 3. 启用搜狗拼音 ----------
echo ""
echo "[3/3] 启用搜狗拼音输入法..."
if [[ ! -f "$FCITX_PROFILE" ]]; then
    echo "❌ fcitx 配置文件不存在: $FCITX_PROFILE"
    echo "   请先注销/重启一次让 fcitx 生成配置文件"
    exit 1
fi

if grep -q "sogoupinyin:True" "$FCITX_PROFILE"; then
    echo "搜狗拼音已经是启用状态，无需修改"
else
    sed -i 's/sogoupinyin:False/sogoupinyin:True/' "$FCITX_PROFILE"
    # 将搜狗拼音移到列表靠前位置（紧跟 us 键盘之后）
    # 先检查是否需要调整顺序
    if grep -q "fcitx-keyboard-us:True,sogoupinyin:True" "$FCITX_PROFILE"; then
        echo "搜狗拼音已在正确位置"
    elif grep -q "sogoupinyin:True" "$FCITX_PROFILE"; then
        # 从当前位置删除，插入到 us 键盘后面
        sed -i 's/sogoupinyin:True,//' "$FCITX_PROFILE"
        sed -i 's/fcitx-keyboard-us:True,/fcitx-keyboard-us:True,sogoupinyin:True,/' "$FCITX_PROFILE"
    fi
    echo "✅ 已启用搜狗拼音"
fi

# 重载 fcitx 配置
fcitx-remote -r
echo "✅ 已重载 fcitx 配置"

# ---------- 完成 ----------
echo ""
echo "========================================="
echo "  ✅ 配置完成！"
echo ""
echo "  使用方法："
echo "  - Ctrl+Space 切换中/英文输入法"
echo "  - 右上角键盘图标也可点击切换"
echo "========================================="
