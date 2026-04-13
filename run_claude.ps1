# 检查是否以管理员权限运行，如果不是则以管理员权限重新启动
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process PowerShell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

# 切换到 game 目录
Set-Location -Path "C:\Users\winnieshi\github\game"

# 执行 claude-internal
claude-internal

# 防止窗口立即关闭
pause
