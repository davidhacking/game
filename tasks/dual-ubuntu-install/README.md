# 覆盖 Windows 分区，在 nvme0n1 上安装第二个 Ubuntu

## 机器实际情况（已确认）

- **机器**：`ssh david@192.168.1.2`，主机名 `david-PC`
- **Ubuntu1**：Ubuntu 24.04 LTS (Noble)，UEFI 引导，内核 6.8.0-45-generic
- **Ubuntu2**：Ubuntu 22.04 LTS (Jammy)，安装在 nvme0n1
- **网卡**：`eno1`，IP `192.168.1.2/24`，DHCP

### 磁盘布局

| 硬盘 | 大小 | 用途 |
|------|------|------|
| **nvme1n1**（Ubuntu1） | 1.9TB | 主系统，GRUB 主引导 |
| **nvme0n1**（Ubuntu2） | 931.5GB | 第二系统（原 Windows） |

**nvme0n1 安装后的分区：**

| 分区 | 大小 | 类型 | 用途 |
|------|------|------|------|
| nvme0n1p1 | 512MB | vfat (EFI) | Ubuntu2 EFI |
| nvme0n1p2 | ~922GB | ext4 | Ubuntu2 根分区 |
| nvme0n1p3 | 8GB | swap | Ubuntu2 交换分区 |

---

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `install_ubuntu2.sh` | 一键安装脚本，支持 `./install_ubuntu2.sh [起始步骤]` 断点续跑 |
| `install_desktop.sh` | 为 Ubuntu2 安装桌面环境 |

---

## 切换系统的方式

**必须通过 GRUB 菜单手动选择**，需要连接显示器。

重启后会看到 GRUB 菜单（10 秒超时）：
- 不操作 → 10 秒后自动进入 **Ubuntu1**（默认）
- 选择 `Ubuntu 22.04 LTS (22.04) (on /dev/nvme0n1p2)` → 进入 **Ubuntu2**

> **⚠️ 不要使用 `grub-reboot` 命令切换系统！** 见下方「踩坑记录」。

---

## 踩坑记录

### 问题 1：`apt update` 报错导致脚本中断

**现象**：步骤 4 执行 `apt update` 时，Ubuntu1 的源里有过期的 mantic (23.10 EOL) 配置，报 `E: The repository ... no longer has a Release file`，`set -e` 导致脚本退出。

**原因**：Ubuntu1 有残留的旧版本源配置，`apt update` 非零退出。

**修复**：`apt update` 的错误输出过滤掉，加 `|| true` 防止中断：
```bash
sudo apt update -qq 2>&1 | grep -v '^E:' || true
```

### 问题 2：`grub-reboot` 导致进入 `grub>` 命令行

**现象**：执行 `grub-reboot 4` 切换到 Ubuntu2 后，重启直接掉进 `grub>` 命令行，而不是进入 Ubuntu2 系统。

**原因**：在 UEFI 双盘环境下，`grub-reboot` 不仅设置 GRUB 菜单默认项，还会通过 `efibootmgr` 将 EFI 启动顺序切换到 Ubuntu2 自己的 GRUB（`Boot0001: ubuntu2`）。但 Ubuntu2 的独立 GRUB（安装在 nvme0n1p1 EFI 分区上）配置不完整，无法找到正确的 grub.cfg，于是掉进 `grub>` 交互界面。

**根本原因**：两块 NVMe 盘各有独立的 EFI 分区，Ubuntu2 的 GRUB 是在 chroot 环境下安装的，它的 grub.cfg 路径和 EFI 分区的挂载关系在独立启动时可能不正确。

**修复方案**：
1. 放弃使用 `grub-reboot`，改为通过 GRUB 菜单手动选择
2. 固定 EFI 启动顺序，Ubuntu1 永远第一：`sudo efibootmgr -o 0000,0001,0002`
3. 设置 GRUB 菜单超时 10 秒，让用户有时间选择：
   ```bash
   GRUB_TIMEOUT=10
   GRUB_TIMEOUT_STYLE=menu
   ```

**手动恢复方法**：如果已经掉进 `grub>` 了，手动引导回 Ubuntu1：
```
# 先 ls 确认 Ubuntu1 的分区号
ls
ls (hd0,gpt3)/    # 看有没有 /boot 目录

# 手动引导 Ubuntu1
set root=(hd0,gpt3)
linux /boot/vmlinuz-6.8.0-45-generic root=UUID=348e110a-00d9-485f-ac75-cc66615ba7dc ro
initrd /boot/initrd.img-6.8.0-45-generic
boot
```

### 问题 3：脚本中 `ls` 命令缺少 `sudo` 导致中断

**现象**：fix_ubuntu2_grub.sh 执行 `ls /boot/efi/` 报 `Permission denied`，`set -e` 导致脚本退出。

**原因**：EFI 分区目录需要 root 权限访问，`ls` 没加 `sudo`。

**教训**：涉及 `/boot/efi` 的所有操作都要加 `sudo`。

---

## EFI 启动项参考

```
Boot0000* Ubuntu      → nvme1n1p2 EFI → Ubuntu1 的 GRUB（主引导）
Boot0001* ubuntu2     → nvme0n1p1 EFI → Ubuntu2 的 GRUB（不要直接用！）
Boot0002* UEFI OS     → nvme0n1p1 EFI → 默认 UEFI 引导

正确的启动顺序：0000, 0001, 0002（Ubuntu1 优先）
```

---

## 总结

| 步骤 | 耗时预估 | 是否需要重启 |
|------|----------|-------------|
| 1. 备份 | 1 分钟 | 否 |
| 2. 分区 | 1 分钟 | 否 |
| 3. 格式化 | 1 分钟 | 否 |
| 4. debootstrap | 5-15 分钟 | 否 |
| 5. 配置系统 | 10-15 分钟 | 否 |
| 6. GRUB + EFI | 2 分钟 | 否 |
| 7. 安装桌面（可选） | 15-30 分钟 | 否 |
| 8. 重启验证 | 需重启 | **是（需显示器选 GRUB 菜单）** |

全程通过 SSH 在 Mac 上执行，只有最后验证时需要重启并通过显示器选择 GRUB 菜单。
