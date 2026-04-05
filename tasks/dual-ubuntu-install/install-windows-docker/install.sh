#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# 通过 Docker 安装 Windows 11 (dockur/windows)
# 用法: bash install.sh
# ============================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

WINDOWS_DIR="$HOME/windows-docker"

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ----------------------------------------------------------
# 1. 安装 Docker（如果未安装）
# ----------------------------------------------------------
install_docker() {
    if command -v docker &>/dev/null; then
        info "Docker 已安装: $(docker --version)"
        return 0
    fi

    info "正在安装 Docker..."

    sudo apt-get update -qq
    sudo apt-get install -y ca-certificates curl gnupg

    sudo install -m 0755 -d /etc/apt/keyrings

    # 带重试的 GPG key 下载（偶发 SSL reset 问题）
    local gpg_downloaded=false
    for attempt in 1 2 3; do
        info "下载 Docker GPG key（第 $attempt 次尝试）..."
        if curl -fsSL --retry 3 --retry-delay 2 https://download.docker.com/linux/ubuntu/gpg \
                -o /tmp/docker.gpg 2>&1 && \
           gpg --dearmor < /tmp/docker.gpg > /tmp/docker.gpg.dearmored 2>&1 && \
           sudo install -m 644 /tmp/docker.gpg.dearmored /etc/apt/keyrings/docker.gpg; then
            rm -f /tmp/docker.gpg /tmp/docker.gpg.dearmored
            gpg_downloaded=true
            break
        fi
        warn "第 $attempt 次失败，等待 3 秒后重试..."
        sleep 3
    done
    if ! $gpg_downloaded; then
        error "下载 Docker GPG key 失败，请检查网络连接"
    fi
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -qq
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin

    # 将当前用户加入 docker 组
    if ! groups "$USER" | grep -q docker; then
        sudo usermod -aG docker "$USER"
        warn "已将 $USER 加入 docker 组，如果后续 docker 命令报权限错误，请重新登录或运行: newgrp docker"
    fi

    info "Docker 安装完成: $(docker --version)"
}

# ----------------------------------------------------------
# 2. 启用 KVM（如果可用）
# ----------------------------------------------------------
setup_kvm() {
    if [ -e /dev/kvm ]; then
        info "KVM 已可用"
    else
        info "正在尝试加载 KVM 模块..."
        sudo modprobe kvm
        sudo modprobe kvm_intel 2>/dev/null || sudo modprobe kvm_amd 2>/dev/null || true

        if [ -e /dev/kvm ]; then
            info "KVM 已启用"
        else
            warn "KVM 不可用，Windows 将以软件模拟模式运行（速度较慢）"
        fi
    fi

    # 确保当前用户有 KVM 访问权限
    if [ -e /dev/kvm ]; then
        sudo chmod 666 /dev/kvm 2>/dev/null || true
    fi
}

# ----------------------------------------------------------
# 3. 创建 docker-compose.yml
# ----------------------------------------------------------
create_compose() {
    mkdir -p "$WINDOWS_DIR/storage"

    if [ -f "$WINDOWS_DIR/docker-compose.yml" ]; then
        warn "docker-compose.yml 已存在，跳过创建"
        return 0
    fi

    info "正在创建 $WINDOWS_DIR/docker-compose.yml ..."

    cat > "$WINDOWS_DIR/docker-compose.yml" << 'EOF'
services:
  windows:
    image: dockurr/windows
    container_name: windows
    environment:
      VERSION: "win11"
      RAM_SIZE: "8G"
      CPU_CORES: "4"
      DISK_SIZE: "64G"
      USERNAME: "windows"
      PASSWORD: "windows"
    devices:
      - /dev/kvm
    cap_add:
      - NET_ADMIN
    ports:
      - "8006:8006"   # noVNC 网页访问
      - "3389:3389/tcp" # RDP 远程桌面
      - "3389:3389/udp"
    volumes:
      - ./storage:/storage
    stop_grace_period: 2m
    restart: on-failure
EOF

    # 如果没有 KVM，移除 devices 配置
    if [ ! -e /dev/kvm ]; then
        sed -i '/devices:/,/\/dev\/kvm/d' "$WINDOWS_DIR/docker-compose.yml"
        warn "已移除 KVM 设备配置（KVM 不可用）"
    fi

    info "配置文件已创建"
}

# ----------------------------------------------------------
# 4. 启动 Windows 容器
# ----------------------------------------------------------
start_windows() {
    info "正在拉取镜像并启动 Windows 11 容器..."
    cd "$WINDOWS_DIR"

    # 用 sudo docker 以防 newgrp 尚未生效
    if docker compose pull 2>/dev/null; then
        docker compose up -d
    else
        sudo docker compose pull
        sudo docker compose up -d
    fi

    echo ""
    info "============================================"
    info "  Windows 11 容器已启动!"
    info "============================================"
    echo ""
    info "  浏览器访问: http://localhost:8006"
    info "  RDP 连接:   localhost:3389"
    echo ""
    info "  首次启动需要 10-20 分钟完成 Windows 安装"
    info "  配置文件: $WINDOWS_DIR/docker-compose.yml"
    info "  数据目录: $WINDOWS_DIR/storage/"
    echo ""
    info "  查看日志: docker compose -f $WINDOWS_DIR/docker-compose.yml logs -f"
    info "============================================"
}

# ----------------------------------------------------------
# 主流程
# ----------------------------------------------------------
main() {
    echo ""
    info "=========================================="
    info "  Docker Windows 11 安装脚本"
    info "=========================================="
    echo ""

    install_docker
    setup_kvm
    create_compose
    start_windows
}

main "$@"
