"""
Analyze email processing results: Company, Products Parsed vs Matched
"""
import json
import glob
import os
import sys
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def analyze_all_emails():
    """Analyze all processed emails and create a summary report"""

    email_dirs = sorted(glob.glob('logs/email_steps/*/'))

    results = []

    for email_dir in email_dirs:
        email_id = os.path.basename(email_dir.rstrip('/'))

        # Read extraction results
        extraction_file = os.path.join(email_dir, '2_entity_extraction.json')
        rag_output_file = os.path.join(email_dir, '4_rag_output.json')

        if not os.path.exists(extraction_file):
            continue

        try:
            # Load extraction data
            with open(extraction_file, encoding='utf-8', errors='ignore') as f:
                extraction = json.load(f)

            # Load RAG matching results
            matched_products = []
            if os.path.exists(rag_output_file):
                with open(rag_output_file, encoding='utf-8', errors='ignore') as f:
                    rag_output = json.load(f)
                    product_matches = rag_output.get('product_matches', {})
                    matched_products = product_matches.get('products', [])

            # Extract info
            customer_info = extraction.get('customer_info', {})
            company = customer_info.get('company', 'N/A')

            extracted = extraction.get('extracted_products', {})
            parsed_products = extracted.get('product_names', [])
            parsed_codes = extracted.get('product_codes', [])

            # Count matched products
            matched_count = len(matched_products)
            parsed_count = len(parsed_products)

            # Calculate match percentage
            match_percentage = (matched_count / parsed_count * 100) if parsed_count > 0 else 0

            results.append({
                'email_id': email_id,
                'company': company,
                'parsed_count': parsed_count,
                'matched_count': matched_count,
                'match_percentage': match_percentage,
                'parsed_products': list(zip(parsed_codes, parsed_products)),
                'matched_products': matched_products
            })

        except Exception as e:
            print(f"Error processing {email_id}: {e}")
            continue

    return results

def print_summary_report(results):
    """Print a summary report of all emails"""

    print("=" * 120)
    print("EMAIL PROCESSING RESULTS SUMMARY")
    print("=" * 120)
    print(f"\nTotal emails analyzed: {len(results)}")
    print()

    # Overall statistics
    total_parsed = sum(r['parsed_count'] for r in results)
    total_matched = sum(r['matched_count'] for r in results)
    avg_match_rate = (total_matched / total_parsed * 100) if total_parsed > 0 else 0

    print(f"Overall Statistics:")
    print(f"  Total Products Parsed:  {total_parsed}")
    print(f"  Total Products Matched: {total_matched}")
    print(f"  Overall Match Rate:     {avg_match_rate:.1f}%")
    print()

    print("=" * 120)
    print(f"{'EMAIL ID':<50} {'COMPANY':<30} {'PARSED':<8} {'MATCHED':<8} {'RATE':<8}")
    print("=" * 120)

    for result in results:
        email_short = result['email_id'][:48]
        company_short = result['company'][:28]

        print(f"{email_short:<50} {company_short:<30} {result['parsed_count']:<8} {result['matched_count']:<8} {result['match_percentage']:>6.1f}%")

    print("=" * 120)

def print_detailed_report(results):
    """Print detailed report with product-level information"""

    print("\n\n")
    print("=" * 120)
    print("DETAILED PRODUCT ANALYSIS")
    print("=" * 120)

    for i, result in enumerate(results, 1):
        print(f"\n{'='*120}")
        print(f"EMAIL {i}/{len(results)}: {result['email_id']}")
        print(f"{'='*120}")
        print(f"Company: {result['company']}")
        print(f"Parsed: {result['parsed_count']} products | Matched: {result['matched_count']} products | Rate: {result['match_percentage']:.1f}%")
        print()

        # Show parsed products
        print("PARSED PRODUCTS:")
        for j, (code, name) in enumerate(result['parsed_products'], 1):
            print(f"  {j}. [{code}] {name[:90]}")

        print()

        # Show matched products
        if result['matched_products']:
            print("MATCHED PRODUCTS:")
            for j, match in enumerate(result['matched_products'], 1):
                matched_name = match.get('product_name', 'N/A')[:90]
                matched_code = match.get('product_code', 'N/A')
                extracted_as = match.get('extracted_as', 'N/A')[:90] if match.get('extracted_as') else 'N/A'
                score = match.get('match_score', '0%')

                print(f"  {j}. Extracted: {extracted_as}")
                print(f"     Matched:   [{matched_code}] {matched_name} (Score: {score})")
        else:
            print("MATCHED PRODUCTS: None")

        print()

if __name__ == "__main__":
    print("Analyzing all processed emails...")
    print()

    results = analyze_all_emails()

    # Print summary report
    print_summary_report(results)

    # Ask if user wants detailed report
    print("\n")
    response = input("Show detailed product-level report? (y/n): ").strip().lower()
    if response == 'y':
        print_detailed_report(results)

    print("\n" + "="*120)
    print("ANALYSIS COMPLETE")
    print("="*120)
