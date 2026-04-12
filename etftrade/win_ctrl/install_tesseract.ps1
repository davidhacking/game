Write-Host "=== Installing Tesseract OCR from shared folder ==="

$tesseractPath = "C:\Program Files\Tesseract-OCR\tesseract.exe"

if (Test-Path $tesseractPath) {
    Write-Host "Tesseract already installed:"
    & $tesseractPath --version
    exit 0
}

# The installer is in the shared folder (\\host.lan\Data maps to Linux /home/david/MF/github/game/)
$sharedInstaller = "C:\Users\windows\Desktop\Shared\tesseract_setup.exe"

Write-Host "Checking shared folder installer: $sharedInstaller"
if (-not (Test-Path $sharedInstaller)) {
    Write-Host "ERROR: Installer not found at $sharedInstaller"
    exit 1
}

Write-Host "Found installer. Copying to local temp..."
Copy-Item $sharedInstaller "C:\tesseract_setup.exe" -Force
Write-Host "Copy done. Size: $((Get-Item 'C:\tesseract_setup.exe').Length) bytes"

Write-Host "Installing Tesseract (silent)..."
$proc = Start-Process -FilePath "C:\tesseract_setup.exe" -ArgumentList "/S" -Wait -PassThru
Write-Host "Installer exit code: $($proc.ExitCode)"

Start-Sleep -Seconds 3

if (Test-Path $tesseractPath) {
    Write-Host "Tesseract installed successfully!"
    & $tesseractPath --version

    # Add to system PATH
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $tesseractDir = "C:\Program Files\Tesseract-OCR"
    if ($currentPath -notlike "*Tesseract*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$tesseractDir", "Machine")
        $env:PATH = "$env:PATH;$tesseractDir"
        Write-Host "Added Tesseract to system PATH"
    }

    # Verify pytesseract can find it
    $Python = "C:\Python310\python.exe"
    Write-Host ""
    Write-Host "Testing pytesseract..."
    & $Python -c "import pytesseract; pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'; print(pytesseract.get_tesseract_version())"
} else {
    Write-Host "Checking alternate locations..."
    Get-ChildItem "C:\Program Files\" -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*Tesseract*" -or $_.Name -like "*tesseract*" } | ForEach-Object { Write-Host $_.FullName }
    Get-ChildItem "C:\" -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*Tesseract*" } | ForEach-Object { Write-Host $_.FullName }
}

Remove-Item "C:\tesseract_setup.exe" -Force -ErrorAction SilentlyContinue
Write-Host "=== Tesseract OCR Installation Done ==="
