"""
Detailed extraction debug - see exactly what Mistral receives and returns
"""
import json
from pathlib import Path
import pdfplumber
from orchestrator.mistral_agent import MistralAgent

# Get email text
email_path = Path('organized_emails/email_001_20250929_Fwd_BK_Bestellung_10891037')
with open(email_path / 'email.json', 'r', encoding='utf-8') as f:
    email_data = json.load(f)

subject = email_data['content']['subject']
body = email_data['content']['body_text']

# Get PDF
pdf_path = email_path / 'attachments'
pdf_file = list(pdf_path.glob('*.pdf'))[0]

pdf_text = ""
with pdfplumber.open(pdf_file) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            pdf_text += text + "\n"

full_text = f"{subject}\n\n{body}\n\n{pdf_text}"

# Save input text
print(f"Full text length: {len(full_text)} chars")
print(f"Saving to debug_input.txt...")
with open('debug_input.txt', 'w', encoding='utf-8') as f:
    f.write(full_text)

# Extract with Mistral Agent
print("Calling Mistral extract_entities...")
extractor = MistralAgent()

# Monkey-patch to save raw response
original_extract = extractor.extract_entities

def debug_extract(text):
    print(f"  Input text length: {len(text)}")
    result = original_extract(text)

    # Save result
    with open('debug_output.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result

extractor.extract_entities = debug_extract

entities = extractor.extract_entities(full_text)

print("\nRESULT:")
print(f"  Intent: {entities.get('intent', {}).get('type', 'N/A')}")
print(f"  Customer: {entities.get('customer_info', {}).get('company', 'N/A')}")

products = entities.get('extracted_products', {})
codes = products.get('product_codes', [])
names = products.get('product_names', [])

print(f"  Products: {len(codes)}")
if codes:
    for i, (code, name) in enumerate(zip(codes, names), 1):
        print(f"    {i}. {code}: {name[:50]}")
else:
    print("    NO PRODUCTS!")

print("\nFiles saved:")
print("  - debug_input.txt (input to Mistral)")
print("  - debug_output.json (Mistral's response)")
print("\nCheck these files to see what went wrong.")
