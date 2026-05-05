"""
MedPak AI — OCR Scanner Module
Uses EasyOCR to extract text from images, specifically looking for medicine names.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import easyocr
import io
from PIL import Image
import numpy as np
from config import settings


# Initialize reader once (downloads weights on first run)
# We only need English for reading medicine names on boxes
_reader: easyocr.Reader | None = None

def _get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        print("[OCR] Initializing EasyOCR (English)...")
        # Reconfigure stdout to avoid UnicodeEncodeError in Windows terminals
        import sys
        enc = sys.stdout.encoding or ""
        if enc.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")

        use_gpu = getattr(settings, "OCR_USE_GPU", False)
        try:
            _reader = easyocr.Reader(["en"], gpu=use_gpu, verbose=False)
        except Exception:
            if use_gpu:
                print("[OCR] GPU init failed; retrying on CPU.")
                _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            else:
                raise
    return _reader


def scan_medicine_image(image_bytes: bytes) -> str:
    """
    Takes an uploaded image (bytes) of a medicine box/blister pack.
    Returns the most prominent extracted text (likely the brand name).
    """
    # Open image using Pillow to normalize format
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        print(f"[OCR] Error loading image: {e}")
        return ""
        
    # Convert to numpy array for EasyOCR
    img_np = np.array(img)
    
    reader = _get_reader()
    
    # Read text. detail=1 returns (bbox, text, confidence)
    results = reader.readtext(img_np, detail=1)
    
    if not results:
        return ""
        
    # Heuristic: the medicine name is usually the largest/most prominent text
    # We can sort by bounding box size to guess the main text.
    # bbox format: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
    
    def bbox_area(bbox):
        width = abs(bbox[1][0] - bbox[0][0])
        height = abs(bbox[2][1] - bbox[1][1])
        return width * height
        
    # Sort results by area (largest first)
    results.sort(key=lambda x: bbox_area(x[0]), reverse=True)
    
    # Return the largest text block found
    # Usually this will be the brand name like "PANADOL"
    largest_text = results[0][1]
    
    # Optionally, we can return top 2-3 words joined if they are close
    # For now, just return the biggest text string
    return largest_text.strip()


if __name__ == "__main__":
    # Test script if run directly
    print("Run OCR from main application.")
