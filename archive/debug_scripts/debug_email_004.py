"""
Debug email_004 extraction issue
"""
import pdfplumber
from orchestrator.mistral_agent import MistralAgent

# Extract PDF
pdf_path = "organized_emails/email_004_20250929_WG_PO3227/attachments/Purchase Order - PO03227 (1).pdf"
with pdfplumber.open(pdf_path) as pdf:
    text = ""
    for page in pdf.pages[:3]:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

print("=" * 80)
print("PDF TEXT (first 2000 chars)")
print("=" * 80)
print(text[:2000])
print()

# Test extraction
print("=" * 80)
print("EXTRACTION TEST")
print("=" * 80)

extractor = MistralAgent()
entities = extractor.extract_entities(text[:8000])

print(f"Product codes: {entities.get('product_codes', [])}")
print(f"Product names: {entities.get('product_names', [])}")
print(f"Product quantities: {entities.get('product_quantities', [])}")
