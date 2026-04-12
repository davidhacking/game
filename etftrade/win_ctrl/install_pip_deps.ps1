Write-Host "=== Start Installing Python Dependencies ==="

$Python = "C:\Python310\python.exe"
$PyAlt = "C:\Program Files\Python310\python.exe"

$found = $false
if (Test-Path $Python) {
    $found = $true
} elseif (Test-Path $PyAlt) {
    $Python = $PyAlt
    $found = $true
}

if (-not $found) {
    Write-Host "ERROR: Python 3.10 not found!"
    exit 1
}

Write-Host "Using Python: $Python"
& $Python --version
& $Python -m pip --version

$mirror = "https://pypi.tuna.tsinghua.edu.cn/simple/"
$trusted = "pypi.tuna.tsinghua.edu.cn"

Write-Host ""
Write-Host "=== Upgrading pip ==="
& $Python -m pip install --upgrade pip -i $mirror --trusted-host $trusted

$packages = @(
    "flask",
    "pillow",
    "pyperclip",
    "requests",
    "pandas",
    "beautifulsoup4",
    "lxml",
    "pyquery",
    "easyutils",
    "pytz",
    "dill",
    "pywinauto",
    "pytesseract",
    "easytrader"
)

Write-Host ""
Write-Host "=== Installing packages ==="
foreach ($pkg in $packages) {
    Write-Host ">>> Installing $pkg ..."
    & $Python -m pip install $pkg -i $mirror --trusted-host $trusted
    if ($LASTEXITCODE -eq 0) {
        Write-Host "<<< $pkg installed OK"
    } else {
        Write-Host "<<< WARNING: $pkg install failed (exit $LASTEXITCODE)"
    }
    Write-Host ""
}

Write-Host "=== Installed packages ==="
& $Python -m pip list

Write-Host ""
Write-Host "=== Done ==="
