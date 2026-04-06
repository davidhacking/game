#!/usr/bin/env bash
# 一键启动 Windows 容器 + RDP
# 用法：bash start.sh [--no-rdp]

set -e

COMPOSE_FILE="$HOME/windows-docker/docker-compose.yml"
RDP_HOST="localhost"
RDP_PORT="3389"
RDP_USER="windows"
RDP_PASS="windows"
NO_RDP=false

for arg in "$@"; do
    case $arg in
        --no-rdp) NO_RDP=true ;;
    esac
done

echo "=== 启动 Windows 容器 ==="

# 检查 docker-compose.yml 是否存在
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "错误：找不到 $COMPOSE_FILE"
    exit 1
fi

# 启动容器（已运行则跳过）
STATUS=$(docker compose -f "$COMPOSE_FILE" ps --status running --quiet 2>/dev/null | wc -l)
if [ "$STATUS" -gt 0 ]; then
    echo "容器已在运行，跳过启动。"
else
    echo "启动容器..."
    docker compose -f "$COMPOSE_FILE" up -d
    echo "等待 Windows 启动（通常需要 15-30 秒）..."
    sleep 20
fi

echo "容器状态："
docker compose -f "$COMPOSE_FILE" ps

if [ "$NO_RDP" = true ]; then
    echo ""
    echo "已跳过 RDP（--no-rdp）"
    echo "  noVNC   : http://localhost:8006"
    echo "  共享目录 : Windows 里打开 \\\\host.lan\\Data"
    exit 0
fi

# 检查 xfreerdp
if ! command -v xfreerdp &>/dev/null; then
    echo ""
    echo "未找到 xfreerdp，跳过 RDP 连接。"
    echo "安装命令：sudo apt install freerdp2-x11"
    echo "noVNC: http://localhost:8006"
    exit 0
fi

echo ""
echo "=== 启动 RDP ==="
echo "连接到 $RDP_HOST:$RDP_PORT，用户：$RDP_USER"
xfreerdp \
    /v:${RDP_HOST}:${RDP_PORT} \
    /u:${RDP_USER} \
    /p:${RDP_PASS} \
    /sound:sys:pulse \
    /dynamic-resolution \
    /cert:ignore \
    /scale:140 &

echo "RDP 已启动（PID=$!）"
echo ""
echo "快捷入口："
echo "  noVNC      : http://localhost:8006"
echo "  RDP        : ${RDP_HOST}:${RDP_PORT}"
echo "  SSH        : ssh -p 2222 ${RDP_USER}@localhost"
echo "  共享目录    : Windows 里打开 \\\\host.lan\\Data（即宿主 ~/MF/github/game）"
