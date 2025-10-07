"""
Debug entity extraction on email_001 to understand why products aren't being extracted
"""
import json
import pdfplumber
from pathlib import Path
from orchestrator.mistral_agent import MistralAgent

print("=" * 80)
print("EXTRACTION DEBUG - Email 001")
print("=" * 80)
print()

# Read email
email_path = Path('organized_emails/email_001_20250929_Fwd_BK_Bestellung_10891037')
with open(email_path / 'email.json', 'r', encoding='utf-8') as f:
    email_data = json.load(f)

subject = email_data['content']['subject']
body = email_data['content']['body_text']

print(f"Subject: {subject}")
print(f"Body length: {len(body)} chars")
print()

# Extract PDF text
pdf_path = email_path / 'attachments'
pdf_file = list(pdf_path.glob('*.pdf'))[0]
print(f"PDF: {pdf_file.name}")
print()

pdf_text = ""
with pdfplumber.open(pdf_file) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if text:
            pdf_text += text + "\n"
            print(f"Page {i+1}: {len(text)} chars")

print(f"\nTotal PDF text: {len(pdf_text)} chars")
print()

# Show relevant parts
print("=" * 80)
print("PDF TEXT SAMPLE (first 2000 chars)")
print("=" * 80)
print(pdf_text[:2000])
print()

# Look for product indicators
print("=" * 80)
print("PRODUCT INDICATORS IN TEXT")
print("=" * 80)
indicators = ['SDS', 'Artikel', 'Material', 'Pos', 'Menge', 'Preis', 'Einheit']
for indicator in indicators:
    count = pdf_text.upper().count(indicator.upper())
    if count > 0:
        print(f"  '{indicator}': {count} occurrences")

print()

# Try extraction
print("=" * 80)
print("ATTEMPTING EXTRACTION")
print("=" * 80)

extractor = MistralAgent()
full_text = f"{subject}\n\n{body}\n\n{pdf_text}"

print(f"Full text length: {len(full_text)} chars")
print(f"Sending to Mistral: {min(len(full_text), 10000)} chars (limit)")
print()

try:
    entities = extractor.extract_entities(full_text[:10000])

    print("EXTRACTION RESULT:")
    print(f"  Intent: {entities.get('intent', {}).get('type', 'unknown')}")
    print(f"  Customer: {entities.get('customer_info', {}).get('company', 'N/A')}")

    products = entities.get('extracted_products', {})
    product_codes = products.get('product_codes', [])
    product_names = products.get('product_names', [])
    quantities = products.get('quantities', [])

    print(f"  Products found: {len(product_codes)}")

    if product_codes:
        for i, (code, name, qty) in enumerate(zip(product_codes, product_names, quantities), 1):
            print(f"    {i}. {code}")
            print(f"       Name: {name[:60]}")
            print(f"       Qty: {qty}")
    else:
        print("    [NO PRODUCTS EXTRACTED]")

    # Show raw extraction for debugging
    print()
    print("  Raw extracted_products:")
    print(f"    {json.dumps(products, indent=4)}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
