# win_ctrl — Windows 命令行控制工具

通过 SSH（Windows 内置 OpenSSH Server）对 Windows 进行进程管理、服务管理、日志查看等 CLI 操作。

## 架构

```
Mac/Linux
  └─ SSH ──► Ubuntu 192.168.1.2
                └─ SSH localhost:2222 ──► Windows VM（Docker 容器内端口 22）
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `start.sh` | 一键启动 Windows 容器 + RDP |
| `setup_windows.ps1` | 在 Windows 里以管理员运行，安装 OpenSSH + 配置公钥 |
| `config.json` | SSH 连接配置（已配置好） |
| `win_ctrl.py` | Python CLI 控制工具 |
| `update_docker_compose.sh` | 首次部署时添加 2222:22 端口映射（已执行过） |

## 日常使用

### 启动 Windows + RDP

```bash
bash win_ctrl/start.sh           # 启动容器 + 弹出 RDP 窗口
bash win_ctrl/start.sh --no-rdp  # 只启动容器，不开 RDP
```

### 首次配置（只需做一次）

在 Windows 里以**管理员** PowerShell 运行 `setup_windows.ps1`（公钥已内嵌）：
```powershell
.\setup_windows.ps1
```

### SSH 控制

```bash
cd win_ctrl
uv sync  # 首次安装依赖

uv run python win_ctrl.py ps                        # 列出进程
uv run python win_ctrl.py services                  # 列出服务
uv run python win_ctrl.py service sshd status       # 查看服务状态
uv run python win_ctrl.py run "Get-Date"            # 执行 PowerShell 命令
uv run python win_ctrl.py log "C:\logs\app.log" -f  # 实时看日志
uv run python win_ctrl.py shell                     # 交互式 PowerShell
```

## win_ctrl.py 命令速查

| 命令 | 说明 |
|------|------|
| `ps [name]` | 列出进程（可按名称过滤） |
| `kill <pid\|name>` | 结束进程 |
| `run <cmd>` | 执行 PowerShell 命令 |
| `services [name]` | 列出服务（可按名称过滤） |
| `service <name> <start\|stop\|restart\|status>` | 管理指定服务 |
| `log <path> [-n N] [-f]` | 查看日志（-f 实时追踪） |
| `upload <local> <remote>` | 上传文件 |
| `download <remote> <local>` | 下载文件 |
| `exec <script.ps1>` | 上传并执行 PS1 脚本 |
| `shell` | 交互式 PowerShell |

## 连接配置（config.json）

已配置好，无需修改：
```json
{
  "host": "localhost",
  "port": 2222,
  "user": "windows",
  "key": "~/.ssh/id_rsa",
  "jump": "david@192.168.1.2"
}
```
