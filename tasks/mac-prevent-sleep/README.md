# Mac 防休眠设置

## 背景

运行长时间脚本（如远程安装系统）时，需要防止 Mac 休眠导致 SSH 断连。

## 当前 Mac 电源设置（2026-04-05 记录）

### Battery Power（电池供电）

| 设置项 | 当前值 | 说明 |
|--------|--------|------|
| sleep | 1 | 1 分钟后系统休眠 |
| displaysleep | 15 | 15 分钟后关屏 |
| disksleep | 10 | 10 分钟后硬盘休眠 |
| hibernatemode | 3 | 休眠模式（内存+磁盘） |
| standby | 1 | 启用待机模式 |
| powernap | 1 | 启用 Power Nap |
| lowpowermode | 1 | 启用低电量模式 |
| ttyskeepawake | 1 | tty 活跃时保持唤醒 |
| lessbright | 1 | 电池供电时降低亮度 |
| tcpkeepalive | 1 | 保持 TCP 连接 |
| womp | 0 | 禁用网络唤醒 |
| networkoversleep | 0 | 休眠时不保持网络 |
| Sleep On Power Button | 1 | 电源键可触发休眠 |

### AC Power（接电源）

| 设置项 | 当前值 | 说明 |
|--------|--------|------|
| sleep | 1 | 1 分钟后系统休眠 |
| displaysleep | 10 | 10 分钟后关屏 |
| disksleep | 10 | 10 分钟后硬盘休眠 |
| hibernatemode | 3 | 休眠模式（内存+磁盘） |
| standby | 1 | 启用待机模式 |
| powernap | 1 | 启用 Power Nap |
| lowpowermode | 1 | 启用低电量模式 |
| ttyskeepawake | 1 | tty 活跃时保持唤醒 |
| tcpkeepalive | 1 | 保持 TCP 连接 |
| womp | 1 | 启用网络唤醒 |
| networkoversleep | 0 | 休眠时不保持网络 |
| Sleep On Power Button | 1 | 电源键可触发休眠 |

## 用法

```bash
# 关闭休眠（运行脚本前）
sudo ./disable_sleep.sh

# 恢复原来的设置（脚本跑完后）
sudo ./restore_sleep.sh
```
