"""
Test PHASE 2: SmartProductMatcher

Tests the 7-level matching cascade with real product database
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from retriever_module.smart_matcher import SmartProductMatcher
from orchestrator.mistral_agent import MistralAgent


def load_products():
    """Load products from JSON"""
    with open('odoo_database/odoo_products.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def test_exact_code_match():
    """Test Level 1: Exact code matching"""
    print("="*80)
    print("TEST 1: EXACT CODE MATCHING (Level 1)")
    print("="*80)

    products = load_products()
    matcher = SmartProductMatcher(products, customer_mapper=None, rag_search=None)
    agent = MistralAgent()

    # Test: L1520 with 685mm width
    test_product = {
        'product_code': 'L1520',
        'product_name': '3M Cushion Mount L1520, 685 x 0,55 mm, Rolle à 33m',
        'attributes': agent.extract_product_attributes('3M Cushion Mount L1520, 685 x 0,55 mm, Rolle à 33m')
    }

    print(f"\nTest Product:")
    print(f"   Code: {test_product['product_code']}")
    print(f"   Name: {test_product['product_name']}")
    print(f"   Width: {test_product['attributes']['dimensions']['width']}mm")

    result = matcher.find_match(test_product)

    print(f"\nResult:")
    print(f"   Method: {result.get('method')}")
    print(f"   Confidence: {result.get('confidence', 0):.2f}")
    if result.get('match'):
        print(f"   Matched Code: {result['match'].get('default_code')}")
        print(f"   Matched Name: {result['match'].get('name', '')[:60]}")
    print(f"   Requires Review: {result.get('requires_review', False)}")

    print("\n" + "="*80)


def test_duplicate_prevention():
    """Test duplicate product detection"""
    print("="*80)
    print("TEST 2: DUPLICATE PREVENTION")
    print("="*80)

    products = load_products()
    matcher = SmartProductMatcher(products, customer_mapper=None, rag_search=None)
    agent = MistralAgent()

    # Test: L1520 and L1320 (should NOT both match to E1015)
    test_products = [
        {
            'product_code': 'L1520',
            'product_name': '3M Cushion Mount L1520, 685 x 0,55 mm',
            'attributes': agent.extract_product_attributes('3M Cushion Mount L1520, 685 x 0,55 mm')
        },
        {
            'product_code': 'L1320',
            'product_name': '3M Cushion Mount L1320, 685 x 0,55 mm',
            'attributes': agent.extract_product_attributes('3M Cushion Mount L1320, 685 x 0,55 mm')
        }
    ]

    results = []
    for test_product in test_products:
        print(f"\nMatching: {test_product['product_code']}")
        result = matcher.find_match(test_product)
        results.append(result)

        if result.get('match'):
            print(f"   -> Matched to: {result['match'].get('default_code')}")
        else:
            print(f"   -> No match")

    # Check for duplicates
    matched_codes = [r['match'].get('default_code') for r in results if r.get('match')]
    print(f"\n\nMatched Codes: {matched_codes}")

    if len(matched_codes) == len(set(matched_codes)):
        print("OK SUCCESS: No duplicates detected!")
    else:
        print("X FAIL: Duplicate products matched!")

    print("\n" + "="*80)


def test_attribute_matching():
    """Test Level 3: Pure attribute matching (NO CODE)"""
    print("="*80)
    print("TEST 3: ATTRIBUTE MATCHING (Level 3 - NO CODE)")
    print("="*80)

    products = load_products()
    matcher = SmartProductMatcher(products, customer_mapper=None, rag_search=None)
    agent = MistralAgent()

    # Test: No code, only description
    test_product = {
        'product_code': 'NO_CODE_FOUND',
        'product_name': 'DuroSeal gaskets for Bobst 16S machine, Grey, 177mm height',
        'attributes': agent.extract_product_attributes('DuroSeal gaskets for Bobst 16S machine, Grey, 177mm height')
    }

    print(f"\nTest Product (NO CODE):")
    print(f"   Name: {test_product['product_name']}")
    print(f"   Brand: {test_product['attributes']['brand']}")
    print(f"   Machine: {test_product['attributes']['machine_type']}")
    print(f"   Color: {test_product['attributes']['color']}")

    result = matcher.find_match(test_product)

    print(f"\nResult:")
    print(f"   Method: {result.get('method')}")
    print(f"   Confidence: {result.get('confidence', 0):.2f}")
    if result.get('match'):
        print(f"   Matched Code: {result['match'].get('default_code')}")
        print(f"   Matched Name: {result['match'].get('name', '')[:70]}")
        print(f"   Attribute Score: {result.get('attribute_match_score', 0):.2f}")
    else:
        print(f"   No match found")

    print("\n" + "="*80)


def test_real_failed_emails():
    """Test with actual failed email scenarios"""
    print("="*80)
    print("TEST 4: REAL FAILED EMAIL SCENARIOS")
    print("="*80)

    products = load_products()
    matcher = SmartProductMatcher(products, customer_mapper=None, rag_search=None)
    agent = MistralAgent()

    # Email 1: Duerrbeck
    print("\n[EMAIL 1] Duerrbeck Order")
    print("   Problem: Both L1520 and L1320 matched to E1015-685 (WRONG)")

    email1_products = [
        {
            'product_code': 'L1520',
            'product_name': '3M Klischee-Klebeband Cushion Mount L1520, 685 x 0,55 mm, Rolle à 33m',
            'attributes': agent.extract_product_attributes('3M Klischee-Klebeband Cushion Mount L1520, 685 x 0,55 mm, Rolle à 33m')
        },
        {
            'product_code': 'L1320',
            'product_name': '3M Klischee-Klebeband Cushion Mount L1320, 685 x 0,55 mm, Rolle à 33m',
            'attributes': agent.extract_product_attributes('3M Klischee-Klebeband Cushion Mount L1320, 685 x 0,55 mm, Rolle à 33m')
        }
    ]

    matcher.reset_matched_products()  # Reset for new order
    for idx, product in enumerate(email1_products, 1):
        print(f"\n   Product {idx}: {product['product_code']}")
        result = matcher.find_match(product)

        if result.get('match'):
            matched_code = result['match'].get('default_code')
            matched_name = result['match'].get('name', '')
            print(f"      OK Matched: {matched_code}")
            print(f"      Name: {matched_name[:50]}")
            print(f"      Confidence: {result.get('confidence', 0):.2f}")

            # Check if correct
            if product['product_code'] in matched_code:
                print(f"      OKOK CORRECT MATCH!")
            else:
                print(f"      XX WRONG MATCH!")
        else:
            print(f"      X No match found")

    # Email 2: Alesco
    print("\n" + "-"*80)
    print("\n[EMAIL 2] Alesco Order")
    print("   Problem: Code 8060104 (customer code) matched to HEAT SEAL 1282 (WRONG)")
    print("   Expected: Should match SDS025A")

    # First normalize the code
    email2_data = {
        'product_names': ['SDS025 - 177H DuroSeal Bobst 16S Grey'],
        'product_codes': ['8060104']
    }

    normalized = agent.normalize_product_codes(email2_data)
    product_info = normalized['products'][0]

    print(f"\n   Normalized Code: {product_info['primary_code']}")

    email2_product = {
        'product_code': product_info['primary_code'],
        'product_name': product_info['product_name'],
        'attributes': agent.extract_product_attributes(product_info['product_name'])
    }

    matcher.reset_matched_products()  # Reset for new order
    result = matcher.find_match(email2_product)

    if result.get('match'):
        matched_code = result['match'].get('default_code')
        matched_name = result['match'].get('name', '')
        print(f"      OK Matched: {matched_code}")
        print(f"      Name: {matched_name[:60]}")
        print(f"      Method: {result.get('method')}")
        print(f"      Confidence: {result.get('confidence', 0):.2f}")

        # Check if correct
        if 'SDS025' in matched_code:
            print(f"      OKOK CORRECT MATCH!")
        else:
            print(f"      XX WRONG MATCH (expected SDS025)")
    else:
        print(f"      X No match found")

    print("\n" + "="*80)
    print("PHASE 2 TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    print("\nPHASE 2 IMPLEMENTATION TEST")
    print("Testing: SmartProductMatcher (7-level cascade)\n")

    # Run tests
    test_exact_code_match()
    print("\n")
    test_duplicate_prevention()
    print("\n")
    test_attribute_matching()
    print("\n")
    test_real_failed_emails()

    print("\nAll tests complete!")
    print("Next: Integrate SmartProductMatcher into processor")
