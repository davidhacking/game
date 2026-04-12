Write-Host "=== Final Verification ==="

$Python = "C:\Python310\python.exe"
$env:PATH = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Write-Host ""
Write-Host "--- Python version ---"
& $Python --version

Write-Host ""
Write-Host "--- Testing key imports ---"
$testScript = @"
import sys
print(f"Python: {sys.version}")

packages = ['flask', 'PIL', 'pyperclip', 'requests', 'pandas', 'bs4', 'lxml',
            'pyquery', 'easyutils', 'dill', 'pywinauto', 'pytesseract', 'easytrader']

success = []
failed = []
for pkg in packages:
    try:
        __import__(pkg)
        success.append(pkg)
    except ImportError as e:
        failed.append(f'{pkg}: {e}')

print(f"\nSuccess ({len(success)}): {', '.join(success)}")
if failed:
    print(f"\nFailed ({len(failed)}):")
    for f in failed:
        print(f"  - {f}")
else:
    print("\nAll packages imported successfully!")

# Test tesseract
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
print(f"\nTesseract version: {pytesseract.get_tesseract_version()}")
"@

& $Python -c $testScript

Write-Host ""
Write-Host "--- Tesseract ---"
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version

Write-Host ""
Write-Host "=== All done! ==="
