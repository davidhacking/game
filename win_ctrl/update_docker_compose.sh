#!/usr/bin/env bash
# 在 Ubuntu（192.168.1.2）上运行
# 作用：给 Windows Docker 容器的 docker-compose.yml 添加 2222:22 端口映射，然后重启容器
#
# 用法：bash update_docker_compose.sh

set -e

COMPOSE_FILE="$HOME/windows-docker/docker-compose.yml"

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "错误：找不到 $COMPOSE_FILE"
    echo "请先运行 Windows Docker 安装脚本：tasks/dual-ubuntu-install/install-windows-docker/install.sh"
    exit 1
fi

echo "=== 更新 Windows Docker 端口映射 ==="
echo "目标文件：$COMPOSE_FILE"
echo ""

# 检查 2222:22 是否已存在
if grep -q "2222:22" "$COMPOSE_FILE"; then
    echo "端口映射 2222:22 已存在，无需更新。"
else
    echo "[1/2] 添加 2222:22 端口映射..."

    # 备份原文件
    cp "$COMPOSE_FILE" "${COMPOSE_FILE}.bak"
    echo "  已备份原文件到 ${COMPOSE_FILE}.bak"

    # 在 ports 段插入 2222:22
    # 找到已有的 3389 端口映射行，在其后插入 2222:22
    if grep -q "3389:3389" "$COMPOSE_FILE"; then
        # 在 3389 行后面插入（保持缩进一致）
        INDENT=$(grep -o "^[[:space:]]*" <<< "$(grep '3389:3389' "$COMPOSE_FILE")")
        sed -i "/3389:3389/a\\${INDENT}- \"2222:22\"" "$COMPOSE_FILE"
    else
        # 没有 3389 行，在 ports: 段后面插入
        INDENT="      "  # 默认 6 空格缩进
        sed -i "/ports:/a\\${INDENT}- \"2222:22\"" "$COMPOSE_FILE"
    fi

    echo "  端口映射已添加。"
fi

echo ""
echo "[2/2] 重启 Windows 容器以应用新配置..."
cd "$HOME/windows-docker"
docker compose down
docker compose up -d

echo ""
echo "=== 完成 ==="
echo "Windows SSH 端口已映射：Ubuntu:2222 -> Windows:22"
echo ""
echo "等待 Windows 容器完全启动后（通常 10-20 秒），即可通过 SSH 连接："
echo "  ssh -p 2222 windows@localhost"
echo ""
echo "如果是首次安装 OpenSSH，请先通过 noVNC 或 RDP 在 Windows 里运行 setup_windows.ps1"
