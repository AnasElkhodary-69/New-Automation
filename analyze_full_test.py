#!/usr/bin/env python3
"""
Analyze Full System Test Results (158 Emails)
"""

import re
from collections import Counter

def analyze_results(log_file='full_system_test.log'):
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Extract all companies
    companies = re.findall(r'Company Extracted: (.+)', content)

    # Extract processing results
    processed = re.findall(r'Email (\d+)/158 processed', content)

    # Extract customer matches
    odoo_customers = re.findall(r'Customer Found in ODOO: (.+)', content)

    # Extract product matches
    product_matches = re.findall(r'Products Matched in ODOO: (\d+)/(\d+)', content)

    # Calculate statistics
    total_emails = len(companies)
    total_processed = max([int(p) for p in processed]) if processed else 0

    # Check for SDS (should be 0)
    sds_companies = [c for c in companies if any(x in c.upper() for x in ['SDS GMBH', 'SDS-PRINT', 'SDS PRINT'])]
    real_companies = [c for c in companies if not any(x in c.upper() for x in ['SDS GMBH', 'SDS-PRINT', 'SDS PRINT'])]

    # Odoo customer matches
    customers_found = sum([1 for c in odoo_customers if c != 'None'])
    customers_not_found = sum([1 for c in odoo_customers if c == 'None'])

    # Product matching
    total_products = sum([int(m[1]) for m in product_matches])
    matched_products = sum([int(m[0]) for m in product_matches])

    # Company frequency
    company_counter = Counter(real_companies)

    print("=" * 80)
    print("FULL SYSTEM TEST RESULTS - 158 EMAILS")
    print("=" * 80)
    print()

    print(f"PROCESSING STATUS:")
    print(f"  Emails Processed: {total_processed}/158")
    print(f"  Companies Extracted: {total_emails}")
    print()

    print(f"CUSTOMER EXTRACTION:")
    print(f"  SDS Extracted (should be 0): {len(sds_companies)}")
    print(f"  Real Customers: {len(real_companies)}")
    if sds_companies:
        print(f"  WARNING - SDS companies found:")
        for sds in sds_companies:
            print(f"    - {sds}")
    print()

    print(f"ODOO CUSTOMER MATCHING:")
    print(f"  Found in Odoo: {customers_found}/{total_emails} ({customers_found/total_emails*100:.1f}%)")
    print(f"  Not Found: {customers_not_found}/{total_emails} ({customers_not_found/total_emails*100:.1f}%)")
    print()

    print(f"PRODUCT MATCHING:")
    print(f"  Total Products Extracted: {total_products}")
    print(f"  Products Matched: {matched_products}/{total_products} ({matched_products/total_products*100:.1f}%)")
    print()

    print("TOP 20 CUSTOMERS (by frequency):")
    for company, count in company_counter.most_common(20):
        print(f"  {count:2d}x - {company}")
    print()

    print("=" * 80)
    print("SUCCESS CRITERIA:")
    print(f"  [{'OK' if len(sds_companies) == 0 else 'FAIL'}] SDS not extracted as customer: {len(sds_companies) == 0}")
    print(f"  [{'OK' if matched_products/total_products >= 0.80 else 'WARN'}] Product matching >= 80%: {matched_products/total_products*100:.1f}%")
    print(f"  [{'OK' if total_processed >= 150 else 'WARN'}] Processed >= 150 emails: {total_processed}")
    print("=" * 80)

if __name__ == "__main__":
    analyze_results()
