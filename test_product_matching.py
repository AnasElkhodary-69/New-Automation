"""
Quick test to verify improved product matching
"""

import logging
import sys
from retriever_module.odoo_connector import OdooConnector

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)

# Initialize Odoo connector
odoo = OdooConnector()

print("="*80)
print("TESTING IMPROVED PRODUCT MATCHING")
print("="*80)

# Test product codes from the last email
test_cases = [
    ("G-25-20-125-17", "Doctor Blade Gold 25x0,20x0,125x1,7 mm"),
    ("C-25-20-125-17", "Doctor Blade Carbon 25x0,20x125x1,7 mm"),
    ("C-40-20-125-17", "Doctor Blade Carbon 40x0,20x125x1,7 mm"),
    ("SDS011A", "444-AKC-SX-BEG-N / Coated Seals W&H Miraflex 9805 (N)"),
    ("SDS115D", "444-AK-CR-GRY / Foam Seal W&H Miraflex"),
]

print("\n1. Testing search by PRODUCT CODE (should be most reliable)")
print("-"*80)

matches = 0
for code, name in test_cases:
    result = odoo.query_products(product_code=code)
    if result:
        print(f"✓ Code '{code}' → {len(result)} match(es)")
        print(f"  Product: {result[0]['name']}")
        matches += 1
    else:
        print(f"✗ Code '{code}' → NO MATCH")

print(f"\nCode-based matching: {matches}/{len(test_cases)} ({matches*100//len(test_cases)}%)")

print("\n2. Testing search by PRODUCT NAME (with normalization)")
print("-"*80)

matches = 0
for code, name in test_cases:
    result = odoo.query_products(product_name=name)
    if result:
        print(f"✓ Name '{name[:40]}...' → {len(result)} match(es)")
        matches += 1
    else:
        print(f"✗ Name '{name[:40]}...' → NO MATCH")

print(f"\nName-based matching: {matches}/{len(test_cases)} ({matches*100//len(test_cases)}%)")

print("\n3. Testing NORMALIZED name matching (comma → period)")
print("-"*80)

# Test some products that failed before
test_names = [
    "Doctor Blade Carbon 25x0,20x125x1,7 mm",
    "Doctor Blade Gold 35x0,20x125x1,7 mm",
    "3M 9353 R Easy Splice Tape",
]

matches = 0
for name in test_names:
    # First try exact
    result = odoo.query_products(product_name=name)
    if result:
        print(f"✓ Exact: '{name}' → {len(result)} match(es)")
        matches += 1
    else:
        # Try normalized (this is now automatic in the method)
        print(f"  Exact failed, trying normalized...")
        normalized = name.replace(',', '.')
        result_norm = odoo.query_products(product_name=normalized)
        if result_norm:
            print(f"✓ Normalized: '{normalized}' → {len(result_norm)} match(es)")
            matches += 1
        else:
            print(f"✗ Both failed for: '{name}'")

print(f"\nNormalized matching: {matches}/{len(test_names)} ({matches*100//len(test_names) if test_names else 0}%)")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)

odoo.close()
