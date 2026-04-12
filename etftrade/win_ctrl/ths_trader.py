"""
同花顺交易接口 (trade_a50_v2 版)

通过 paramiko SSH → Windows VM → schtasks → ths_cmds.py → 同花顺 GUI

对外接口:
    get_account_info()  → {"balance": float, "position": {code: {quantity, price, value}}}
    buy_stock(code, price, qty)
    sell_stock(code, price, qty)
    preflight_check()   → 检查前置条件 (SSH/同花顺进程/窗口状态)
"""

import json
import os
import sys
import time
from pathlib import Path

import paramiko

# ── 复用 win_ctrl 的配置加载 ──
import importlib.util
_spec = importlib.util.spec_from_file_location("win_ctrl_mod", str(Path(__file__).parent / "win_ctrl.py"))
_wc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_wc)
load_config = _wc.load_config
connect = _wc.connect

# Windows 端路径
WIN_PYTHON = r"C:\Python310\python.exe"
WIN_SCRIPT = r"C:\Users\windows\Desktop\Shared\stock_models\brokerage\ths_cmds.py"
WIN_OUTPUT = r"C:\Windows\Temp\ths_cmd_output.json"
XIADAN_EXE = r"C:\同花顺软件\同花顺\xiadan.exe"


# ─────────────────────────────────────────────────────────────
# SSH 工具
# ─────────────────────────────────────────────────────────────

def _ssh_run(client, cmd, timeout=15):
    """通过已有 SSH 连接执行命令"""
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read()
        try:
            return out.decode('utf-8').strip()
        except UnicodeDecodeError:
            return out.decode('gbk', errors='replace').strip()
    except Exception as e:
        print('  [SSH] %s' % e)
        return ''


# ─────────────────────────────────────────────────────────────
# 前置检查
# ─────────────────────────────────────────────────────────────

class PreflightError(Exception):
    """前置检查失败"""
    pass


def preflight_check(auto_fix=True):
    """
    检查所有前置条件, 返回 (ok, message)

    检查项:
    1. SSH 连接是否通
    2. Windows 上 Python 是否存在
    3. ths_cmds.py 脚本是否存在
    4. 同花顺 xiadan.exe 进程是否运行
    5. 同花顺窗口是否可见 (非最小化)

    auto_fix=True 时会尝试自动修复:
    - 同花顺未运行 → 启动它
    - 窗口最小化 → 通过 schtasks 恢复窗口
    """
    errors = []
    warnings = []

    # 1. SSH 连接
    cfg = load_config()
    try:
        client = connect(cfg)
    except Exception as e:
        return False, 'SSH 连接失败 (%s:%d): %s' % (cfg['host'], cfg['port'], e)

    try:
        out = _ssh_run(client, 'echo ok', timeout=5)
        if out != 'ok':
            return False, 'SSH 连接异常: echo 返回 %s' % repr(out)

        # 2. Python
        out = _ssh_run(client, 'cmd /c %s --version' % WIN_PYTHON, timeout=10)
        if 'Python' not in out:
            errors.append('Windows Python 未安装: %s 返回 %s' % (WIN_PYTHON, repr(out)))

        # 3. ths_cmds.py
        out = _ssh_run(client, 'cmd /c if exist %s echo FOUND' % WIN_SCRIPT, timeout=5)
        if 'FOUND' not in out:
            errors.append('交易脚本不存在: %s' % WIN_SCRIPT)

        # 4. 同花顺进程
        out = _ssh_run(client, 'tasklist /FI "IMAGENAME eq xiadan.exe" /FO CSV /NH', timeout=10)
        xiadan_running = 'xiadan.exe' in out.lower()

        if not xiadan_running:
            if auto_fix:
                print('  [修复] 同花顺未运行, 尝试启动...')
                # 通过 schtasks 在 GUI session 启动
                start_cmd = 'cmd /c start "" "%s"' % XIADAN_EXE
                _ssh_run(client, 'schtasks /Create /TN "StartTHS" /TR "%s" /SC ONCE /ST 00:00 /F /RL HIGHEST' % start_cmd, timeout=10)
                _ssh_run(client, 'schtasks /Run /TN "StartTHS"', timeout=10)
                time.sleep(5)
                _ssh_run(client, 'schtasks /Delete /TN "StartTHS" /F', timeout=5)
                # 再检查一次
                out = _ssh_run(client, 'tasklist /FI "IMAGENAME eq xiadan.exe" /FO CSV /NH', timeout=10)
                if 'xiadan.exe' not in out.lower():
                    errors.append('同花顺启动失败, 请手动在 Windows 上打开同花顺下单程序')
                else:
                    warnings.append('同花顺已自动启动, 请确认已登录')
            else:
                errors.append('同花顺 (xiadan.exe) 未运行')

        # 5. 窗口状态 — 通过 schtasks 执行一个小 Python 脚本检查窗口
        if not errors:
            check_script = (
                '%s -c "'
                'import ctypes; '
                'from ctypes import wintypes; '
                'import subprocess; '
                'r = subprocess.run([chr(116)+chr(97)+chr(115)+chr(107)+chr(108)+chr(105)+chr(115)+chr(116), '
                '  chr(47)+chr(70)+chr(73), chr(73)+chr(77)+chr(65)+chr(71)+chr(69)+chr(78)+chr(65)+chr(77)+chr(69)+chr(32)+chr(101)+chr(113)+chr(32)+chr(120)+chr(105)+chr(97)+chr(100)+chr(97)+chr(110)+chr(46)+chr(101)+chr(120)+chr(101), '
                '  chr(47)+chr(70)+chr(79), chr(67)+chr(83)+chr(86), chr(47)+chr(78)+chr(72)], '
                '  capture_output=True, text=True); '
                'print(chr(79)+chr(75))"'
            ) % WIN_PYTHON
            # 简化: 直接用 PowerShell 检查窗口是否最小化
            ps_check = (
                'powershell -Command "'
                '$p = Get-Process xiadan -ErrorAction SilentlyContinue; '
                'if ($p) { '
                '  Add-Type -Name WinAPI -Namespace Check -MemberDefinition '
                '    \'[DllImport(\\\"user32.dll\\\")] public static extern bool IsIconic(IntPtr hWnd);\'; '
                '  $iconic = [Check.WinAPI]::IsIconic($p.MainWindowHandle); '
                '  if ($iconic) { Write-Output \\\"MINIMIZED\\\" } '
                '  else { Write-Output \\\"VISIBLE\\\" } '
                '} else { Write-Output \\\"NO_PROCESS\\\" }"'
            )
            out = _ssh_run(client, ps_check, timeout=10)

            if 'MINIMIZED' in out:
                if auto_fix:
                    print('  [修复] 同花顺窗口最小化, 恢复中...')
                    restore_ps = (
                        'powershell -Command "'
                        'Add-Type -Name WinAPI -Namespace Restore -MemberDefinition '
                        '  \'[DllImport(\\\"user32.dll\\\")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow); '
                        '  [DllImport(\\\"user32.dll\\\")] public static extern bool SetForegroundWindow(IntPtr hWnd);\'; '
                        '$p = Get-Process xiadan; '
                        '[Restore.WinAPI]::ShowWindow($p.MainWindowHandle, 9); '
                        'Start-Sleep -Milliseconds 300; '
                        '[Restore.WinAPI]::SetForegroundWindow($p.MainWindowHandle); '
                        'Write-Output \\\"RESTORED\\\""'
                    )
                    # 通过 schtasks 在 GUI session 执行恢复
                    restore_output = r"C:\Windows\Temp\ths_restore.txt"
                    tr_cmd = 'cmd /c %s > %s 2>&1' % (restore_ps, restore_output)
                    _ssh_run(client, 'schtasks /Create /TN "RestoreTHS" /TR "%s" /SC ONCE /ST 00:00 /F /RL HIGHEST' % tr_cmd, timeout=10)
                    _ssh_run(client, 'schtasks /Run /TN "RestoreTHS"', timeout=10)
                    time.sleep(2)
                    out2 = _ssh_run(client, 'cmd /c type %s' % restore_output, timeout=5)
                    _ssh_run(client, 'schtasks /Delete /TN "RestoreTHS" /F', timeout=5)
                    _ssh_run(client, 'cmd /c del /q %s' % restore_output, timeout=5)
                    if 'RESTORED' in (out2 or ''):
                        warnings.append('同花顺窗口已自动恢复')
                    else:
                        warnings.append('窗口恢复可能失败, 如卡住请手动检查 Windows 桌面')
                else:
                    errors.append('同花顺窗口处于最小化状态, 无法操作 GUI')
            elif 'NO_PROCESS' in out:
                if not any('未运行' in e for e in errors):
                    errors.append('同花顺进程不存在')

    finally:
        client.close()

    if errors:
        return False, '; '.join(errors)

    msg = 'OK'
    if warnings:
        msg += ' (' + '; '.join(warnings) + ')'
    return True, msg


# ─────────────────────────────────────────────────────────────
# schtasks 执行核心
# ─────────────────────────────────────────────────────────────

def _run_ths_cmd(cmd_args, timeout=30):
    """
    通过 SSH + schtasks 在 Windows GUI Session 执行 ths_cmds.py
    """
    cfg = load_config()
    client = connect(cfg)
    task_name = 'ThsCmd'

    try:
        tr_cmd = 'cmd /c %s %s %s > %s 2>&1' % (WIN_PYTHON, WIN_SCRIPT, cmd_args, WIN_OUTPUT)

        # 清理旧输出
        _ssh_run(client, 'cmd /c del /q %s' % WIN_OUTPUT, timeout=5)

        # 创建并运行 schtasks
        create_cmd = (
            'schtasks /Create /TN "%s" '
            '/TR "%s" '
            '/SC ONCE /ST 00:00 /F /RL HIGHEST'
        ) % (task_name, tr_cmd)
        _ssh_run(client, create_cmd, timeout=10)
        _ssh_run(client, 'schtasks /Run /TN "%s"' % task_name, timeout=10)

        # 轮询等待输出
        elapsed = 0.0
        raw_output = ''
        while elapsed < timeout:
            time.sleep(1.0)
            elapsed += 1.0
            raw_output = _ssh_run(client, 'cmd /c type %s' % WIN_OUTPUT, timeout=10)
            if raw_output:
                for i, ch in enumerate(raw_output):
                    if ch in ('{', '['):
                        try:
                            json.loads(raw_output[i:])
                            break
                        except json.JSONDecodeError:
                            pass
                else:
                    continue
                break

        # 清理
        _ssh_run(client, 'schtasks /Delete /TN "%s" /F' % task_name, timeout=5)
        _ssh_run(client, 'cmd /c del /q %s' % WIN_OUTPUT, timeout=5)

        if not raw_output:
            raise TimeoutError('ths_cmds.py %s timeout (%ds)' % (cmd_args, timeout))

        # 解析 JSON
        data = None
        for i, ch in enumerate(raw_output):
            if ch in ('{', '['):
                try:
                    data = json.loads(raw_output[i:])
                    break
                except json.JSONDecodeError:
                    continue
        if data is None:
            raise RuntimeError('Invalid JSON: %s' % raw_output[:200])
        if isinstance(data, dict) and 'error' in data:
            raise RuntimeError('ths_cmds error: %s' % data['error'])
        return data
    finally:
        client.close()


# ─────────────────────────────────────────────────────────────
# 对外接口
# ─────────────────────────────────────────────────────────────

def get_account_info():
    """
    获取账户信息, 返回 predict.py 兼容的格式:
    {"balance": float, "position": {"588000": {"quantity": int, "price": float, "value": float}}}

    自动执行前置检查, 确保同花顺可用
    """
    # 前置检查 (自动修复)
    ok, msg = preflight_check(auto_fix=True)
    if not ok:
        raise PreflightError('前置检查失败: %s' % msg)
    if msg != 'OK':
        print('  [preflight] %s' % msg, file=sys.stderr)

    # 获取余额
    balance_data = _run_ths_cmd('balance', timeout=30)
    balance = 0
    if isinstance(balance_data, dict):
        balance = balance_data.get('可用金额', balance_data.get('available', 0))

    # 获取持仓
    position_data = _run_ths_cmd('position', timeout=30)
    position = {}
    if isinstance(position_data, list):
        for item in position_data:
            code = item.get('证券代码', '')
            qty = item.get('实际数量', item.get('可用余额', 0))
            price = item.get('当前价', item.get('最新价', 0))
            value = item.get('市值', qty * price)
            if code and qty > 0:
                position[code] = {
                    'quantity': int(qty),
                    'price': float(price),
                    'value': float(value),
                }

    return {'balance': float(balance), 'position': position}


def buy_stock(code, price, qty):
    """买入股票 (code=纯数字如'588000')"""
    ok, msg = preflight_check(auto_fix=True)
    if not ok:
        raise PreflightError('前置检查失败: %s' % msg)
    print('  buy_stock: %s price=%.3f qty=%d' % (code, price, qty))
    try:
        data = _run_ths_cmd('buy --code %s --price %.3f --qty %d' % (code, price, int(qty)), timeout=30)
        print('  buy result: %s' % data)
        return data
    except Exception as e:
        print('  buy failed: %s' % e)
        return None


def sell_stock(code, price, qty):
    """卖出股票"""
    ok, msg = preflight_check(auto_fix=True)
    if not ok:
        raise PreflightError('前置检查失败: %s' % msg)
    print('  sell_stock: %s price=%.3f qty=%d' % (code, price, qty))
    try:
        data = _run_ths_cmd('sell --code %s --price %.3f --qty %d' % (code, price, int(qty)), timeout=30)
        print('  sell result: %s' % data)
        return data
    except Exception as e:
        print('  sell failed: %s' % e)
        return None


if __name__ == '__main__':
    """直接运行时: 先检查前置条件, 再输出账户信息 JSON"""
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--check', action='store_true', help='只做前置检查, 不查询账户')
    args = p.parse_args()

    if args.check:
        ok, msg = preflight_check(auto_fix=True)
        if ok:
            print('OK: %s' % msg)
        else:
            print('FAIL: %s' % msg, file=sys.stderr)
            sys.exit(1)
    else:
        info = get_account_info()
        print(json.dumps(info, ensure_ascii=False, indent=2))
