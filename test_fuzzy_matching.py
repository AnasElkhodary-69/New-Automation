"""
Test generalized fuzzy matching on the 3 missing products
"""

import logging
import sys
from retriever_module.odoo_connector import OdooConnector

sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO, format='%(message)s')

odoo = OdooConnector()

print("="*80)
print("TESTING GENERALIZED FUZZY MATCHING")
print("="*80)

# The 3 products that previously failed
test_products = [
    ("3M 9353 R Easy Splice Tape", None),
    ("3M L1020 33 meters", None),
    ("Quicktest 38 Dyn Corona Pen", None),
]

matched = 0
total = len(test_products)

for product_name, product_code in test_products:
    print(f"\n{'='*80}")
    print(f"Testing: {product_name}")
    print("-"*80)

    result = odoo.query_products(product_name=product_name, product_code=product_code)

    if result:
        print(f"✓ FOUND {len(result)} match(es):")
        for r in result[:3]:
            print(f"   - Name: {r.get('name')}")
            print(f"     Code: {r.get('default_code', 'N/A')}")
            print(f"     Price: {r.get('list_price', 0)} EUR")
        matched += 1
    else:
        print(f"✗ NO MATCH FOUND")

print(f"\n{'='*80}")
print(f"RESULTS: {matched}/{total} products matched ({matched*100//total}%)")
print(f"{'='*80}")

odoo.close()
