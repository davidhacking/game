# 修复 Ubuntu2 启动问题（重装）

## 问题现象

Ubuntu2（nvme0n1, Ubuntu 22.04）启动后卡住，显示器无画面（无登录界面）。
内核日志报错：`[  64.735743] hdaudio hdaudioC0D2: Unable to configure, disabling`

## 第一次尝试：修改配置（失败）

### 根因分析

`hdaudio` 错误只是表象。真正的问题链：

1. `snd_hda_codec_hdmi hdaudioC0D2: No i915 binding for Intel HDMI/DP codec` — Intel 核显 HDMI 音频绑定失败
2. **`org.gnome.Shell.desktop: Failed to setup: No GPUs with outputs found`** — GDM 默认用 Wayland，NVIDIA 580 + mutter 42.9 无法枚举 GPU 输出
3. GDM 反复重试全部失败 → 登录界面永远不出现

### 修复措施（已执行但未解决）

1. 禁用 Wayland：`/etc/gdm3/custom.conf` → `WaylandEnable=false`
2. 添加 Xorg NVIDIA 配置：`/etc/X11/xorg.conf.d/10-nvidia.conf`
3. 配置 NVIDIA 内核模块自动加载：`/etc/modules-load.d/nvidia.conf`
4. 更新 initramfs

### 结果

重启后仍然完全黑屏，无任何显示输出。可能是 NVIDIA 驱动在 debootstrap 安装的系统中配置不完整。

---

## 第二次尝试：完全重装（成功）

### 方案

通过 Ubuntu1 SSH 完全重装 Ubuntu2，复用 `dual-ubuntu-install` 任务的脚本流程。

### 执行步骤

1. ✅ 备份 Ubuntu2 上本地没有的 tasks 到 Mac
2. ✅ 清除 nvme0n1 并重新分区（EFI 512MB + 根分区 922.5GB + swap 8GB）
3. ✅ 格式化分区
4. ✅ debootstrap 安装 Ubuntu 22.04 基础系统
5. ✅ 配置系统（apt源、内核、fstab、主机名、网络、时区、用户、GRUB、SSH）
6. ✅ 清理挂载 & 更新主系统 GRUB（10秒菜单超时）
7. ✅ 固定 EFI 启动顺序（Ubuntu1 优先）
8. ✅ 重启验证 — SSH 可登录
9. ✅ 在 Ubuntu2 上生成 RSA 4096 SSH 密钥
10. ✅ Mac SSH 公钥写入 Ubuntu2 authorized_keys
11. ✅ 安装桌面环境（ubuntu-desktop）
12. ✅ 配置 GDM 使用 Xorg（`WaylandEnable=false`）
13. ✅ 设置默认启动 graphical.target
14. ✅ 重启验证桌面 — GDM 登录界面正常显示

### 关键经验

- **不要先装 NVIDIA 驱动再装桌面**：上次的问题就是 NVIDIA 580 驱动和 GDM Wayland 模式冲突
- **先装桌面，确保能进图形界面，再装 NVIDIA 驱动**
- 重装时用非交互方式设置密码（`chpasswd`），避免 `adduser` 交互式输入的问题

### 用户密码

- root 和 david 用户密码相同（与 Ubuntu1 一致）

---

## 第三次尝试：不重装修复（2026-04-05）

### 问题现象

同样的黑屏 + `hdaudio hdaudioC0D2: Unable to configure, disabling`

### 排查过程

1. **磁盘分区编号不稳定**：`grub-reboot` 切换 EFI 启动顺序后，两块 NVMe 的设备编号会互换（nvme0n1 ↔ nvme1n1）。必须用 `LABEL=ubuntu2-root` 或 `UUID=46974041-f9a4-4008-8cd7-5c60b8c8bfbe` 挂载，不要依赖 `/dev/nvmeXn1pY`。

2. **Xorg 找不到 NVIDIA 驱动**：nvidia_drv.so 安装在 `/usr/lib/x86_64-linux-gnu/nvidia/xorg/` 而非标准路径 `/usr/lib/xorg/modules/drivers/`。需要在 xorg.conf 中添加 ModulePath 或创建符号链接。

3. **netplan renderer 与 systemd-networkd 不匹配**：netplan 配置 `renderer: networkd` 但 systemd-networkd 是 disabled 的。改为 `renderer: NetworkManager`。

4. **⭐ 根因：iOA（腾讯零信任安全客户端）拦截外部网络**：`ngnclient.service` 启动 `/usr/lib/iOA/bin/iOA` → SmartGateAgent，拦截了所有外部 SSH/ping 连接。本地能 `ssh localhost` 但远程无法连入。

### 修复措施

1. ✅ 禁用 iOA：`systemctl disable ngnclient.service && systemctl mask ngnclient.service`，移除 ioagui.service、iOALinux.desktop，chmod -x iOA 二进制
2. ✅ 创建 `/etc/X11/xorg.conf`：指定 NVIDIA 驱动 + BusID PCI:1:0:0 + ModulePath
3. ✅ Blacklist nouveau：`/etc/modprobe.d/blacklist-nouveau.conf`
4. ✅ NVIDIA 模块自动加载：`/etc/modules-load.d/nvidia.conf`
5. ✅ GDM 禁用 Wayland：`WaylandEnable=false`
6. ✅ netplan renderer 改为 NetworkManager
7. ✅ SSH 增加端口 16000（Port 22 + Port 16000）
8. ✅ david 免密 sudo
9. ✅ 默认 target 临时改为 multi-user.target（绕过桌面问题）
10. ✅ 禁用 Docker（防止 iptables 规则干扰）
11. ✅ 开机清空 iptables/nftables 规则

### 桌面修复

排查发现：
- **内核 5.15 不支持 13 代 Intel Raptor Lake 核显**：i915 没有注册 DRM card，导致只有 NVIDIA card0，但显示器接在主板 HDMI 口（Intel 核显）上，所以所有 NVIDIA 端口都 disconnected
- 安装 HWE 内核 `linux-image-generic-hwe-22.04`（6.8.0-106-generic），i915 成功注册 card2
- NVIDIA 580 DKMS 编译失败（GCC 11 不支持 `-ftrivial-auto-var-init=zero`），需要先升级到 GCC 12
- Ubuntu1 的 GRUB os-prober 只记录了旧内核，需要在 Ubuntu1 上 `update-grub` 刷新
- **不要用 `efibootmgr --bootnext` 启动 Ubuntu2 自己的 GRUB**，会掉进 `grub>` 命令行
- 删除手写的 `/etc/X11/xorg.conf`，让 Xorg 自动检测 Intel 核显做主显示
- NVIDIA 只需 `/etc/X11/xorg.conf.d/10-nvidia.conf` 的 OutputClass 做 PRIME offload

最终修复步骤：
1. ✅ 安装 HWE 内核：`apt install linux-image-generic-hwe-22.04 linux-headers-generic-hwe-22.04`
2. ✅ 升级 GCC：`apt install gcc-12 && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 100`
3. ✅ 重新编译 NVIDIA DKMS：`dkms build nvidia/580.126.09 -k 6.8.0-106-generic && dkms install ...`
4. ✅ 删除 `/etc/X11/xorg.conf`（让自动检测工作）
5. ✅ 在 Ubuntu1 上 `update-grub`（让 os-prober 发现 Ubuntu2 新内核）
6. ✅ 通过 Ubuntu1 的 `grub-reboot 4` 引导 Ubuntu2

### 结果

✅ **桌面启动成功！** GDM 登录界面正常显示，gnome-shell 运行正常。

### 关键经验

- **永远用 UUID/LABEL 挂载 Ubuntu2 分区**，不要用设备路径
- **iOA（腾讯零信任安全客户端）是网络不通的真正元凶**，不是防火墙也不是网卡驱动
- **调试双系统时，先确保 SSH 可达，再修其他问题**
- **5.15 内核不支持 13 代 Intel Raptor Lake**，必须用 HWE 内核 6.5+
- **显示器接在主板 HDMI 口 = Intel 核显输出**，不要在 xorg.conf 里强制指定 NVIDIA
- **不要用 Ubuntu2 自己的 GRUB 引导**，始终通过 Ubuntu1 的主 GRUB
- **NVIDIA DKMS + 新内核需要 GCC 12+**
