#!/usr/bin/env python3
"""
win_ctrl.py — Windows 命令行控制工具

通过 SSH 连接到 Windows（内置 OpenSSH Server）实现：
  - 进程查看与管理
  - 服务查看与管理
  - 日志查看（支持 tail -f 模式）
  - 文件上传/下载
  - 交互式 PowerShell
  - 执行 PS1 脚本

连接配置（优先级：环境变量 > ~/.win_ctrl.json > 默认值）：
  WIN_HOST   目标主机（默认 localhost）
  WIN_PORT   SSH 端口（默认 2222）
  WIN_USER   用户名（默认 windows）
  WIN_KEY    私钥路径（默认 ~/.ssh/id_rsa）
  WIN_JUMP   跳板机（格式 user@host，如 david@192.168.1.2）
"""

import argparse
import json
import os
import select
import shlex
import sys
import tempfile
import time
from pathlib import Path

import paramiko


# ─────────────────────────────────────────────────────────────
# 配置加载
# ─────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "host": "localhost",
    "port": 2222,
    "user": "windows",
    "password": "",
    "key": "~/.ssh/id_rsa",
    "jump": "",
}


def load_config() -> dict:
    """加载连接配置（环境变量 > 脚本同目录 config.json > 默认值）"""
    cfg = dict(DEFAULT_CONFIG)

    # 优先读脚本同目录下的 config.json
    script_dir = Path(__file__).parent
    config_file = script_dir / "config.json"
    if config_file.exists():
        try:
            with open(config_file) as f:
                file_cfg = json.load(f)
            cfg.update(file_cfg)
        except Exception as e:
            print(f"[警告] 读取 {config_file} 失败：{e}", file=sys.stderr)

    env_map = {
        "WIN_HOST": "host",
        "WIN_PORT": "port",
        "WIN_USER": "user",
        "WIN_PASSWORD": "password",
        "WIN_KEY": "key",
        "WIN_JUMP": "jump",
    }
    for env_key, cfg_key in env_map.items():
        val = os.environ.get(env_key)
        if val:
            cfg[cfg_key] = int(val) if cfg_key == "port" else val

    cfg["port"] = int(cfg["port"])
    if cfg.get("key"):
        cfg["key"] = str(Path(cfg["key"]).expanduser())
    return cfg


# ─────────────────────────────────────────────────────────────
# SSH 连接
# ─────────────────────────────────────────────────────────────

def connect(cfg: dict) -> paramiko.SSHClient:
    """建立 SSH 连接（支持跳板机）"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    pkey = None
    key_path = cfg.get("key", "")
    if key_path:
        key_path = str(Path(key_path).expanduser())
    if key_path and os.path.exists(key_path):
        try:
            pkey = paramiko.RSAKey.from_private_key_file(key_path)
        except Exception:
            try:
                pkey = paramiko.Ed25519Key.from_private_key_file(key_path)
            except Exception:
                pass

    password = cfg.get("password") or None

    connect_kwargs = {
        "hostname": cfg["host"],
        "port": cfg["port"],
        "username": cfg["user"],
        "pkey": pkey,
        "password": password,
        "look_for_keys": bool(pkey),
        "allow_agent": bool(pkey),
        "timeout": 10,
    }

    if cfg.get("jump"):
        # 通过跳板机建立 SSH 隧道
        jump_user, jump_host = _parse_jump(cfg["jump"])
        jump_client = paramiko.SSHClient()
        jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        jump_client.connect(
            hostname=jump_host,
            username=jump_user,
            pkey=pkey,
            look_for_keys=True,
            allow_agent=True,
            timeout=10,
        )
        jump_transport = jump_client.get_transport()
        dest_addr = (cfg["host"], cfg["port"])
        local_addr = ("127.0.0.1", 0)
        channel = jump_transport.open_channel("direct-tcpip", dest_addr, local_addr)
        connect_kwargs["sock"] = channel

    client.connect(**connect_kwargs)
    return client


def _parse_jump(jump: str):
    """解析跳板机字符串 user@host"""
    if "@" in jump:
        user, host = jump.split("@", 1)
    else:
        user = os.environ.get("USER", "root")
        host = jump
    return user, host


def run_cmd(client: paramiko.SSHClient, cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    """执行命令，返回 (exit_code, stdout, stderr)"""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    return exit_code, stdout.read().decode("utf-8", errors="replace"), stderr.read().decode("utf-8", errors="replace")


def run_ps(client: paramiko.SSHClient, ps_cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    """执行 PowerShell 命令"""
    # -NonInteractive -NoProfile 加速启动，-OutputFormat Text 避免 XML 编码问题
    cmd = f'powershell -NonInteractive -NoProfile -Command "{ps_cmd}"'
    return run_cmd(client, cmd, timeout=timeout)


# ─────────────────────────────────────────────────────────────
# 子命令实现
# ─────────────────────────────────────────────────────────────

def cmd_ps(client: paramiko.SSHClient, name_filter: str = ""):
    """列出进程"""
    if name_filter:
        ps_cmd = f"Get-Process -Name '*{name_filter}*' -ErrorAction SilentlyContinue | Select-Object Id, CPU, WorkingSet, Name, MainWindowTitle | Format-Table -AutoSize"
    else:
        ps_cmd = "Get-Process | Sort-Object CPU -Descending | Select-Object -First 50 Id, CPU, WorkingSet, Name | Format-Table -AutoSize"
    code, out, err = run_ps(client, ps_cmd)
    if out.strip():
        print(out)
    if err.strip():
        print(f"[stderr] {err}", file=sys.stderr)


def cmd_kill(client: paramiko.SSHClient, target: str):
    """结束进程（PID 或进程名）"""
    if target.isdigit():
        ps_cmd = f"Stop-Process -Id {target} -Force"
        desc = f"PID {target}"
    else:
        ps_cmd = f"Stop-Process -Name '{target}' -Force -ErrorAction SilentlyContinue"
        desc = f"名称 '{target}'"
    code, out, err = run_ps(client, ps_cmd)
    if code == 0:
        print(f"已结束进程 {desc}")
    else:
        print(f"结束进程失败：{err.strip() or '进程不存在或权限不足'}", file=sys.stderr)


def cmd_run(client: paramiko.SSHClient, command: str):
    """执行 PowerShell 命令并输出结果"""
    code, out, err = run_ps(client, command, timeout=60)
    if out.strip():
        print(out)
    if err.strip():
        print(f"[stderr] {err}", file=sys.stderr)
    if code != 0:
        sys.exit(code)


def cmd_services(client: paramiko.SSHClient, name_filter: str = ""):
    """列出服务"""
    if name_filter:
        ps_cmd = f"Get-Service -Name '*{name_filter}*' -ErrorAction SilentlyContinue | Select-Object Status, StartType, Name, DisplayName | Format-Table -AutoSize"
    else:
        ps_cmd = "Get-Service | Sort-Object Status, Name | Select-Object Status, StartType, Name, DisplayName | Format-Table -AutoSize"
    code, out, err = run_ps(client, ps_cmd)
    if out.strip():
        print(out)
    if err.strip():
        print(f"[stderr] {err}", file=sys.stderr)


def cmd_service(client: paramiko.SSHClient, name: str, action: str):
    """管理指定服务：start / stop / restart / status"""
    action = action.lower()
    if action == "status":
        ps_cmd = f"Get-Service -Name '{name}' | Select-Object Status, StartType, Name, DisplayName | Format-List"
    elif action == "start":
        ps_cmd = f"Start-Service -Name '{name}'"
    elif action == "stop":
        ps_cmd = f"Stop-Service -Name '{name}' -Force"
    elif action == "restart":
        ps_cmd = f"Restart-Service -Name '{name}' -Force"
    else:
        print(f"未知操作：{action}（支持 start / stop / restart / status）", file=sys.stderr)
        sys.exit(1)

    code, out, err = run_ps(client, ps_cmd)
    if out.strip():
        print(out)
    if err.strip():
        print(f"[stderr] {err}", file=sys.stderr)
    if code == 0 and action != "status":
        print(f"服务 '{name}' {action} 成功")
    elif code != 0:
        sys.exit(code)


def cmd_log(client: paramiko.SSHClient, filepath: str, lines: int = 50, follow: bool = False):
    """查看日志文件（支持 -f 实时追踪）"""
    filepath_escaped = filepath.replace("'", "''")
    if follow:
        # Get-Content -Wait 类似 tail -f
        ps_cmd = f"Get-Content -Path '{filepath_escaped}' -Tail {lines} -Wait"
        print(f"[实时追踪 {filepath}，Ctrl+C 退出]")
        _stream_command(client, f'powershell -NonInteractive -NoProfile -Command "{ps_cmd}"')
    else:
        ps_cmd = f"Get-Content -Path '{filepath_escaped}' -Tail {lines}"
        code, out, err = run_ps(client, ps_cmd)
        if out.strip():
            print(out)
        if err.strip():
            print(f"[stderr] {err}", file=sys.stderr)


def cmd_upload(client: paramiko.SSHClient, local: str, remote: str):
    """上传文件到 Windows"""
    sftp = client.open_sftp()
    try:
        sftp.put(local, remote)
        print(f"已上传：{local} -> {remote}")
    finally:
        sftp.close()


def cmd_download(client: paramiko.SSHClient, remote: str, local: str):
    """从 Windows 下载文件"""
    sftp = client.open_sftp()
    try:
        sftp.get(remote, local)
        print(f"已下载：{remote} -> {local}")
    finally:
        sftp.close()


def cmd_exec(client: paramiko.SSHClient, script_path: str):
    """上传并执行 PS1 脚本"""
    local_path = Path(script_path)
    if not local_path.exists():
        print(f"脚本文件不存在：{script_path}", file=sys.stderr)
        sys.exit(1)

    remote_path = f"C:\\Windows\\Temp\\win_ctrl_{local_path.name}"

    # 读取脚本内容，加上 UTF-8 BOM 后再上传，防止 PowerShell 解析中文出错
    content = local_path.read_bytes()
    bom = b'\xef\xbb\xbf'
    if not content.startswith(bom):
        content = bom + content
    # 写入临时文件再上传
    with tempfile.NamedTemporaryFile(suffix='.ps1', delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        cmd_upload(client, tmp_path, remote_path)
    finally:
        os.unlink(tmp_path)

    # 使用 Bypass 执行策略以避免 Windows 脚本执行限制
    # 用 -Command 而非 -File，避免 UNC/编码问题
    cmd = f'powershell -ExecutionPolicy Bypass -NonInteractive -NoProfile -Command "& \'{remote_path}\'"'
    code, out, err = run_cmd(client, cmd, timeout=600)
    if out.strip():
        print(out)
    if err.strip():
        print(f"[stderr] {err}", file=sys.stderr)
    if code != 0:
        sys.exit(code)


def cmd_shell(client: paramiko.SSHClient):
    """启动交互式 PowerShell session"""
    channel = client.invoke_shell()
    channel.settimeout(0.0)

    # 启动 PowerShell
    channel.send("powershell\r\n")

    print("[交互式 PowerShell，输入 exit 退出]")
    import termios
    import tty

    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        while True:
            r, _, _ = select.select([channel, sys.stdin], [], [], 0.1)
            if channel in r:
                data = channel.recv(4096)
                if not data:
                    break
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            if sys.stdin in r:
                data = os.read(sys.stdin.fileno(), 1024)
                if not data:
                    break
                channel.send(data)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    print("\n[session 已结束]")


def _stream_command(client: paramiko.SSHClient, cmd: str):
    """流式输出长时间运行的命令（Ctrl+C 中断）"""
    transport = client.get_transport()
    channel = transport.open_session()
    channel.exec_command(cmd)

    try:
        while True:
            if channel.recv_ready():
                data = channel.recv(4096).decode("utf-8", errors="replace")
                print(data, end="", flush=True)
            if channel.recv_stderr_ready():
                data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                print(data, end="", flush=True)
            if channel.exit_status_ready():
                break
            time.sleep(0.05)
    except KeyboardInterrupt:
        channel.close()
        print("\n[中断]")


# ─────────────────────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="win_ctrl",
        description="Windows 命令行控制工具（通过 SSH）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python win_ctrl.py ps
  python win_ctrl.py ps chrome
  python win_ctrl.py kill 1234
  python win_ctrl.py kill notepad
  python win_ctrl.py run "Get-Date"
  python win_ctrl.py services
  python win_ctrl.py services ssh
  python win_ctrl.py service sshd status
  python win_ctrl.py service sshd restart
  python win_ctrl.py log "C:\\logs\\app.log"
  python win_ctrl.py log "C:\\logs\\app.log" -n 100 -f
  python win_ctrl.py upload ./file.txt "C:\\Users\\windows\\file.txt"
  python win_ctrl.py download "C:\\logs\\app.log" ./app.log
  python win_ctrl.py exec ./my_script.ps1
  python win_ctrl.py shell
""",
    )

    # 全局连接参数
    parser.add_argument("--host", help="目标主机（默认 localhost）")
    parser.add_argument("--port", type=int, help="SSH 端口（默认 2222）")
    parser.add_argument("--user", help="用户名（默认 windows）")
    parser.add_argument("--key", help="私钥路径（默认 ~/.ssh/id_rsa）")
    parser.add_argument("--jump", help="跳板机（格式 user@host）")

    sub = parser.add_subparsers(dest="command", required=True)

    # ps
    p_ps = sub.add_parser("ps", help="列出进程")
    p_ps.add_argument("name", nargs="?", default="", help="进程名过滤（模糊匹配）")

    # kill
    p_kill = sub.add_parser("kill", help="结束进程")
    p_kill.add_argument("target", help="PID 或进程名")

    # run
    p_run = sub.add_parser("run", help="执行 PowerShell 命令")
    p_run.add_argument("cmd", help="PowerShell 命令")

    # services
    p_svc = sub.add_parser("services", help="列出服务")
    p_svc.add_argument("name", nargs="?", default="", help="服务名过滤（模糊匹配）")

    # service
    p_svcm = sub.add_parser("service", help="管理指定服务")
    p_svcm.add_argument("name", help="服务名")
    p_svcm.add_argument("action", choices=["start", "stop", "restart", "status"], help="操作")

    # log
    p_log = sub.add_parser("log", help="查看日志文件")
    p_log.add_argument("path", help="Windows 文件路径")
    p_log.add_argument("-n", "--lines", type=int, default=50, help="显示行数（默认 50）")
    p_log.add_argument("-f", "--follow", action="store_true", help="实时追踪（类似 tail -f）")

    # upload
    p_up = sub.add_parser("upload", help="上传文件到 Windows")
    p_up.add_argument("local", help="本地文件路径")
    p_up.add_argument("remote", help="Windows 目标路径")

    # download
    p_dl = sub.add_parser("download", help="从 Windows 下载文件")
    p_dl.add_argument("remote", help="Windows 文件路径")
    p_dl.add_argument("local", help="本地目标路径")

    # exec
    p_exec = sub.add_parser("exec", help="上传并执行 PS1 脚本")
    p_exec.add_argument("script", help="本地 PS1 脚本路径")

    # shell
    sub.add_parser("shell", help="交互式 PowerShell session")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # 合并配置
    cfg = load_config()
    if args.host:
        cfg["host"] = args.host
    if args.port:
        cfg["port"] = args.port
    if args.user:
        cfg["user"] = args.user
    if args.key:
        cfg["key"] = str(Path(args.key).expanduser())
    if args.jump:
        cfg["jump"] = args.jump

    # 连接
    try:
        client = connect(cfg)
    except Exception as e:
        print(f"SSH 连接失败：{e}", file=sys.stderr)
        print(f"  主机：{cfg['host']}:{cfg['port']}  用户：{cfg['user']}  密钥：{cfg['key']}", file=sys.stderr)
        if cfg.get("jump"):
            print(f"  跳板机：{cfg['jump']}", file=sys.stderr)
        sys.exit(1)

    try:
        cmd = args.command
        if cmd == "ps":
            cmd_ps(client, args.name)
        elif cmd == "kill":
            cmd_kill(client, args.target)
        elif cmd == "run":
            cmd_run(client, args.cmd)
        elif cmd == "services":
            cmd_services(client, args.name)
        elif cmd == "service":
            cmd_service(client, args.name, args.action)
        elif cmd == "log":
            cmd_log(client, args.path, args.lines, args.follow)
        elif cmd == "upload":
            cmd_upload(client, args.local, args.remote)
        elif cmd == "download":
            cmd_download(client, args.remote, args.local)
        elif cmd == "exec":
            cmd_exec(client, args.script)
        elif cmd == "shell":
            cmd_shell(client)
    finally:
        client.close()


if __name__ == "__main__":
    main()
