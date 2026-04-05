#!/usr/bin/env bash
set -euo pipefail

echo "========================================="
echo "  搜狗输入法安装脚本 - Ubuntu 22.04 x86_64"
echo "========================================="

# ---------- 1. 安装 fcitx 框架 ----------
echo ""
echo "[1/4] 安装 fcitx 及相关依赖..."
sudo apt update
sudo apt install -y fcitx fcitx-bin fcitx-table fcitx-config-gtk \
    fcitx-frontend-all fcitx-module-cloudpinyin fcitx-ui-classic \
    libqt5qml5 libqt5quick5 libqt5quickwidgets5 qml-module-qtquick2 \
    libgsettings-qt1

# ---------- 2. 下载搜狗输入法 ----------
echo ""
echo "[2/4] 下载搜狗输入法..."
SOGOU_DEB="/tmp/sogoupinyin.deb"

# 多个候选下载地址（搜狗 CDN 地址经常变化）
SOGOU_URLS=(
    "https://ime-sec.gtimg.com/202407/18c31a45/sogoupinyin_4.2.1.145_amd64.deb"
    "https://ime-sec.gtimg.com/202403/0cc1d948/sogoupinyin_4.2.1.145_amd64.deb"
)

# 验证已有文件是否为有效 deb 包
need_download=true
if [[ -f "$SOGOU_DEB" ]]; then
    if dpkg-deb --info "$SOGOU_DEB" &>/dev/null; then
        echo "已存在有效的 deb 文件，跳过下载"
        need_download=false
    else
        echo "已存在的文件无效，删除后重新下载..."
        rm -f "$SOGOU_DEB"
    fi
fi

if $need_download; then
    downloaded=false
    for url in "${SOGOU_URLS[@]}"; do
        echo "尝试下载: $url"
        if wget --timeout=30 -O "$SOGOU_DEB" "$url" 2>&1; then
            # 验证下载的文件是否为有效 deb
            if dpkg-deb --info "$SOGOU_DEB" &>/dev/null; then
                echo "✅ 下载成功并验证通过"
                downloaded=true
                break
            else
                echo "下载的文件无效，尝试下一个地址..."
                rm -f "$SOGOU_DEB"
            fi
        else
            rm -f "$SOGOU_DEB"
        fi
    done

    if ! $downloaded; then
        echo ""
        echo "========================================="
        echo "⚠️  自动下载失败！请手动下载："
        echo ""
        echo "  1. 浏览器打开: https://shurufa.sogou.com/linux"
        echo "  2. 点击下载 x86_64 版本的 deb 包"
        echo "  3. 将下载的文件复制到: $SOGOU_DEB"
        echo "     例如: cp ~/Downloads/sogoupinyin_*.deb $SOGOU_DEB"
        echo "  4. 重新运行此脚本"
        echo "========================================="
        exit 1
    fi
fi

# ---------- 3. 安装搜狗输入法 ----------
echo ""
echo "[3/4] 安装搜狗输入法..."
sudo dpkg -i "$SOGOU_DEB" || true
sudo apt install -f -y

# ---------- 4. 配置 fcitx 为默认输入法 ----------
echo ""
echo "[4/4] 配置 fcitx 为默认输入法框架..."

# 写入环境变量
PROFILE_CONTENT='
# Fcitx input method
export INPUT_METHOD=fcitx
export GTK_IM_MODULE=fcitx
export QT_IM_MODULE=fcitx
export XMODIFIERS=@im=fcitx
export SDL_IM_MODULE=fcitx
export GLFW_IM_MODULE=ibus
'

# 追加到 ~/.xprofile（避免重复）
XPROFILE="$HOME/.xprofile"
if [[ -f "$XPROFILE" ]] && grep -q "GTK_IM_MODULE=fcitx" "$XPROFILE"; then
    echo "~/.xprofile 已配置，跳过"
else
    echo "$PROFILE_CONTENT" >> "$XPROFILE"
    echo "已写入 ~/.xprofile"
fi

# 同时写入 ~/.profile
PROFILE="$HOME/.profile"
if [[ -f "$PROFILE" ]] && grep -q "GTK_IM_MODULE=fcitx" "$PROFILE"; then
    echo "~/.profile 已配置，跳过"
else
    echo "$PROFILE_CONTENT" >> "$PROFILE"
    echo "已写入 ~/.profile"
fi

# 使用 im-config 设置 fcitx（如果可用）
if command -v im-config &>/dev/null; then
    im-config -n fcitx
    echo "已通过 im-config 设置 fcitx"
fi

# ---------- 完成 ----------
echo ""
echo "========================================="
echo "  ✅ 安装完成！"
echo ""
echo "  请执行以下操作："
echo "  1. 注销当前用户或重启电脑"
echo "  2. 登录后右上角应出现键盘图标"
echo "  3. 右键键盘图标 -> 设置 -> 添加搜狗拼音"
echo "  4. 使用 Ctrl+Space 切换输入法"
echo "========================================="
