import sys
print("Python:", sys.version)

packages = ['flask', 'PIL', 'pyperclip', 'requests', 'pandas', 'bs4', 'lxml',
            'pyquery', 'easyutils', 'dill', 'pywinauto', 'pytesseract', 'easytrader']

success = []
failed = []
for pkg in packages:
    try:
        __import__(pkg)
        success.append(pkg)
    except ImportError as e:
        failed.append(str(pkg) + ': ' + str(e))

print("Success (" + str(len(success)) + "): " + ", ".join(success))
if failed:
    print("Failed (" + str(len(failed)) + "):")
    for f in failed:
        print("  - " + f)
else:
    print("All packages imported successfully!")

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
print("Tesseract version: " + str(pytesseract.get_tesseract_version()))
