#!/usr/bin/env python3
"""
Extract Missing Customers from Test Log
"""

import re
from collections import Counter

def extract_missing_customers(log_file='full_system_test.log'):
    """Extract all customers NOT found in Odoo"""

    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Extract all companies and their Odoo match status
    companies = []
    lines = content.split('\n')

    current_company = None
    for i, line in enumerate(lines):
        if 'Company Extracted:' in line:
            current_company = line.split('Company Extracted:')[1].strip()
            # Remove ANSI color codes
            current_company = re.sub(r'\x1b\[[0-9;]*m', '', current_company)

        if 'Customer Found in ODOO: None' in line and current_company:
            companies.append(current_company)
            current_company = None

    # Count frequency
    company_counter = Counter(companies)

    print("="*80)
    print(f"MISSING CUSTOMERS NOT FOUND IN ODOO ({len(companies)} instances, {len(company_counter)} unique)")
    print("="*80)
    print()

    print("Sorted by Frequency:")
    print("-"*80)
    for company, count in company_counter.most_common():
        print(f"{count:3d}x - {company}")
    print()

    print("="*80)
    print("Sorted Alphabetically:")
    print("-"*80)
    for company in sorted(company_counter.keys()):
        print(f"- {company} ({company_counter[company]}x)")
    print()

    # Export to CSV
    with open('missing_customers.csv', 'w', encoding='utf-8') as f:
        f.write("Company Name,Frequency\n")
        for company, count in company_counter.most_common():
            f.write(f'"{company}",{count}\n')

    print("="*80)
    print(f"Exported to: missing_customers.csv")
    print("="*80)

    return company_counter

if __name__ == "__main__":
    extract_missing_customers()
