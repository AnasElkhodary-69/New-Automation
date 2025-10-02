"""
Search for the 3 missing products in Odoo database
"""

import logging
from retriever_module.odoo_connector import OdooConnector

logging.basicConfig(level=logging.INFO)

odoo = OdooConnector()

print("="*80)
print("SEARCHING FOR MISSING PRODUCTS IN ODOO")
print("="*80)

missing_products = [
    "3M 9353 R Easy Splice Tape",
    "3M L1020 33 meters",
    "Quicktest 38 Dyn Corona Pen"
]

for product_name in missing_products:
    print(f"\n{'='*80}")
    print(f"Searching for: {product_name}")
    print("="*80)

    # Try different search strategies

    # 1. Search by full name
    print("\n1. Full name search:")
    result = odoo.query_products(product_name=product_name)
    if result:
        print(f"   FOUND {len(result)} match(es)")
        for r in result[:3]:
            print(f"   - {r.get('name')} (Code: {r.get('default_code', 'N/A')})")
    else:
        print("   NO MATCH")

    # 2. Search by partial name
    parts = product_name.split()
    for i in range(len(parts), 0, -1):
        partial = " ".join(parts[:i])
        if partial != product_name:
            print(f"\n2. Partial search: '{partial}'")
            result = odoo.query_products(product_name=partial)
            if result:
                print(f"   FOUND {len(result)} match(es)")
                for r in result[:5]:
                    print(f"   - {r.get('name')} (Code: {r.get('default_code', 'N/A')})")
                break

    # 3. Search by key terms
    if "3M" in product_name:
        print(f"\n3. Brand search: '3M'")
        result = odoo.query_products(product_name="3M")
        if result:
            print(f"   FOUND {len(result)} match(es) - showing first 10:")
            for r in result[:10]:
                if any(term in r.get('name', '') for term in parts):
                    print(f"   * {r.get('name')} (Code: {r.get('default_code', 'N/A')})")

    if "Quicktest" in product_name:
        print(f"\n3. Brand search: 'Quicktest'")
        result = odoo.query_products(product_name="Quicktest")
        if result:
            print(f"   FOUND {len(result)} match(es):")
            for r in result[:10]:
                print(f"   - {r.get('name')} (Code: {r.get('default_code', 'N/A')})")

print("\n" + "="*80)

odoo.close()
