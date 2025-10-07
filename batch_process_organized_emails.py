"""
Batch process 50 organized emails to test system and identify all issues
"""
import json
import os
from pathlib import Path
from orchestrator.mistral_agent import MistralAgent
from retriever_module.smart_matcher import SmartProductMatcher
from retriever_module.simple_rag import SimpleProductRAG
import pdfplumber

# Initialize components
extractor = MistralAgent()

with open('odoo_database/odoo_products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

rag = SimpleProductRAG()
matcher = SmartProductMatcher(products=products, customer_mapper=None, rag_search=rag, enable_rag=True)

# Get all email directories
emails_dir = Path('organized_emails')
email_folders = sorted([d for d in emails_dir.iterdir() if d.is_dir()])

print("=" * 100)
print(f"BATCH PROCESSING {len(email_folders)} EMAILS FROM organized_emails/")
print("=" * 100)
print()

# Track results
total_emails = 0
order_emails = 0
non_order_emails = 0
total_products = 0
total_matched = 0
total_failed = 0
all_failures = []

for idx, email_folder in enumerate(email_folders, 1):
    print(f"[{idx}/{len(email_folders)}] Processing: {email_folder.name}")

    # Read email.json
    email_json_path = email_folder / 'email.json'
    if not email_json_path.exists():
        print(f"  [SKIP] No email.json found")
        print()
        continue

    with open(email_json_path, 'r', encoding='utf-8') as f:
        email_data = json.load(f)

    # Extract text from email body
    subject = email_data['content']['subject']
    body_text = email_data['content']['body_text']

    # Extract text from PDF attachments
    pdf_text = ""
    attachments_dir = email_folder / 'attachments'
    if attachments_dir.exists():
        for pdf_file in attachments_dir.glob('*.pdf'):
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            pdf_text += text + "\n"
            except Exception as e:
                print(f"  [ERROR] Failed to read PDF {pdf_file.name}: {e}")

    # Combine email text
    full_text = f"{body_text}\n\n{pdf_text}"

    # Classify intent
    intent = extractor.classify_intent(subject, full_text[:5000])  # Limit to first 5000 chars
    is_order = intent.get('type') == 'order_inquiry'

    total_emails += 1

    if not is_order:
        non_order_emails += 1
        print(f"  [NON-ORDER] Intent: {intent.get('type')} (confidence: {intent.get('confidence')})")
        print()
        continue

    order_emails += 1

    # Extract entities
    combined_text = f"{subject}\n\n{full_text}"
    entities = extractor.extract_entities(combined_text[:10000])  # Limit to first 10000 chars

    if not entities or 'extracted_products' not in entities:
        print(f"  [ERROR] Failed to extract entities")
        print()
        continue

    # Get products
    product_codes = entities['extracted_products'].get('product_codes', [])
    product_names = entities['extracted_products'].get('product_names', [])

    if not product_codes:
        print(f"  [NO PRODUCTS] No products extracted")
        print()
        continue

    print(f"  [ORDER] {len(product_codes)} product(s) found")

    # Match products
    for i, (code, name) in enumerate(zip(product_codes, product_names)):
        # Extract attributes
        attrs = extractor.extract_product_attributes(name)

        # Match
        extracted = {
            'product_code': code,
            'product_name': name,
            'attributes': attrs
        }

        result = matcher.find_match(extracted)

        total_products += 1

        if result and result.get('match'):
            matched_code = result['match'].get('default_code', '').strip()
            confidence = result.get('confidence', 0) * 100
            method = result.get('method', 'unknown')

            # Check if correct (allow variants)
            is_correct = (
                code == matched_code or
                code in matched_code or
                matched_code in code or
                code.replace('3M', '').strip() == matched_code.replace('3M', '').strip() or
                code.split('-')[0] == matched_code.split('-')[0]
            )

            if is_correct:
                total_matched += 1
                status = "OK"
            else:
                total_failed += 1
                status = "FAIL"
                all_failures.append({
                    'email': email_folder.name,
                    'subject': subject,
                    'extracted_code': code,
                    'matched_code': matched_code,
                    'product_name': name[:60]
                })

            print(f"    {i+1}. {code} -> {matched_code} [{status}] ({confidence:.0f}%, {method})")
        else:
            total_failed += 1
            print(f"    {i+1}. {code} -> NO_MATCH [FAIL]")
            all_failures.append({
                'email': email_folder.name,
                'subject': subject,
                'extracted_code': code,
                'matched_code': 'NO_MATCH',
                'product_name': name[:60]
            })

    # Reset matcher for next email
    matcher.matched_products = set()

    print()

# Summary
print("=" * 100)
print("BATCH PROCESSING SUMMARY")
print("=" * 100)
print(f"Total emails processed: {total_emails}")
print(f"  Order emails: {order_emails}")
print(f"  Non-order emails: {non_order_emails}")
print()
print(f"Total products extracted: {total_products}")
print(f"  Successfully matched: {total_matched} ({total_matched/total_products*100:.1f}%)" if total_products > 0 else "  Successfully matched: 0")
print(f"  Failed to match: {total_failed} ({total_failed/total_products*100:.1f}%)" if total_products > 0 else "  Failed to match: 0")
print()
print(f"OVERALL ACCURACY: {total_matched}/{total_products} = {total_matched/total_products*100:.1f}%" if total_products > 0 else "OVERALL ACCURACY: N/A")
print()

# Show all failures
if all_failures:
    print("=" * 100)
    print(f"ALL FAILURES ({len(all_failures)} total)")
    print("=" * 100)
    for i, failure in enumerate(all_failures, 1):
        print(f"{i}. Email: {failure['email']}")
        print(f"   Subject: {failure['subject']}")
        print(f"   Extracted: {failure['extracted_code']}")
        print(f"   Matched: {failure['matched_code']}")
        print(f"   Product: {failure['product_name']}")
        print()

print("=" * 100)

# Save results to file
results = {
    'total_emails': total_emails,
    'order_emails': order_emails,
    'non_order_emails': non_order_emails,
    'total_products': total_products,
    'total_matched': total_matched,
    'total_failed': total_failed,
    'accuracy': total_matched/total_products*100 if total_products > 0 else 0,
    'failures': all_failures
}

with open('batch_processing_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("Results saved to: batch_processing_results.json")
