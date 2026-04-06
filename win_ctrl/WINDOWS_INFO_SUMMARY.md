# Windows 机器信息摘要

## 一、网络信息

### 主机信息
- **SSH 连接地址**: `ssh david@192.168.1.2`
- **主机名**: `david-PC`
- **网卡**: `eno1`
- **IP 地址**: `192.168.1.2/24`
- **DHCP**: 是

## 二、硬件配置

### 磁盘布局
| 硬盘 | 大小 | 当前用途 | 备注 |
|------|------|---------|------|
| **nvme1n1** (Ubuntu1) | 1.9TB | Ubuntu 24.04 LTS 主系统 | UEFI 引导，内核 6.8.0-45-generic |
| **nvme0n1** (Ubuntu2) | 931.5GB | Ubuntu 22.04 LTS 第二系统 | **原来是 Windows 分区**（已被覆盖） |

### nvme0n1 安装 Ubuntu2 后的分区表
| 分区 | 大小 | 类型 | 用途 |
|------|------|------|------|
| nvme0n1p1 | 512MB | vfat (EFI) | Ubuntu2 EFI 分区 |
| nvme0n1p2 | ~922GB | ext4 | Ubuntu2 根分区 |
| nvme0n1p3 | 8GB | swap | Ubuntu2 交换分区 |

### 显卡配置
- **Intel 核显**: 13代 Intel Raptor Lake（i915）
- **NVIDIA 580**: 独立显卡（用于 PRIME offload）
- **显示器连接**: 主板 HDMI 口（通过 Intel 核显输出）

## 三、Docker 中的 Windows 11 配置

### Windows 容器相关信息
**任务位置**: `tasks/dual-ubuntu-install/install-windows-docker/`

#### 系统要求
- Ubuntu 22.04+ (x86_64)
- 至少 4 核 CPU、8GB 内存、64GB 磁盘空间
- 需要 sudo 权限

#### Docker 容器配置
**docker-compose.yml 配置**:
```
服务名: windows
镜像: dockurr/windows
```

#### 资源分配
- **CPU 核数**: 4 核（可配置）
- **内存**: 8GB（可配置，参数名 `RAM_SIZE`）
- **磁盘**: 64GB（可配置，参数名 `DISK_SIZE`）

#### Windows 11 容器的网络/端口信息
| 端口 | 协议 | 用途 | 访问方式 |
|------|------|------|---------|
| **8006** | TCP | noVNC 网页桌面 | `http://localhost:8006` |
| **3389** | TCP | RDP 远程桌面协议 | `localhost:3389` |
| **3389** | UDP | RDP (UDP 加速) | `localhost:3389` |

#### Windows 容器的用户账户
- **用户名**: `windows`
- **密码**: `windows`

#### 启动信息
- **首次启动时间**: 约 10-20 分钟完成 Windows 安装
- **数据目录**: `~/windows-docker/storage/`
- **配置文件**: `~/windows-docker/docker-compose.yml`

#### 访问方式详解
1. **noVNC 网页访问（纯视频流，不支持音频）**
   - 地址: `http://localhost:8006`
   - 无音频支持

2. **RDP 远程连接（支持音频重定向）**
   - 命令示例:
   ```bash
   # 使用 xfreerdp（需要 freerdp2-x11）
   xfreerdp /v:localhost:3389 /u:windows /p:windows /sound:sys:pulse /dynamic-resolution /cert:ignore /scale:140
   ```
   - 或使用 Remmina 创建 RDP 连接 → 音频选项选「在本机播放」
   - 参数说明:
     - `/cert:ignore` — 跳过自签名证书校验
     - `/scale:140` — 放大到140%（支持100/140/180）
     - `/dynamic-resolution` — 动态分辨率跟随窗口大小
     - `/sound:sys:pulse` — 启用音频重定向到 PulseAudio

#### Docker 容器常用命令
```bash
# 查看容器状态
docker compose -f ~/windows-docker/docker-compose.yml ps

# 停止 Windows 容器
docker compose -f ~/windows-docker/docker-compose.yml stop

# 启动 Windows 容器
docker compose -f ~/windows-docker/docker-compose.yml start

# 删除容器（数据保留）
docker compose -f ~/windows-docker/docker-compose.yml down

# 查看日志
docker compose -f ~/windows-docker/docker-compose.yml logs -f

# 重启脚本
~/bin/restart_windows.sh  # 始终执行 down + up
```

#### 虚拟化加速
- **KVM 支持**: 如果 KVM 可用，容器可用 `/dev/kvm` 进行硬件加速
- **无 KVM 模式**: 如果 KVM 不可用，Windows 将以软件模拟模式运行（速度较慢）

## 四、原始 Windows 相关信息

### 原 Windows 分区（已被覆盖）
- **所在硬盘**: `/dev/nvme0n1`（931.5GB）
- **当前状态**: 已被完全清除，安装了 Ubuntu 22.04 LTS
- **覆盖时间**: 已执行
- **备份状态**: 已在 Mac 上备份必要数据

## 五、与 Windows 相关的依赖包

### stock_models 项目中被跳过的 Windows-only 包
在 Linux 系统上安装 stock_models 环境时，以下 Windows-only 包被跳过：
- `pywinauto` — Windows 自动化库
- `comtypes` — COM 对象库
- `easytrader` — 同花顺/华泰等券商交易接口（仅 Windows）
- `atari-py` — Atari 游戏模拟器（仅 Windows）

**已成功安装的核心包**:
- torch 2.11.0+cu130
- stable-baselines3 1.2.0
- gym 0.26.2
- tushare、stockstats、futu-api 等

## 六、其他 Windows 相关配置

### 启动菜单 (GRUB)
**EFI 启动项配置**:
```
Boot0000* Ubuntu      → nvme1n1p2 EFI → Ubuntu1 GRUB（主引导）
Boot0001* ubuntu2     → nvme0n1p1 EFI → Ubuntu2 GRUB（不建议直接使用）
Boot0002* UEFI OS     → nvme0n1p1 EFI → 默认 UEFI 引导

正确启动顺序: 0000, 0001, 0002（Ubuntu1 优先）
```

**系统切换方式**:
- 通过 GRUB 菜单手动选择（10 秒超时）
- 不操作 → 自动进入 Ubuntu1（默认）
- 手动选择 `Ubuntu 22.04 LTS (on /dev/nvme0n1p2)` → 进入 Ubuntu2

### 网络安全相关
**iOA 安全客户端** (腾讯零信任)
- **服务**: `ngnclient.service`
- **执行路径**: `/usr/lib/iOA/bin/iOA` → SmartGateAgent
- **功能**: 拦截所有外部 SSH/ping 连接
- **当前状态**: 在 Ubuntu2 上已禁用
  ```bash
  systemctl disable ngnclient.service
  systemctl mask ngnclient.service
  ```

### SSH 配置
**Ubuntu2 SSH 端口**: 
- 标准端口 22 和备用端口 16000（用于网络问题排查）

## 七、关键经验总结

1. **分区编号不稳定**: 切换 EFI 启动后，nvme 设备编号会互换，必须使用 UUID/LABEL 挂载，不要用设备路径
2. **iOA 是网络问题元凶**: 腾讯零信任安全客户端会拦截外部连接，需要禁用
3. **显卡配置**: 显示器接在主板 HDMI（Intel 核显）上，不要在 xorg.conf 强制指定 NVIDIA
4. **NVIDIA DKMS**: 需要 GCC 12+ 才能编译，5.15 内核不支持 13 代 Intel 核显，需要 HWE 内核 6.5+
5. **音频重定向**: noVNC 不支持音频，必须用 RDP 连接听声音

---

*摘要生成时间: 2026-04-06*
