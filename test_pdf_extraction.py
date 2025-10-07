"""
Test PDF extraction for the specific alesco order PDF
"""
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import os

pdf_path = r"D:\Downloads\1668_001 (1).pdf"

print("="*80)
print("PDF EXTRACTION TEST")
print("="*80)
print(f"File: {pdf_path}")
print()

# Method 1: Direct text extraction with pdfplumber
print("\n" + "="*80)
print("METHOD 1: pdfplumber text extraction")
print("="*80)
try:
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            print(f"\n--- Page {page_num} ---")
            if text:
                print(text)
                print(f"\nLength: {len(text)} chars")

                # Check for key terms
                if 'SDS 06' in text or 'SDS06' in text:
                    print("✓ SDS 06 found!")
                else:
                    print("✗ SDS 06 NOT found")

                if 'DF-3068' in text:
                    print("✓ DF-3068 found!")
                else:
                    print("✗ DF-3068 NOT found")
            else:
                print("(No text extracted)")
except Exception as e:
    print(f"Error: {e}")

# Method 2: OCR with Tesseract
print("\n" + "="*80)
print("METHOD 2: OCR with Tesseract")
print("="*80)
try:
    # Set poppler path
    poppler_path = r"C:\Anas's PC\Moaz\New Automation\poppler-24.08.0\Library\bin"

    images = convert_from_path(pdf_path, poppler_path=poppler_path)

    for page_num, image in enumerate(images, 1):
        print(f"\n--- Page {page_num} (OCR) ---")
        ocr_text = pytesseract.image_to_string(image, lang='deu+eng')
        print(ocr_text)
        print(f"\nLength: {len(ocr_text)} chars")

        # Check for key terms
        if 'SDS 06' in ocr_text or 'SDS06' in ocr_text or 'SDS 06' in ocr_text:
            print("✓ SDS 06 found!")
        else:
            print("✗ SDS 06 NOT found")

        if 'DF-3068' in ocr_text:
            print("✓ DF-3068 found!")
        else:
            print("✗ DF-3068 NOT found")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
