"""
Test script to validate product matching quality
Run this to identify and debug matching issues
"""

import json
import logging
from pathlib import Path
from retriever_module.vector_store import VectorStore
from fix_extraction import validate_extraction

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_product_matching():
    """Test product matching with various scenarios"""

    print("\n" + "="*80)
    print("PRODUCT MATCHING QUALITY TEST")
    print("="*80 + "\n")

    # Initialize vector store
    vector_store = VectorStore()

    # Test cases representing common product formats
    test_cases = [
        {
            "name": "Exact Code Match",
            "product_name": "Doctor Blade Gold 25x0.20",
            "product_code": "SDS025",
            "expected_match": True
        },
        {
            "name": "Code in Name",
            "product_name": "3M L1520 685mm x 0.55mm",
            "product_code": "",
            "expected_match": True
        },
        {
            "name": "No Code - Name Only",
            "product_name": "Heat Seal Tape Blue 50mm",
            "product_code": "",
            "expected_match": True
        },
        {
            "name": "Fuzzy Code Match",
            "product_name": "Product with code",
            "product_code": "SDS-025-A",  # Has dashes
            "expected_match": True
        },
        {
            "name": "Customer vs Product Code",
            "product_name": "Doctor Blade",
            "product_code": "1234567",  # Customer internal code
            "expected_match": False
        }
    ]

    results = []
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"  Product: {test['product_name']}")
        print(f"  Code: {test['product_code'] or '(no code)'}")

        # Search product
        result = vector_store.search_product_multilevel(
            product_name=test['product_name'],
            product_code=test['product_code'] if test['product_code'] else None
        )

        # Check result
        matched = result['match'] is not None
        confidence = result['confidence']
        method = result['method']

        print(f"  Result: {'MATCHED' if matched else 'NO MATCH'}")
        print(f"  Confidence: {confidence:.0%}")
        print(f"  Method: {method}")

        if matched:
            print(f"  Found: {result['match'].get('name', '')[:50]}")
            print(f"  DB Code: {result['match'].get('default_code', '')}")

        # Track results
        results.append({
            'test': test['name'],
            'matched': matched,
            'expected': test['expected_match'],
            'passed': matched == test['expected_match'],
            'confidence': confidence,
            'method': method
        })

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for r in results if r['passed'])
    total = len(results)

    print(f"\nTests Passed: {passed}/{total} ({passed/total*100:.0f}%)")

    print("\nDetailed Results:")
    for r in results:
        status = "PASS" if r['passed'] else "FAIL"
        print(f"  [{status}] {r['test']}: {r['method']} ({r['confidence']:.0%})")

    # Check database status
    print("\n" + "="*80)
    print("DATABASE STATUS")
    print("="*80)

    print(f"Products loaded: {len(vector_store.products_data)}")
    print(f"Customers loaded: {len(vector_store.customers_data)}")

    # Sample products to verify data
    if vector_store.products_data:
        print("\nSample products in database:")
        for i, product in enumerate(vector_store.products_data[:5]):
            print(f"  {i+1}. {product.get('default_code', 'NO_CODE')}: {product.get('name', '')[:50]}")

    return results


def test_extraction_alignment():
    """Test if extraction maintains product-attribute alignment"""

    print("\n" + "="*80)
    print("EXTRACTION ALIGNMENT TEST")
    print("="*80 + "\n")

    # Simulate extraction results
    test_extractions = [
        {
            "name": "Aligned Arrays",
            "entities": {
                "product_names": ["Product A", "Product B", "Product C"],
                "product_codes": ["CODE-A", "CODE-B", "CODE-C"],
                "product_quantities": [10, 20, 30],
                "product_prices": [100, 200, 300]
            }
        },
        {
            "name": "Missing Codes",
            "entities": {
                "product_names": ["Product A", "Product B", "Product C"],
                "product_codes": ["CODE-A"],  # Only 1 code for 3 products!
                "product_quantities": [10, 20, 30],
                "product_prices": [100, 200, 300]
            }
        },
        {
            "name": "Missing Quantities",
            "entities": {
                "product_names": ["Product A", "Product B"],
                "product_codes": ["CODE-A", "CODE-B"],
                "product_quantities": [10],  # Only 1 quantity for 2 products!
                "product_prices": [100, 200]
            }
        }
    ]

    for test in test_extractions:
        print(f"\nTest: {test['name']}")

        entities = test['entities']
        validation = validate_extraction(entities)

        print(f"  Products: {len(entities['product_names'])}")
        print(f"  Codes: {len(entities['product_codes'])}")
        print(f"  Quantities: {len(entities['product_quantities'])}")
        print(f"  Prices: {len(entities['product_prices'])}")

        print(f"  Valid: {'YES' if validation['valid'] else 'NO'}")
        if validation['issues']:
            print(f"  Issues: {', '.join(validation['issues'])}")

        # Show stats
        for key, value in validation['stats'].items():
            print(f"  {key}: {value}")


def diagnose_json_database():
    """Diagnose issues with JSON database"""

    print("\n" + "="*80)
    print("JSON DATABASE DIAGNOSIS")
    print("="*80 + "\n")

    # Check if files exist
    customers_path = Path("odoo_database/odoo_customers.json")
    products_path = Path("odoo_database/odoo_products.json")

    print(f"Customers file exists: {customers_path.exists()}")
    print(f"Products file exists: {products_path.exists()}")

    if products_path.exists():
        with open(products_path, 'r', encoding='utf-8') as f:
            products = json.load(f)

        # Analyze product codes
        products_with_codes = [p for p in products if p.get('default_code')]
        products_without_codes = [p for p in products if not p.get('default_code')]

        print(f"\nProduct Statistics:")
        print(f"  Total products: {len(products)}")
        print(f"  With codes: {len(products_with_codes)} ({len(products_with_codes)/len(products)*100:.0f}%)")
        print(f"  Without codes: {len(products_without_codes)} ({len(products_without_codes)/len(products)*100:.0f}%)")

        # Check code patterns
        code_patterns = {}
        for p in products_with_codes:
            code = p.get('default_code', '')
            if code:
                # Extract pattern prefix
                import re
                prefix_match = re.match(r'^([A-Z]+)', code)
                if prefix_match:
                    prefix = prefix_match.group(1)
                    code_patterns[prefix] = code_patterns.get(prefix, 0) + 1

        print(f"\nCode Patterns Found:")
        for prefix, count in sorted(code_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {prefix}: {count} products")

    # Check for backup files
    backup_customers = Path("odoo_database/odoo_customers.json.backup")
    backup_products = Path("odoo_database/odoo_products.json.backup")

    if backup_customers.exists() or backup_products.exists():
        print(f"\nWARNING: Backup files found!")
        print(f"  This suggests the database was previously synchronized.")
        print(f"  Run sync_databases.py to update from current Odoo.")


if __name__ == "__main__":
    # Run all tests
    test_product_matching()
    test_extraction_alignment()
    diagnose_json_database()

    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    print("""
1. Run sync_databases.py to synchronize JSON with current Odoo
2. Update extraction to use extraction_prompt_v2.txt
3. Monitor extraction alignment with this test script
4. Review products without codes in the database
    """)