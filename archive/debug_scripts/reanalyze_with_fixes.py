"""
Re-analyze all emails with fixed SmartMatcher to verify accuracy
"""
import json
from pathlib import Path
from retriever_module.smart_matcher import SmartProductMatcher
from retriever_module.simple_rag import SimpleProductRAG
from orchestrator.mistral_agent import MistralAgent

# Load products
with open('odoo_database/odoo_products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# Initialize
rag = SimpleProductRAG()
matcher = SmartProductMatcher(products=products, customer_mapper=None, rag_search=rag, enable_rag=True)
extractor = MistralAgent()

# Get last 6 emails
logs_dir = Path('logs/email_steps')
email_dirs = sorted(logs_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:6]

print("=" * 80)
print("RE-ANALYSIS WITH FIXES")
print("=" * 80)
print()

total_products = 0
total_correct = 0
total_wrong = 0

for idx, email_dir in enumerate(email_dirs, 1):
    # Read extraction
    try:
        with open(email_dir / '1_email_parsing.json', 'r', encoding='utf-8') as f:
            parsing = json.load(f)
        with open(email_dir / '2_entity_extraction.json', 'r', encoding='utf-8') as f:
            extraction = json.load(f)
    except:
        continue

    subject = parsing['email_info']['subject']
    codes = extraction['extracted_products']['product_codes']
    names = extraction['extracted_products']['product_names']

    print(f"EMAIL {idx}: {subject}")
    print("-" * 80)

    for i, (code, name) in enumerate(zip(codes, names)):
        # Extract attributes
        attrs = extractor.extract_product_attributes(name)

        # Match with fixed SmartMatcher
        extracted = {
            'product_code': code,
            'product_name': name,
            'attributes': attrs
        }

        result = matcher.find_match(extracted)

        # Determine if correct
        if result and result.get('match'):
            matched_code = result['match'].get('default_code', '').strip()
            confidence = result.get('confidence', 0) * 100
            method = result.get('method', 'unknown')

            # Check if correct (exact or variant match)
            is_correct = (
                code == matched_code or
                code in matched_code or
                matched_code in code or
                code.replace('3M', '') == matched_code.replace('3M', '').strip() or
                code.split('-')[0] == matched_code.split('-')[0]
            )

            status = "[OK]" if is_correct else "[FAIL]"

            print(f"  {i+1}. {code} -> {matched_code} {status} ({confidence:.0f}%, {method})")

            total_products += 1
            if is_correct:
                total_correct += 1
            else:
                total_wrong += 1
        else:
            print(f"  {i+1}. {code} -> NO_MATCH [FAIL]")
            total_products += 1
            total_wrong += 1

    print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total products: {total_products}")
print(f"Correct: {total_correct} ({total_correct/total_products*100:.1f}%)")
print(f"Wrong: {total_wrong} ({total_wrong/total_products*100:.1f}%)")
print(f"\nACCURACY: {total_correct}/{total_products} = {total_correct/total_products*100:.1f}%")
print("=" * 80)
