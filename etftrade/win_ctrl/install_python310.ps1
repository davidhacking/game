# 安装 Python 3.10
Write-Host "=== 开始安装 Python 3.10 ==="

$pythonInstaller = "C:\python310.exe"
$pythonUrl = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe"

# 先检查是否已安装
if (Test-Path "C:\Python310\python.exe") {
    Write-Host "Python 3.10 已安装在 C:\Python310"
    C:\Python310\python.exe --version
    exit 0
}

if (Test-Path "C:\Program Files\Python310\python.exe") {
    Write-Host "Python 3.10 已安装在 C:\Program Files\Python310"
    & "C:\Program Files\Python310\python.exe" --version
    exit 0
}

Write-Host "正在下载 Python 3.10.11..."
$start = Get-Date
try {
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller -UseBasicParsing
    $elapsed = (Get-Date) - $start
    Write-Host "下载完成，耗时 $($elapsed.TotalSeconds) 秒"
} catch {
    Write-Host "下载失败: $_"
    exit 1
}

Write-Host "正在安装 Python 3.10.11（静默安装）..."
$proc = Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 DefaultAllUsersTargetDir=C:\Python310" -Wait -PassThru
Write-Host "安装程序退出码: $($proc.ExitCode)"

if ($proc.ExitCode -eq 0) {
    Write-Host "Python 安装成功！"
    # 刷新 PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    # 验证
    if (Test-Path "C:\Python310\python.exe") {
        C:\Python310\python.exe --version
        C:\Python310\python.exe -m pip --version
    } else {
        # 搜索安装目录
        $pyPath = (Get-ChildItem "C:\Program Files\Python310\python.exe" -ErrorAction SilentlyContinue).FullName
        if ($pyPath) {
            Write-Host "找到 Python: $pyPath"
            & $pyPath --version
        }
    }
} else {
    Write-Host "Python 安装失败，退出码: $($proc.ExitCode)"
    exit 1
}

# 清理安装包
Remove-Item $pythonInstaller -Force -ErrorAction SilentlyContinue
Write-Host "=== Python 3.10 安装完成 ==="
