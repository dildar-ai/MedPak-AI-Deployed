"""
MedPak AI — OCR Scanner Module
Uses OCR.space free API to extract text from images to drastically reduce RAM usage.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from config import settings


async def scan_medicine_image(image_bytes: bytes) -> str:
    """
    Takes an uploaded image (bytes) of a medicine box/blister pack.
    Sends it to OCR.space API and returns the extracted text.
    """
    api_key = settings.OCR_SPACE_API_KEY
    url = "https://api.ocr.space/parse/image"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
            data = {
                "apikey": api_key,
                "language": "eng",
                "scale": "true",
                "OCREngine": "2",
            }
            
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("IsErroredOnProcessing"):
                print(f"[OCR] API Error: {result.get('ErrorMessage')}")
                return ""
                
            parsed_results = result.get("ParsedResults", [])
            if not parsed_results:
                return ""
                
            text = parsed_results[0].get("ParsedText", "")
            return text.strip()
            
    except Exception as e:
        print(f"[OCR] HTTP Request Error: {e}")
        return ""


if __name__ == "__main__":
    # Test script if run directly
    print("Run OCR from main application.")
