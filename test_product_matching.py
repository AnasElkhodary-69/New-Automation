"""
Product Matching Test Script

Interactive test script to validate the multi-level product matching system.
Tests product names/codes against the RAG database and shows matching results.
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from retriever_module.vector_store import VectorStore


def print_separator(char="=", length=80):
    """Print a separator line"""
    print(char * length)


def print_match_result(result, product_input):
    """
    Pretty print the match result

    Args:
        result: Match result from search_product_multilevel()
        product_input: Original product name/code from user
    """
    print_separator()
    print(f"PRODUCT INPUT: {product_input}")
    print_separator()

    # Show extraction details
    print("\nEXTRACTION:")
    if result['search_input']['product_code']:
        print(f"   Product Code: {result['search_input']['product_code']}")
    if result['search_input']['product_name']:
        print(f"   Product Name: {result['search_input']['product_name'][:80]}...")

    # Show matching method and confidence
    print(f"\nMATCHING METHOD: {result['method'].upper()}")
    print(f"   Confidence: {result['confidence']:.0%}")
    print(f"   Requires Review: {'YES (Review Required)' if result['requires_review'] else 'NO (Auto-approved)'}")

    # Show matched product
    if result['match']:
        match = result['match']
        print(f"\nMATCHED PRODUCT:")
        print(f"   Code: {match.get('default_code', 'N/A')}")
        print(f"   Name: {match.get('name', 'N/A')}")
        print(f"   Display Name: {match.get('display_name', 'N/A')}")
        print(f"   List Price: {match.get('list_price', 0.0):.2f} EUR")

        # Show additional match metadata
        if 'match_method' in match:
            print(f"   Match Method: {match['match_method']}")
        if 'match_score' in match:
            print(f"   Match Score: {match['match_score']:.0%}")

    elif result['candidates']:
        print(f"\nMULTIPLE CANDIDATES FOUND ({len(result['candidates'])}):")
        for idx, candidate in enumerate(result['candidates'][:3], 1):
            print(f"\n   Candidate {idx}:")
            print(f"      Code: {candidate.get('default_code', 'N/A')}")
            print(f"      Name: {candidate.get('name', 'N/A')[:70]}...")

    else:
        print(f"\nNO MATCH FOUND")
        print(f"   This product requires MANUAL REVIEW")

    print_separator()


def test_product(vector_store, product_input, has_code=False):
    """
    Test a single product matching

    Args:
        vector_store: VectorStore instance
        product_input: Product name or code from user
        has_code: Whether the input is a product code
    """
    # Parse input - try to extract product code from name if present
    if has_code:
        product_code = product_input
        product_name = None
    else:
        # Try to extract product code from the beginning of the string (e.g., "SDS025 - ...")
        import re
        code_match = re.match(r'^([A-Z0-9\-]+)\s*-\s*(.+)$', product_input)
        if code_match:
            product_code = code_match.group(1).strip()
            product_name = product_input  # Keep full name for attribute extraction
        else:
            product_code = None
            product_name = product_input

    # Search using multi-level matching
    result = vector_store.search_product_multilevel(
        product_name=product_name,
        product_code=product_code
    )

    # Print results
    print_match_result(result, product_input)

    # Return result for programmatic use
    return result


def interactive_mode():
    """Interactive testing mode - ask user for products to test"""
    print_separator("=")
    print("PRODUCT MATCHING TEST SCRIPT")
    print_separator("=")
    print("\nLoading vector store...")

    # Initialize vector store
    vector_store = VectorStore()

    stats = vector_store.get_stats()
    print(f"\nLoaded {stats['total_products']} products from database")
    print(f"Loaded {stats['total_customers']} customers from database")

    print("\nMatching Thresholds:")
    for key, value in stats['thresholds'].items():
        print(f"   {key}: {value:.2f}")

    print("\n" + "="*80)
    print("INSTRUCTIONS:")
    print("  - Enter a product name or code to test matching")
    print("  - Type 'code:XYZ' to search specifically by code")
    print("  - Type 'quit' or 'exit' to stop")
    print("="*80)

    # Interactive loop
    while True:
        print("\n")
        user_input = input("Enter product name or code (or 'quit'): ").strip()

        if not user_input:
            continue

        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\nExiting test script. Goodbye!")
            break

        # Check if user specified it's a code
        if user_input.lower().startswith('code:'):
            product_input = user_input[5:].strip()
            has_code = True
        else:
            product_input = user_input
            has_code = False

        # Test the product
        try:
            test_product(vector_store, product_input, has_code)
        except Exception as e:
            print(f"\nERROR: {str(e)}")
            import traceback
            traceback.print_exc()


def batch_test_mode(test_cases):
    """
    Batch testing mode - test multiple products at once

    Args:
        test_cases: List of tuples (product_name, product_code)
    """
    print_separator("=")
    print("🧪 BATCH PRODUCT MATCHING TEST")
    print_separator("=")
    print(f"\nTesting {len(test_cases)} products...\n")

    # Initialize vector store
    vector_store = VectorStore()

    results = []
    for idx, (product_name, product_code) in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST {idx}/{len(test_cases)}")
        print(f"{'='*80}")

        result = test_product(
            vector_store,
            product_code if product_code else product_name,
            has_code=bool(product_code)
        )
        results.append(result)

    # Print summary
    print("\n" + "="*80)
    print("📊 BATCH TEST SUMMARY")
    print("="*80)

    total = len(results)
    matched = sum(1 for r in results if r['match'])
    auto_approved = sum(1 for r in results if r['match'] and not r['requires_review'])
    review_required = sum(1 for r in results if r['match'] and r['requires_review'])
    no_match = total - matched

    print(f"\nTotal Tests: {total}")
    print(f"  OK: Matched: {matched} ({matched/total*100:.0f}%)")
    print(f"  OK: Auto-approved: {auto_approved} ({auto_approved/total*100:.0f}%)")
    print(f"  WARNING:  Review required: {review_required} ({review_required/total*100:.0f}%)")
    print(f"  ERROR: No match: {no_match} ({no_match/total*100:.0f}%)")

    # Method breakdown
    methods = {}
    for r in results:
        if r['match']:
            method = r['method']
            methods[method] = methods.get(method, 0) + 1

    if methods:
        print(f"\n📋 Methods Used:")
        for method, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
            print(f"  {method}: {count}")

    print("="*80)


if __name__ == "__main__":
    # Check if running in batch mode with test cases
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        # Example batch test cases
        test_cases = [
            ("SDS025 - 177H DuroSeal Bobst 16S Grey", "SDS025"),
            ("Doctor Blade Gold 25mm for Bobst", None),
            ("3M Cushion Mount Plus E1820", None),
            ("Tesa Tape 51036", "51036"),
            ("Unknown Product XYZ123", None),
        ]
        batch_test_mode(test_cases)
    else:
        # Interactive mode
        interactive_mode()
