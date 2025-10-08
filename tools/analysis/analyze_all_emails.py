"""
Analyze all processed emails to identify matching failures
"""

import json
import os
from pathlib import Path

def analyze_email(email_dir):
    """Analyze a single email"""

    # Read files
    try:
        with open(email_dir / '1_email_parsing.json', 'r', encoding='utf-8') as f:
            parsing = json.load(f)

        with open(email_dir / '2_entity_extraction.json', 'r', encoding='utf-8') as f:
            extraction = json.load(f)

        with open(email_dir / '4_rag_output.json', 'r', encoding='utf-8') as f:
            rag_output = json.load(f)

        with open(email_dir / '5_odoo_matching.json', 'r', encoding='utf-8') as f:
            odoo_match = json.load(f)
    except Exception as e:
        print(f"Error reading {email_dir.name}: {e}")
        return None

    # Extract data
    subject = parsing['email_info']['subject']

    extracted = extraction['extracted_products']
    extracted_names = extracted.get('product_names', [])
    extracted_codes = extracted.get('product_codes', [])

    matched = rag_output['product_matches']
    matched_products = matched.get('products', [])

    odoo_products = odoo_match['product_matches']['products']

    return {
        'subject': subject,
        'email_id': email_dir.name,
        'extracted_names': extracted_names,
        'extracted_codes': extracted_codes,
        'matched_products': matched_products,
        'odoo_products': odoo_products
    }


def main():
    logs_dir = Path('logs/email_steps')

    # Get last 6 emails
    email_dirs = sorted(logs_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:6]

    print("=" * 100)
    print("COMPLETE EMAIL MATCHING ANALYSIS")
    print("=" * 100)
    print()

    all_results = []
    total_extracted = 0
    total_correct = 0
    total_wrong = 0

    for idx, email_dir in enumerate(email_dirs, 1):
        result = analyze_email(email_dir)
        if not result:
            continue

        all_results.append(result)

        print(f"\n{'='*100}")
        print(f"EMAIL {idx}: {result['subject']}")
        print(f"{'='*100}")

        # Compare extracted vs matched
        for i in range(max(len(result['extracted_codes']), len(result['matched_products']))):
            extracted_code = result['extracted_codes'][i] if i < len(result['extracted_codes']) else None
            extracted_name = result['extracted_names'][i] if i < len(result['extracted_names']) else None

            if i < len(result['matched_products']):
                matched = result['matched_products'][i]
                matched_code = matched.get('product_code')
                matched_name = matched.get('product_name', '')[:60]
                match_score = matched.get('match_score', 'N/A')
            else:
                matched_code = None
                matched_name = None
                match_score = None

            # Get Odoo match
            if i < len(result['odoo_products']):
                odoo = result['odoo_products'][i]
                odoo_code = odoo.get('product_code')
            else:
                odoo_code = None

            print(f"\n  Product {i+1}:")
            print(f"    EXTRACTED: {extracted_code}")
            print(f"               {extracted_name[:70] if extracted_name else 'N/A'}")
            print(f"    MATCHED:   {matched_code} (score: {match_score})")
            print(f"               {matched_name if matched_name else 'N/A'}")
            print(f"    ODOO:      {odoo_code}")

            # Check if correct
            total_extracted += 1
            if extracted_code == matched_code:
                print(f"    STATUS:    [OK] CORRECT")
                total_correct += 1
            else:
                print(f"    STATUS:    [FAIL] WRONG (expected {extracted_code}, got {matched_code})")
                total_wrong += 1

    # Summary
    print(f"\n\n{'='*100}")
    print("OVERALL SUMMARY")
    print(f"{'='*100}")
    print(f"Total products extracted: {total_extracted}")
    print(f"Correctly matched:        {total_correct} ({total_correct/total_extracted*100:.1f}%)")
    print(f"Wrongly matched:          {total_wrong} ({total_wrong/total_extracted*100:.1f}%)")
    print(f"\nACCURACY: {total_correct}/{total_extracted} = {total_correct/total_extracted*100:.1f}%")

    if total_wrong > 0:
        print(f"\n{'='*100}")
        print("FAILURES TO FIX:")
        print(f"{'='*100}")

        for idx, result in enumerate(all_results, 1):
            failures = []
            for i in range(len(result['extracted_codes'])):
                extracted_code = result['extracted_codes'][i]
                if i < len(result['matched_products']):
                    matched_code = result['matched_products'][i].get('product_code')
                    if extracted_code != matched_code:
                        failures.append({
                            'extracted': extracted_code,
                            'matched': matched_code,
                            'name': result['extracted_names'][i]
                        })

            if failures:
                print(f"\nEmail {idx}: {result['subject']}")
                for f in failures:
                    print(f"  - {f['extracted']} -> {f['matched']} WRONG")
                    print(f"    Product: {f['name'][:70]}")

    print(f"\n{'='*100}")


if __name__ == "__main__":
    main()
