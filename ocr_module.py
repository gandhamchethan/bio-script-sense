import json
import re
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Define Tesseract paths for Windows
TESSERACT_PATHS = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'C:\Users\Mahesh\AppData\Local\Tesseract-OCR\tesseract.exe',
]

def setup_tesseract():
    """Setup and verify Tesseract is available"""
    if sys.platform != 'win32':
        return True  # On Linux/Mac, assume it's in PATH
    
    # Try .env first
    tesseract_cmd = os.getenv('TESSERACT_CMD')
    
    if tesseract_cmd and os.path.exists(tesseract_cmd):
        os.environ['TESSERACT_CMD'] = tesseract_cmd
        return tesseract_cmd
    
    # Check standard paths
    for path in TESSERACT_PATHS:
        if os.path.exists(path):
            os.environ['TESSERACT_CMD'] = path
            return path
    
    return None

# Setup before importing pytesseract
tesseract_path = setup_tesseract()

try:
    import pytesseract
    from PIL import Image
    
    # Explicitly set pytesseract path
    if sys.platform == 'win32' and tesseract_path:
        pytesseract.pytesseract.pytesseract_cmd = tesseract_path
        # Just verify the file exists, don't run version check
        if os.path.exists(tesseract_path):
            print(f"[OK] Tesseract configured: {tesseract_path}")
            TESSERACT_AVAILABLE = True
        else:
            print(f"[ERROR] Tesseract file not found: {tesseract_path}")
            TESSERACT_AVAILABLE = False
    else:
        print("[OK] Tesseract OCR ready (using system PATH)")
        TESSERACT_AVAILABLE = True
        
except ImportError as e:
    TESSERACT_AVAILABLE = False
    print(f"[ERROR] Pytesseract import error: {e}")
except Exception as e:
    TESSERACT_AVAILABLE = False
    print(f"[ERROR] Error setting up Tesseract: {e}")

# -------------------------------
# OCR Processing Function - Tesseract (Traditional OCR)
# -------------------------------
def process_answerscript(image_path: str) -> dict:
    """
    Extract answers from student answer sheet using VLM/Tesseract OCR.
    """
    if image_path.lower().endswith('.pdf'):
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), 'files'))
            from files.main import run as run_vlm_main
            temp_out = os.path.join(os.path.dirname(image_path) or ".", "temp_result.json")
            return run_vlm_main(image_path, temp_out)
        except Exception as vlm_err:
            print(f"VLM PDF processing failed ({vlm_err}), falling back to Tesseract...")

    if not TESSERACT_AVAILABLE:
        error_msg = """
[ERROR] TESSERACT OCR NOT FOUND

Pytesseract is installed, but it cannot find the Tesseract executable.

SOLUTIONS:

1. **Install Tesseract Application (REQUIRED)**
   Download: https://github.com/UB-Mannheim/tesseract/wiki
   Windows: Download tesseract-ocr-w64-setup-v5.x.x.exe
   
2. **After installation, set path in your .env file:**
   Add this line: TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
   
3. **Or restart PowerShell** to refresh PATH after installation

4. **Verify installation:**
   - Check: dir "C:\\Program Files\\Tesseract-OCR"
   - Should show tesseract.exe

Tested paths:
  - C:\\Program Files\\Tesseract-OCR\\tesseract.exe
  - C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe
  - C:\\Users\\Mahesh\\AppData\\Local\\Tesseract-OCR\\tesseract.exe
"""
        raise ValueError(error_msg)
    
    try:
        # Verify pytesseract can find tesseract before processing
        if sys.platform == 'win32':
            if not pytesseract.pytesseract.pytesseract_cmd:
                raise RuntimeError("Tesseract path not set. Please check TESSERACT_CMD in .env")
            if not os.path.exists(pytesseract.pytesseract.pytesseract_cmd):
                raise RuntimeError(f"Tesseract not found at: {pytesseract.pytesseract.pytesseract_cmd}")
        
        # Open image
        img = Image.open(image_path)
        
        # Extract text using Tesseract
        print("Extracting text using Tesseract OCR...")
        extracted_text = pytesseract.image_to_string(img)
        
        if not extracted_text.strip():
            raise ValueError("Tesseract extracted empty text. Is the image clear?")
        
        print("Text extracted successfully")
        
        # Parse the extracted text into questions and answers
        # Assuming format like: "Q1: answer" or "1) answer"
        result = parse_extracted_text(extracted_text)
        
        return result

    except Exception as e:
        error_str = str(e)
        
        # Check if it's a Tesseract path issue
        if "not installed" in error_str.lower() or "tesseract" in error_str.lower():
            detailed_error = f"""
[ERROR] TESSERACT EXECUTABLE NOT FOUND

Error: {error_str}

Current configuration:
  pytesseract_cmd: {pytesseract.pytesseract.pytesseract_cmd if sys.platform == 'win32' else 'Not Windows'}
  TESSERACT_CMD env: {os.environ.get('TESSERACT_CMD', 'NOT SET')}

SOLUTIONS:

1. **Verify Tesseract is installed:**
   Check: dir "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

2. **Restart Flask server** after Tesseract installation

3. **Update .env file with correct path:**
   TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe

4. **Restart PowerShell/Terminal** to reload environment

If you just installed Tesseract, restart the Flask server completely.
"""
            raise ValueError(detailed_error)
        
        raise ValueError(f"OCR Processing failed: {e}")

# -------------------------------
# Parse Extracted Text to JSON
# -------------------------------
def parse_extracted_text(text: str) -> dict:
    """
    Parse OCR extracted text into questions and answers.
    Handles formats like:
    - "Q1: answer text"
    - "1) answer text"
    - "Question 1: answer"
    """
    
    lines = text.strip().split('\n')
    result = {}
    current_q = None
    current_answer = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Try to match question markers: "Q1:", "1)", "Question 1:", etc.
        question_match = re.match(r'^(?:Q|Question|q)[\s]*(\d+[a-z]*)[:\)]*', line, re.IGNORECASE)
        
        if question_match:
            # Save previous answer
            if current_q and current_answer:
                result[current_q] = current_answer.strip()
            
            # Start new question
            current_q = question_match.group(1)
            # Get answer part after the question marker
            answer_part = re.sub(r'^(?:Q|Question|q)[\s]*\d+[a-z]*[:\)]*\s*', '', line, flags=re.IGNORECASE)
            current_answer = answer_part
        else:
            # Continuation of previous answer
            if current_q:
                current_answer += " " + line
    
    # Save last answer
    if current_q and current_answer:
        result[current_q] = current_answer.strip()
    
    if not result:
        # If no questions found, return entire text as single entry
        return {"extracted_text": text}
    
    return result

# Test
if __name__ == "__main__":
    path = r"C:\MajorProj\Screenshot 2026-02-14 111537.png"
    result = process_answerscript(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))