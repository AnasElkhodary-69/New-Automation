"""
Debug script to analyze training pair generation for SDS products
"""
import json
from pathlib import Path

def analyze_sds_training_pairs():
    """Analyze how SDS products were included in training pairs"""

    # Load products
    with open('odoo_database/odoo_products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)

    # Filter SDS007 products
    sds007_products = [p for p in products if 'SDS007' in str(p.get('default_code', '')).upper()]

    print(f"[INFO] Found {len(sds007_products)} SDS007 products")
    print("\nSDS007 Products in Database:")
    print("=" * 80)
    for p in sds007_products:
        code = p.get('default_code', 'N/A')
        name = p.get('name', 'N/A')
        print(f"{code:15} - {name}")

    # Now simulate what training pairs would be generated
    print("\n\nSimulating Training Pair Generation:")
    print("=" * 80)

    # Find similar products (positive pairs)
    for i, prod1 in enumerate(sds007_products):
        similar_count = 0
        for j, prod2 in enumerate(sds007_products):
            if i >= j:
                continue

            # Check if they would be considered similar
            code1 = prod1.get('default_code', '').upper()
            code2 = prod2.get('default_code', '').upper()
            name1 = prod1.get('name', '').upper()
            name2 = prod2.get('name', '').upper()

            # Both start with SDS007 (same category)
            if code1.startswith('SDS007') and code2.startswith('SDS007'):
                # Check if they have similar text
                if 'DURO SEAL' in name1 and 'DURO SEAL' in name2:
                    if 'MIRAFLEX' in name1 and 'MIRAFLEX' in name2:
                        similar_count += 1
                        print(f"\n[POSITIVE PAIR]")
                        print(f"  Product 1: {code1} - {name1}")
                        print(f"  Product 2: {code2} - {name2}")

        if similar_count > 0:
            print(f"\n{code1} has {similar_count} similar products for training")

    # Test specific SDS007H and SDS007C
    print("\n\nFocusing on SDS007H and SDS007C:")
    print("=" * 80)

    sds007h = next((p for p in products if p.get('default_code') == 'SDS007H'), None)
    sds007c = next((p for p in products if p.get('default_code') == 'SDS007C'), None)

    if sds007h:
        print(f"\nSDS007H Details:")
        print(f"  Code: {sds007h.get('default_code')}")
        print(f"  Name: {sds007h.get('name')}")
        print(f"  Full text for embedding:")
        full_text_h = f"{sds007h.get('default_code', '')} {sds007h.get('name', '')}"
        print(f"  '{full_text_h}'")

    if sds007c:
        print(f"\nSDS007C Details:")
        print(f"  Code: {sds007c.get('default_code')}")
        print(f"  Name: {sds007c.get('name')}")
        print(f"  Full text for embedding:")
        full_text_c = f"{sds007c.get('default_code', '')} {sds007c.get('name', '')}"
        print(f"  '{full_text_c}'")

    # Show what customer sent
    print(f"\n\nCustomer Query:")
    print("=" * 80)
    customer_query = "DuroSeal W&H End Seals Miraflex SDS 007 CR Grau"
    print(f"  '{customer_query}'")

    # Text comparison
    print(f"\n\nText Variation Analysis:")
    print("=" * 80)
    print(f"Customer uses: 'DuroSeal' (no space)")
    print(f"Database has:  'Duro Seal' (with space)")
    print(f"")
    print(f"Customer uses: 'CR Grau' (German for gray)")
    print(f"Database has:  'CR-GRY' (English abbreviation)")
    print(f"")
    print(f"Customer uses: 'SDS 007' (with space)")
    print(f"Database has:  'SDS007H' / 'SDS007C' (no space + suffix)")
    print(f"")
    print(f"These text variations may prevent BERT from matching correctly!")

if __name__ == "__main__":
    analyze_sds_training_pairs()
