"""
Quick batch test - Process first 10 emails to identify patterns
"""
import json
from pathlib import Path
from orchestrator.mistral_agent import MistralAgent
from retriever_module.smart_matcher import SmartProductMatcher
from retriever_module.simple_rag import SimpleProductRAG
import pdfplumber
import sys

# Initialize
print("Initializing...", flush=True)
extractor = MistralAgent()

with open('odoo_database/odoo_products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

rag = SimpleProductRAG()
rag.load_or_build_index()  # FIX: Load the RAG index
matcher = SmartProductMatcher(products=products, customer_mapper=None, rag_search=rag, enable_rag=True)

# Get first 10 emails
emails_dir = Path('organized_emails')
email_folders = sorted([d for d in emails_dir.iterdir() if d.is_dir()])[:10]

print(f"\n{'='*80}")
print(f"QUICK BATCH TEST - First 10 Emails")
print(f"{'='*80}\n")

total_products = 0
correct = 0
wrong = 0

for idx, email_folder in enumerate(email_folders, 1):
    print(f"[{idx}/10] {email_folder.name}", flush=True)

    # Read email
    with open(email_folder / 'email.json', 'r', encoding='utf-8') as f:
        email_data = json.load(f)

    subject = email_data['content']['subject']
    body = email_data['content']['body_text']

    # Get PDF text
    pdf_text = ""
    attachments_dir = email_folder / 'attachments'
    if attachments_dir.exists():
        for pdf_file in attachments_dir.glob('*.pdf'):
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages[:3]:  # Only first 3 pages
                        text = page.extract_text()
                        if text:
                            pdf_text += text + "\n"
            except:
                pass

    full_text = f"{subject}\n\n{body}\n\n{pdf_text}"

    # Quick intent check
    is_order = any(word in subject.lower() for word in ['order', 'bestellung', 'commande', 'po'])

    if not is_order:
        print(f"  [NON-ORDER]\n")
        continue

    # Extract (with shorter text to speed up)
    try:
        entities = extractor.extract_entities(full_text[:8000])
        # FIX: extract_entities() returns flat structure, not nested
        codes = entities.get('product_codes', [])
        names = entities.get('product_names', [])

        if not codes:
            print(f"  [NO PRODUCTS]\n")
            continue

        print(f"  [ORDER] {len(codes)} products")

        # Match
        for code, name in zip(codes, names):
            attrs = extractor.extract_product_attributes(name)
            result = matcher.find_match({
                'product_code': code,
                'product_name': name,
                'attributes': attrs
            })

            total_products += 1

            if result and result.get('match'):
                matched = result['match'].get('default_code', '').strip()
                is_correct = (code == matched or code in matched or matched in code or
                             code.split('-')[0] == matched.split('-')[0])

                status = "OK" if is_correct else "FAIL"
                if is_correct:
                    correct += 1
                else:
                    wrong += 1

                print(f"    {code} -> {matched} [{status}]")
            else:
                wrong += 1
                print(f"    {code} -> NO_MATCH [FAIL]")

        matcher.reset_matched_products()  # FIX: Use the proper method instead of set()
        print()

    except Exception as e:
        print(f"  [ERROR] {str(e)}\n")

print(f"{'='*80}")
print(f"RESULTS: {correct}/{total_products} correct = {correct/total_products*100:.1f}%" if total_products > 0 else "No products found")
print(f"{'='*80}")
