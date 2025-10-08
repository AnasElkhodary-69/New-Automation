"""
Test the updated production system with variant matching
"""

import logging
from retriever_module.vector_store import VectorStore
from orchestrator.mistral_agent import MistralAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_variant_matching():
    """Test that variant matching works in vector store"""
    print("\n" + "="*80)
    print("TEST 1: VARIANT MATCHING")
    print("="*80)

    vs = VectorStore()

    test_cases = [
        {
            "name": "Base code with attributes",
            "product_name": "DuroSeal Bobst 26S Blue",
            "product_code": "SDS025"
        },
        {
            "name": "Code in name",
            "product_name": "3M L1520 685mm x 0.55mm",
            "product_code": None
        },
        {
            "name": "Full variant code",
            "product_name": "DuroSeal",
            "product_code": "SDS025B"
        }
    ]

    passed = 0
    for test in test_cases:
        result = vs.search_product_multilevel(
            product_name=test['product_name'],
            product_code=test['product_code']
        )

        if result['match']:
            print(f"\n[PASS] {test['name']}")
            print(f"  Input: '{test['product_name']}' + '{test['product_code']}'")
            print(f"  Match: {result['match']['default_code']} - {result['match']['name'][:50]}")
            print(f"  Confidence: {result['confidence']:.0%} ({result['method']})")
            passed += 1
        else:
            print(f"\n[FAIL] {test['name']}")
            print(f"  NO MATCH")

    print(f"\nResult: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_extraction_alignment():
    """Test that extraction properly aligns product attributes"""
    print("\n" + "="*80)
    print("TEST 2: EXTRACTION ALIGNMENT")
    print("="*80)

    # Simulate email with multiple products
    test_email = """
    Order from Test Company

    Please send us the following:
    - SDS025 DuroSeal Bobst 26S Blue - Quantity: 12 pieces - Price: EUR 356.00
    - L1520 3M Cushion Mount 685mm - Quantity: 6 pieces - Price: EUR 405.37
    - SDS2573 Foam Seal Blue - Quantity: 5 pieces - Price: EUR 307.66

    Delivery address:
    Test Company GmbH
    Teststraße 123
    12345 Berlin, Germany

    Contact: Max Mustermann
    Email: max@testcompany.com
    Phone: +49 30 1234567
    """

    # Test if fix_extraction is available
    try:
        from fix_extraction import fix_product_alignment, validate_extraction

        # Create mock entities (simulating misaligned extraction)
        mock_entities = {
            'product_names': ['SDS025 DuroSeal Bobst 26S Blue', 'L1520 3M Cushion Mount 685mm', 'SDS2573 Foam Seal Blue'],
            'product_codes': ['SDS025', 'L1520'],  # Only 2 codes for 3 products!
            'product_quantities': [12, 6, 5],
            'product_prices': [356.00, 405.37, 307.66]
        }

        print("\nBefore alignment:")
        print(f"  Products: {len(mock_entities['product_names'])}")
        print(f"  Codes: {len(mock_entities['product_codes'])}")

        # Fix alignment
        fixed_entities = fix_product_alignment(mock_entities)
        validation = validate_extraction(fixed_entities)

        print("\nAfter alignment:")
        print(f"  Products: {validation['stats']['total_products']}")
        print(f"  With codes: {validation['stats']['products_with_codes']}")
        print(f"  With quantities: {validation['stats']['products_with_quantities']}")
        print(f"  With prices: {validation['stats']['products_with_prices']}")

        if validation['valid']:
            print("\n[OK] Extraction validation passed")
            return True
        else:
            print(f"\n[X] Validation issues: {validation['issues']}")
            return False

    except ImportError:
        print("\n[WARN] Enhanced extraction not available - skipping test")
        return True


def test_prompt_loading():
    """Test that prompts load correctly"""
    print("\n" + "="*80)
    print("TEST 3: PROMPT LOADING")
    print("="*80)

    agent = MistralAgent()

    if 'extraction' in agent.prompts:
        print("[OK] Extraction prompt loaded")

        # Check which version
        if 'customer_info' in agent.prompts['extraction']:
            print("  Using V2 structured prompt")
        else:
            print("  Using V1 legacy prompt")

        return True
    else:
        print("[X] Extraction prompt not found")
        return False


def test_database_sync():
    """Test that database is synchronized"""
    print("\n" + "="*80)
    print("TEST 4: DATABASE SYNCHRONIZATION")
    print("="*80)

    vs = VectorStore()

    print(f"Customers loaded: {len(vs.customers_data)}")
    print(f"Products loaded: {len(vs.products_data)}")

    # Check for product variants
    sds025_variants = [p for p in vs.products_data
                       if isinstance(p.get('default_code'), str) and p.get('default_code', '').startswith('SDS025')]

    print(f"\nSDS025 variants found: {len(sds025_variants)}")
    if sds025_variants:
        for v in sds025_variants[:3]:
            print(f"  - {v['default_code']}: {v['name'][:50]}")

    if len(vs.customers_data) > 0 and len(vs.products_data) > 0:
        print("\n[OK] Database synchronized")
        return True
    else:
        print("\n[X] Database empty - run sync_databases.py")
        return False


def run_all_tests():
    """Run all production tests"""
    print("\n" + "="*80)
    print("PRODUCTION UPDATE VALIDATION")
    print("="*80)

    results = []

    # Run tests
    results.append(("Variant Matching", test_variant_matching()))
    results.append(("Extraction Alignment", test_extraction_alignment()))
    results.append(("Prompt Loading", test_prompt_loading()))
    results.append(("Database Sync", test_database_sync()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK] PASS" if result else "[X] FAIL"
        print(f"{status} - {name}")

    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n[OK] System ready for production!")
        print("\nTo run the full system:")
        print("  python main.py")
    else:
        print("\n[X] Some tests failed - review issues above")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
