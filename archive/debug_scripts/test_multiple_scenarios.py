"""
Test the system with multiple real-world scenarios to validate Phase 1+2 integration
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from orchestrator.mistral_agent import MistralAgent
from retriever_module.smart_matcher import SmartProductMatcher
import json

def load_products():
    """Load products from JSON"""
    with open('odoo_database/odoo_products.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def test_scenario(name, email_text, expected_products):
    """Test a single scenario"""
    print("=" * 80)
    print(f"SCENARIO: {name}")
    print("=" * 80)
    print()

    agent = MistralAgent()
    products = load_products()
    matcher = SmartProductMatcher(products, customer_mapper=None, rag_search=None)

    # Extract entities
    print("1. EXTRACTING ENTITIES...")
    entities = agent.extract_entities(email_text)

    print(f"   Products extracted: {len(entities.get('product_names', []))}")
    print(f"   Codes extracted: {len(entities.get('product_codes', []))}")

    for idx, name in enumerate(entities.get('product_names', [])):
        print(f"   Product {idx+1}: {name[:60]}...")
        if idx < len(entities.get('product_codes', [])):
            print(f"      Code: {entities['product_codes'][idx]}")
    print()

    # Normalize codes
    print("2. NORMALIZING CODES...")
    normalized = agent.normalize_product_codes({
        'product_names': entities.get('product_names', []),
        'product_codes': entities.get('product_codes', [])
    })

    for idx, product_info in enumerate(normalized['products']):
        print(f"   Product {idx+1}: {product_info['primary_code']}")
    print()

    # Match products
    print("3. MATCHING PRODUCTS...")
    matcher.reset_matched_products()

    results = []
    for idx, product_info in enumerate(normalized['products']):
        product_name = product_info['product_name']
        product_code = product_info['primary_code']

        # Extract attributes
        attributes = agent.extract_product_attributes(product_name)

        # Match
        result = matcher.find_match({
            'product_code': product_code,
            'product_name': product_name,
            'attributes': attributes
        })

        results.append(result)

        if result.get('match'):
            match = result['match']
            print(f"   [{idx+1}] {product_code} -> {match.get('default_code')}")
            print(f"       Method: {result.get('method')}")
            print(f"       Confidence: {result.get('confidence', 0):.0%}")
        else:
            print(f"   [{idx+1}] {product_code} -> NO MATCH")
    print()

    # Validate results
    print("4. VALIDATION...")
    success = True

    for idx, (result, expected) in enumerate(zip(results, expected_products)):
        if result.get('match'):
            matched_code = result['match'].get('default_code')
            if expected in matched_code or matched_code in expected:
                print(f"   [{idx+1}] OK: Matched to {matched_code}")
            else:
                print(f"   [{idx+1}] FAIL: Expected {expected}, got {matched_code}")
                success = False
        else:
            print(f"   [{idx+1}] FAIL: Expected {expected}, got NO MATCH")
            success = False

    print()
    print("RESULT:", "PASS" if success else "FAIL")
    print("=" * 80)
    print()

    return success


def run_all_tests():
    """Run all test scenarios"""

    results = []

    # Scenario 1: Exact codes in product names (Dürrbeck scenario)
    scenario1 = """
    Dear SDS,

    Please send us:
    1. 3M Klischee-Klebeband Cushion Mount L1520, 685 x 0,55 mm, Rolle à 33m (Qty: 2)
    2. 3M Klischee-Klebeband Cushion Mount L1320, 685 x 0,55 mm, Rolle à 33m (Qty: 3)

    Best regards,
    Dürrbeck Team
    """

    results.append(test_scenario(
        "Exact codes in product names",
        scenario1,
        ['L1520', 'L1320']
    ))

    # Scenario 2: Customer code + product name (Alesco scenario)
    scenario2 = """
    Order Details:

    Article: 8060104
    Description: SDS025 - 177H DuroSeal Bobst 16S Grey
    Quantity: 5 pieces
    """

    results.append(test_scenario(
        "Customer code + product name",
        scenario2,
        ['SDS025']
    ))

    # Scenario 3: No code, only description
    scenario3 = """
    We need gaskets for our Bobst 16S machine.
    - DuroSeal brand
    - Grey color
    - Height: 177mm

    Please quote.
    """

    results.append(test_scenario(
        "No code, only description",
        scenario3,
        ['SDS025', 'RDS', 'DuroSeal']  # Should match something with these attributes
    ))

    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total scenarios: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    print(f"Success rate: {sum(results) / len(results) * 100:.0f}%")
    print("=" * 80)


if __name__ == "__main__":
    print()
    print("MULTI-SCENARIO TEST - PHASE 1+2 INTEGRATION")
    print()

    run_all_tests()
