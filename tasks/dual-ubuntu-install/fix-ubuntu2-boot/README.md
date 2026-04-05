# 修复 Ubuntu2 启动问题（重装）

## 问题现象

Ubuntu2（nvme0n1, Ubuntu 22.04）启动后卡住，显示器无画面（无登录界面）。
内核日志报错：`hdaudio hdaudioC0D2: Unable to configure, disabling`

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
