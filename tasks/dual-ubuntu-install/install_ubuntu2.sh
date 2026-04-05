#!/bin/bash
#
# 在 nvme0n1 上安装第二个 Ubuntu 22.04 系统（覆盖 Windows）
# 从 Mac 上执行，通过 SSH 远程操作 david@192.168.1.2
#
# 用法：chmod +x install_ubuntu2.sh && ./install_ubuntu2.sh [起始步骤]
#   ./install_ubuntu2.sh        # 从头开始
#   ./install_ubuntu2.sh 4      # 从步骤 4 开始（断点续跑）
#

set -e

REMOTE="david@192.168.1.2"
NEW_HOSTNAME="ubuntu2"
START_STEP=${1:-0}

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
step()  { echo -e "\n${GREEN}========== 步骤 $1 ==========${NC}"; }

# 远程执行命令的辅助函数
run_remote() {
    ssh -t "$REMOTE" "$1"
}

# ============================================================
if [ "$START_STEP" -le 0 ]; then
step "0/8: 最终确认"
# ============================================================

echo ""
echo "即将执行以下操作："
echo "  目标机器: $REMOTE"
echo "  目标硬盘: /dev/nvme0n1 (931.5GB)"
echo "  操作: 清除所有 Windows 分区，安装 Ubuntu 22.04 LTS"
echo ""
echo "  /dev/nvme1n1 (当前 Ubuntu 系统) 不会被修改"
echo ""
read -p "确认继续？(yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "已取消。"
    exit 0
fi
fi

# ============================================================
if [ "$START_STEP" -le 1 ]; then
step "1/8: 备份当前引导信息"
# ============================================================

run_remote "
sudo cp /boot/grub/grub.cfg ~/grub.cfg.bak && \
sudo cp /etc/fstab ~/fstab.bak && \
sudo sgdisk --backup=\$HOME/nvme1n1_gpt_backup.bin /dev/nvme1n1 && \
echo '备份完成'
"
info "引导信息已备份到远程 ~/ 目录"
fi

# ============================================================
if [ "$START_STEP" -le 2 ]; then
step "2/8: 清除 nvme0n1 并重新分区"
# ============================================================

run_remote "
sudo wipefs -a /dev/nvme0n1 && \
sudo sgdisk --zap-all /dev/nvme0n1 && \
sudo parted /dev/nvme0n1 --script -- \
  mklabel gpt \
  mkpart 'EFI' fat32 1MiB 513MiB \
  set 1 esp on \
  mkpart 'ubuntu2-root' ext4 513MiB 923GiB \
  mkpart 'ubuntu2-swap' linux-swap 923GiB 931GiB && \
echo '分区完成：' && \
lsblk /dev/nvme0n1
"
info "nvme0n1 已重新分区"
fi

# ============================================================
if [ "$START_STEP" -le 3 ]; then
step "3/8: 格式化新分区"
# ============================================================

run_remote "
sudo mkfs.vfat -F32 /dev/nvme0n1p1 && \
sudo mkfs.ext4 -F -L ubuntu2-root /dev/nvme0n1p2 && \
sudo mkswap -L ubuntu2-swap /dev/nvme0n1p3 && \
echo '格式化完成'
"
info "分区已格式化"
fi

# ============================================================
if [ "$START_STEP" -le 4 ]; then
step "4/8: debootstrap 安装基础系统"
# ============================================================

info "这一步需要 5-15 分钟，请耐心等待..."

# 注意：apt update 可能因 Ubuntu1 残留的旧版本源报错，用 || true 防止中断
run_remote "
sudo apt update -qq 2>&1 | grep -v '^E:' || true
sudo apt install -y -qq debootstrap && \
sudo mkdir -p /mnt/ubuntu2 && \
(mountpoint -q /mnt/ubuntu2 || sudo mount /dev/nvme0n1p2 /mnt/ubuntu2) && \
sudo mkdir -p /mnt/ubuntu2/boot/efi && \
(mountpoint -q /mnt/ubuntu2/boot/efi || sudo mount /dev/nvme0n1p1 /mnt/ubuntu2/boot/efi) && \
sudo debootstrap --arch=amd64 jammy /mnt/ubuntu2 http://archive.ubuntu.com/ubuntu && \
echo 'debootstrap 安装完成'
"
info "基础系统安装完成"
fi

# ============================================================
if [ "$START_STEP" -le 5 ]; then
step "5/8: 配置新系统"
# ============================================================

info "5.1 - 挂载分区和虚拟文件系统"

run_remote "
(mountpoint -q /mnt/ubuntu2 || sudo mount /dev/nvme0n1p2 /mnt/ubuntu2) && \
(mountpoint -q /mnt/ubuntu2/boot/efi || sudo mount /dev/nvme0n1p1 /mnt/ubuntu2/boot/efi) && \
(mountpoint -q /mnt/ubuntu2/dev || sudo mount --bind /dev /mnt/ubuntu2/dev) && \
(mountpoint -q /mnt/ubuntu2/dev/pts || sudo mount --bind /dev/pts /mnt/ubuntu2/dev/pts) && \
(mountpoint -q /mnt/ubuntu2/proc || sudo mount --bind /proc /mnt/ubuntu2/proc) && \
(mountpoint -q /mnt/ubuntu2/sys || sudo mount --bind /sys /mnt/ubuntu2/sys) && \
(mountpoint -q /mnt/ubuntu2/sys/firmware/efi/efivars || sudo mount --bind /sys/firmware/efi/efivars /mnt/ubuntu2/sys/firmware/efi/efivars) && \
echo '挂载完成'
"

info "5.2 - 配置 apt 源"

run_remote "
sudo chroot /mnt/ubuntu2 bash -c '
cat > /etc/apt/sources.list << APTEOF
deb http://archive.ubuntu.com/ubuntu jammy main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu jammy-updates main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu jammy-security main restricted universe multiverse
APTEOF
apt update -qq
'
echo 'apt 源配置完成'
"

info "5.3 - 安装内核和基础软件包（需要几分钟）"

run_remote "
sudo chroot /mnt/ubuntu2 bash -c '
export DEBIAN_FRONTEND=noninteractive
apt install -y -qq linux-image-generic linux-headers-generic
apt install -y -qq ubuntu-minimal ubuntu-standard
apt install -y -qq openssh-server vim sudo net-tools curl wget
apt install -y -qq grub-efi-amd64
apt install -y -qq locales
'
echo '软件包安装完成'
"

info "5.4 - 配置 fstab（含 EFI 分区自动挂载）"

run_remote "
ROOT_UUID=\$(sudo blkid -s UUID -o value /dev/nvme0n1p2)
EFI_UUID=\$(sudo blkid -s UUID -o value /dev/nvme0n1p1)
SWAP_UUID=\$(sudo blkid -s UUID -o value /dev/nvme0n1p3)
sudo bash -c \"cat > /mnt/ubuntu2/etc/fstab << FSTABEOF
UUID=\${ROOT_UUID}  /          ext4  errors=remount-ro  0  1
UUID=\${EFI_UUID}   /boot/efi  vfat  umask=0077         0  1
UUID=\${SWAP_UUID}  none       swap  sw                 0  0
FSTABEOF\"
echo 'fstab 内容：'
cat /mnt/ubuntu2/etc/fstab
"

info "5.5 - 设置主机名和 hosts"

run_remote "
echo '${NEW_HOSTNAME}' | sudo tee /mnt/ubuntu2/etc/hostname > /dev/null
sudo bash -c 'cat > /mnt/ubuntu2/etc/hosts << HOSTSEOF
127.0.0.1   localhost
127.0.1.1   ${NEW_HOSTNAME}

::1         localhost ip6-localhost ip6-loopback
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
HOSTSEOF'
echo '主机名设置完成'
"

info "5.6 - 配置网络 (netplan DHCP)"

run_remote "
sudo mkdir -p /mnt/ubuntu2/etc/netplan
sudo bash -c 'cat > /mnt/ubuntu2/etc/netplan/01-netcfg.yaml << NETEOF
network:
  version: 2
  renderer: networkd
  ethernets:
    eno1:
      dhcp4: true
NETEOF'
echo '网络配置完成'
"

info "5.7 - 设置时区和 locale"

run_remote "
sudo chroot /mnt/ubuntu2 bash -c '
ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
echo Asia/Shanghai > /etc/timezone
locale-gen en_US.UTF-8 zh_CN.UTF-8
update-locale LANG=en_US.UTF-8
'
echo '时区和 locale 设置完成'
"

info "5.8 - 设置 root 密码（请输入密码）"
echo ""
warn ">>> 接下来会要求你输入 root 密码（输入两次）<<<"
echo ""

run_remote "sudo chroot /mnt/ubuntu2 passwd root"

info "5.9 - 创建 david 用户（请输入密码和用户信息）"
echo ""
warn ">>> 接下来会要求你输入 david 用户的密码和信息 <<<"
echo ""

run_remote "
sudo chroot /mnt/ubuntu2 bash -c '
adduser david
usermod -aG sudo david
'
"

info "5.10 - 安装 GRUB 到 nvme0n1"

run_remote "
sudo chroot /mnt/ubuntu2 bash -c '
grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=ubuntu2 --recheck /dev/nvme0n1
update-grub
'
echo 'GRUB 安装完成'
"

info "5.11 - 确保 SSH 开机启动"

run_remote "
sudo chroot /mnt/ubuntu2 systemctl enable ssh
echo 'SSH 已启用'
"
fi

# ============================================================
if [ "$START_STEP" -le 6 ]; then
step "6/8: 清理挂载 & 更新主系统 GRUB"
# ============================================================

run_remote "
sudo umount /mnt/ubuntu2/sys/firmware/efi/efivars 2>/dev/null || true
sudo umount /mnt/ubuntu2/dev/pts 2>/dev/null || true
sudo umount /mnt/ubuntu2/dev 2>/dev/null || true
sudo umount /mnt/ubuntu2/proc 2>/dev/null || true
sudo umount /mnt/ubuntu2/sys 2>/dev/null || true
sudo umount /mnt/ubuntu2/boot/efi 2>/dev/null || true
sudo umount /mnt/ubuntu2 2>/dev/null || true
echo '挂载点已清理'

sudo apt install -y -qq os-prober 2>&1 | grep -v '^E:' || true
grep -q 'GRUB_DISABLE_OS_PROBER=false' /etc/default/grub 2>/dev/null || \
  echo 'GRUB_DISABLE_OS_PROBER=false' | sudo tee -a /etc/default/grub > /dev/null
sudo update-grub
echo '主系统 GRUB 已更新'
"
fi

# ============================================================
if [ "$START_STEP" -le 7 ]; then
step "7/8: 配置 GRUB 菜单（显示 10 秒超时 + 固定 EFI 启动顺序）"
# ============================================================

# 【重要】不使用 grub-reboot 切换系统！
# grub-reboot 在 UEFI 双盘环境下会切换 EFI 启动项到 ubuntu2 的 GRUB，
# 但 ubuntu2 的独立 GRUB 配置不完整，会掉进 grub> 命令行。
# 正确做法：固定从 Ubuntu1 的 GRUB 引导，通过菜单手动选择 Ubuntu2。

run_remote "
# 设置 GRUB 菜单显示 10 秒超时
sudo sed -i 's/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=10/' /etc/default/grub
sudo sed -i 's/^GRUB_TIMEOUT_STYLE=.*/GRUB_TIMEOUT_STYLE=menu/' /etc/default/grub
grep -q '^GRUB_TIMEOUT_STYLE' /etc/default/grub || echo 'GRUB_TIMEOUT_STYLE=menu' | sudo tee -a /etc/default/grub > /dev/null
sudo update-grub
echo ''
echo 'GRUB 超时设置：'
grep -E '^GRUB_TIMEOUT|^GRUB_TIMEOUT_STYLE' /etc/default/grub

# 固定 EFI 启动顺序：Ubuntu1 (Boot0000) 永远第一
# 防止任何操作意外改变启动顺序
sudo efibootmgr -o 0000,0001,0002
echo ''
echo 'EFI 启动顺序：'
efibootmgr
"
info "GRUB 菜单和 EFI 启动顺序已配置"
fi

# ============================================================
step "8/8: 安装完成！"
# ============================================================

echo ""
info "Ubuntu2 (22.04 LTS) 已成功安装到 /dev/nvme0n1"
echo ""
echo "切换到 Ubuntu2 的方法："
echo "  1. 重启: ssh -t $REMOTE \"sudo reboot\""
echo "  2. 在 GRUB 菜单中选择 'Ubuntu 22.04 LTS (22.04) (on /dev/nvme0n1p2)'"
echo "  3. 不选则 10 秒后自动进 Ubuntu1"
echo ""
warn "注意：需要连接显示器看 GRUB 菜单！不要使用 grub-reboot 命令！"
echo ""
echo "可选：安装桌面环境（进入 Ubuntu2 后执行）："
echo "  ./install_desktop.sh"
echo ""
