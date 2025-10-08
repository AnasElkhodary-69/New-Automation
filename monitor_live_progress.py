#!/usr/bin/env python3
"""
Live Progress Monitor for 158 Email Test
"""

import re
import time
from collections import Counter

def monitor_progress(log_file='full_system_test.log'):
    """Monitor test progress in real-time"""

    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
        return

    # Extract metrics
    companies = re.findall(r'Company Extracted: (.+)', content)
    processed = re.findall(r'Email (\d+)/158 processed', content)
    odoo_customers = re.findall(r'Customer Found in ODOO: (.+)', content)
    product_matches = re.findall(r'Products Matched in ODOO: (\d+)/(\d+)', content)

    # Calculate statistics
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

    # Progress percentage
    progress_pct = (total_processed / 158) * 100 if total_processed > 0 else 0

    print("\n" + "="*80)
    print("LIVE PROGRESS MONITOR - 158 EMAIL TEST")
    print("="*80)
    print()

    print(f"PROGRESS: {total_processed}/158 emails ({progress_pct:.1f}%)")
    print(f"  [{'=' * int(progress_pct/2)}{'-' * (50 - int(progress_pct/2))}]")
    print()

    print(f"CUSTOMER EXTRACTION:")
    print(f"  [OK] Real Customers: {len(real_companies)}")
    print(f"  {'[FAIL]' if len(sds_companies) > 0 else '[OK]'} SDS Extracted: {len(sds_companies)} (should be 0)")
    if sds_companies:
        print(f"  WARNING - SDS companies found:")
        for sds in sds_companies[:5]:
            print(f"    - {sds}")
    print()

    print(f"ODOO CUSTOMER MATCHING:")
    print(f"  Found: {customers_found}/{len(companies)} ({customers_found/len(companies)*100:.1f}%)" if companies else "  Found: 0/0")
    print(f"  Not Found: {customers_not_found}/{len(companies)}" if companies else "  Not Found: 0/0")
    print()

    print(f"PRODUCT MATCHING:")
    if total_products > 0:
        match_rate = (matched_products/total_products)*100
        print(f"  Total Products: {total_products}")
        print(f"  Matched: {matched_products}/{total_products} ({match_rate:.1f}%)")
        print(f"  Status: {'[OK] EXCELLENT' if match_rate >= 80 else '[WARN] NEEDS REVIEW'}")
    else:
        print(f"  No products extracted yet")
    print()

    print(f"TOP 10 CUSTOMERS (so far):")
    company_counter = Counter(real_companies)
    for company, count in company_counter.most_common(10):
        print(f"  {count:2d}x - {company}")
    print()

    print("="*80)
    print(f"LIVE STATUS: {'[RUNNING] Processing...' if total_processed < 158 else '[DONE] COMPLETE!'}")
    print("="*80)
    print()

if __name__ == "__main__":
    monitor_progress()
