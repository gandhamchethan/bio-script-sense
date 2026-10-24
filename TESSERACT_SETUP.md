# Tesseract OCR Setup Guide

## Why Tesseract?
Tesseract is a free, open-source OCR engine that:
- ✅ Uses **zero additional memory** (unlike LM Studio vision)
- ✅ Works on **CPU only** (no GPU needed)
- ✅ Extracts text reliably from documents
- ✅ No token limit issues
- ✅ Much faster than vision models

---

## Installation Steps for Windows

### Step 1: Install Python Package
```powershell
pip install pytesseract
```

### Step 2: Install Tesseract Application
Download and run the installer:
**https://github.com/UB-Mannheim/tesseract/wiki**

1. Go to the link above
2. Download: `tesseract-ocr-w64-setup-v5.x.x.exe` (latest version)
3. Run the installer
4. **Important:** Note the installation path (usually `C:\Program Files\Tesseract-OCR`)

### Step 3: Configure Pytesseract (Windows)
Add this to the top of ocr_module.py after imports:

```python
import pytesseract

# Windows: Point to Tesseract installation
pytesseract.pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

**Or set as environment variable (recommended):**
```powershell
# In PowerShell (run as Administrator):
[Environment]::SetEnvironmentVariable('TESSERACT_CMD', 'C:\Program Files\Tesseract-OCR\tesseract.exe', 'User')
```

Then restart your terminal and the code will find it automatically.

---

## Test Installation

```powershell
# Navigate to your project
cd c:\Users\Mahesh\OneDrive\Desktop\MajorProject\Scriptsense

# Test if Tesseract works
python -c "import pytesseract; print('✓ Tesseract installed')"
```

---

## Supported Languages

Tesseract supports 100+ languages. For English (default), no extra setup needed.

For other languages, download language files from:
https://github.com/UB-Mannheim/tesseract/wiki

---

## System Requirements
- **Disk Space:** ~200MB
- **Memory:** Minimal (< 100MB)
- **CPU:** Any modern processor
- **Supported Formats:** PNG, JPG, TIFF, BMP, GIF

---

## After Installation

Once Tesseract is installed:
1. Restart PowerShell/Terminal
2. Run Flask server again
3. Upload image for evaluation
4. OCR will work without LM Studio memory issues!

---

## Troubleshooting

If you get "Tesseract not found" error:
1. Verify installation: `dir "C:\Program Files\Tesseract-OCR"`
2. Check environment variable: `echo %TESSERACT_CMD%`
3. If still not found, manually set path in ocr_module.py (see Step 3 above)
