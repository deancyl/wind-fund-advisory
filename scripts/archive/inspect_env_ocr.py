import sys
import importlib
from PIL import Image

print(f"Python version: {sys.version}")

# Check image
img_path = r"C:\Users\deanc\.gemini\antigravity\brain\1395b6f9-733c-4446-9cdb-f33a19e5f711\.user_uploaded\media_1794236135877_65af68f3.jpg"
try:
    with Image.open(img_path) as img:
        print(f"Image path: {img_path}")
        print(f"Format: {img.format}, Size: {img.size} (Width={img.width}, Height={img.height}), Mode: {img.mode}")
except Exception as e:
    print(f"Error opening image: {e}")

# Check OCR libraries
ocr_libs = [
    "rapidocr_onnxruntime",
    "rapidocr",
    "paddleocr",
    "easyocr",
    "pytesseract",
    "winocr",
    "windows.media.ocr",
    "winrt.windows.media.ocr",
    "cv2",
    "PIL"
]

print("\nChecking OCR and Vision packages:")
for lib in ocr_libs:
    try:
        mod = importlib.import_module(lib)
        ver = getattr(mod, "__version__", "unknown")
        print(f"  [AVAILABLE] {lib}: {ver}")
    except ImportError as e:
        print(f"  [MISSING]   {lib}: {e}")
    except Exception as e:
        print(f"  [ERROR]     {lib}: {e}")
