"""
RAG Workflow Test Script

Interactive test script that uses the full app workflow to find products in Odoo.
Tests the complete matching pipeline: Extraction → JSON Search → RAG → Odoo Matching
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from retriever_module.vector_store import VectorStore
from retriever_module.odoo_connector import OdooConnector


def print_separator(char="=", length=80):
    """Print a separator line"""
    print(char * length)


def test_product_workflow(product_input: str, vector_store: VectorStore, odoo: OdooConnector):
    """
    Test complete product matching workflow

    Args:
        product_input: Product name/description from user
        vector_store: VectorStore instance with RAG
        odoo: Odoo connector instance
    """
    print_separator()
    print(f"PRODUCT INPUT: {product_input}")
    print_separator()

    # STEP 1: Multi-level matching (includes RAG)
    print("\nSTEP 1: MULTI-LEVEL MATCHING (JSON + RAG)")
    print("-" * 80)

    # Try to extract product code from input (simple pattern)
    import re
    code_match = re.match(r'^([A-Z0-9\-]+)\s*-\s*(.+)$', product_input)
    if code_match:
        product_code = code_match.group(1).strip()
        product_name = product_input
    else:
        product_code = None
        product_name = product_input

    if product_code:
        print(f"   Extracted Code: {product_code}")
    print(f"   Search Name: {product_name}")

    # Search using multi-level matching
    result = vector_store.search_product_multilevel(
        product_name=product_name,
        product_code=product_code
    )

    # Display matching results
    print(f"\n   MATCHING RESULT:")
    print(f"   Method: {result['method'].upper()}")
    print(f"   Confidence: {result['confidence']:.0%}")
    print(f"   Requires Review: {'YES' if result['requires_review'] else 'NO'}")

    if result['match']:
        match = result['match']
        print(f"\n   MATCHED IN JSON:")
        print(f"   Code: {match.get('default_code', 'N/A')}")
        print(f"   Name: {match.get('name', 'N/A')[:70]}...")
        print(f"   List Price: {match.get('list_price', 0.0):.2f} EUR")

        # Show candidates if multiple matches
        if result.get('candidates'):
            print(f"\n   OTHER CANDIDATES ({len(result['candidates'])}):")
            for idx, candidate in enumerate(result['candidates'][:3], 1):
                score = candidate.get('similarity_score', candidate.get('match_score', 0))
                print(f"      {idx}. {candidate.get('default_code', 'N/A')} - {candidate.get('name', 'N/A')[:60]}... ({score:.0%})")

        # STEP 2: Search in Odoo
        print(f"\nSTEP 2: ODOO DATABASE SEARCH")
        print("-" * 80)

        json_code = match.get('default_code')
        if json_code:
            print(f"   Searching Odoo for product code: {json_code}")

            try:
                # Search by product code
                odoo_products = odoo.query_products(product_code=json_code)

                if odoo_products and len(odoo_products) > 0:
                    odoo_product = odoo_products[0]  # Take first match
                    print(f"\n   FOUND IN ODOO:")
                    print(f"   Odoo ID: {odoo_product.get('id')}")
                    print(f"   Code: {odoo_product.get('default_code', 'N/A')}")
                    print(f"   Name: {odoo_product.get('name', 'N/A')[:70]}...")
                    print(f"   List Price: {odoo_product.get('list_price', 0.0):.2f} EUR")
                    print(f"   Standard Price: {odoo_product.get('standard_price', 0.0):.2f} EUR")

                    # STEP 3: Final Summary
                    print(f"\nSTEP 3: FINAL SUMMARY")
                    print("-" * 80)
                    print(f"   STATUS: SUCCESS")
                    print(f"   Match Quality: {result['method'].upper()} ({result['confidence']:.0%})")
                    print(f"   JSON Match: {match.get('default_code')}")
                    print(f"   Odoo ID: {odoo_product.get('id')}")
                    print(f"   Ready for Order Creation: {'YES' if result['confidence'] >= 0.95 else 'NEEDS REVIEW'}")

                else:
                    print(f"\n   NOT FOUND IN ODOO")
                    print(f"   The product exists in JSON but not in Odoo database")
                    print(f"   This may indicate database synchronization issues")

                    print(f"\nSTEP 3: FINAL SUMMARY")
                    print("-" * 80)
                    print(f"   STATUS: PARTIAL SUCCESS")
                    print(f"   JSON Match: {match.get('default_code')}")
                    print(f"   Odoo Match: NOT FOUND")
                    print(f"   Action Required: Product needs to be added to Odoo")

            except Exception as e:
                print(f"\n   ERROR searching Odoo: {str(e)}")

                print(f"\nSTEP 3: FINAL SUMMARY")
                print("-" * 80)
                print(f"   STATUS: ERROR")
                print(f"   Error: {str(e)}")
        else:
            print(f"   No product code to search in Odoo")

            print(f"\nSTEP 3: FINAL SUMMARY")
            print("-" * 80)
            print(f"   STATUS: INCOMPLETE")
            print(f"   Issue: Matched product has no code")

    else:
        # No match found
        print(f"\n   NO MATCH FOUND")
        print(f"   This product could not be matched in the database")

        print(f"\nSTEP 2: ODOO DATABASE SEARCH")
        print("-" * 80)
        print(f"   Skipped (no JSON match)")

        print(f"\nSTEP 3: FINAL SUMMARY")
        print("-" * 80)
        print(f"   STATUS: FAILED")
        print(f"   Match Quality: NO MATCH")
        print(f"   Action Required: MANUAL REVIEW NEEDED")

    print_separator()


def interactive_mode():
    """Interactive testing mode"""
    print_separator("=")
    print("RAG WORKFLOW TEST SCRIPT")
    print_separator("=")
    print("\nInitializing system...")

    # Initialize components
    print("  Loading vector store with RAG...")
    vector_store = VectorStore(enable_rag=True)

    print("  Connecting to Odoo...")
    odoo = OdooConnector()

    # Show system stats
    stats = vector_store.get_stats()
    print(f"\n  Loaded {stats['total_products']} products from JSON database")
    print(f"  RAG Enabled: {vector_store.enable_rag}")
    print(f"  RAG Threshold: {vector_store.rag_threshold:.2f}")

    print("\n" + "="*80)
    print("INSTRUCTIONS:")
    print("  - Enter a product name or description to test the full workflow")
    print("  - The system will:")
    print("    1. Search in JSON database (with RAG semantic search)")
    print("    2. Match result in Odoo database")
    print("    3. Show complete workflow results")
    print("  - Type 'quit' or 'exit' to stop")
    print("="*80)

    # Interactive loop
    while True:
        print("\n")
        user_input = input("Enter product name or description (or 'quit'): ").strip()

        if not user_input:
            continue

        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\nExiting test script. Goodbye!")
            break

        # Test the product
        try:
            test_product_workflow(user_input, vector_store, odoo)
        except Exception as e:
            print(f"\nERROR: {str(e)}")
            import traceback
            traceback.print_exc()


def batch_test_mode():
    """Batch testing mode with predefined test cases"""
    print_separator("=")
    print("RAG WORKFLOW BATCH TEST")
    print_separator("=")

    # Initialize components
    print("\nInitializing system...")
    vector_store = VectorStore(enable_rag=True)
    odoo = OdooConnector()

    # Test cases
    test_cases = [
        # Product with code prefix
        "SDS025 - 177H DuroSeal Bobst 16S Grey",

        # Product without clear code (RAG should help)
        "Duroseal Dichtungen W&H End seals Miraflex Grau",

        # Brand-based product
        "3M Cushion Mount Plus E1820",

        # Doctor Blade
        "Doctor Blade Gold 25x0,20",

        # Unknown product (should fail)
        "Random Unknown Product XYZ999",
    ]

    print(f"\nTesting {len(test_cases)} products...\n")

    for idx, product in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST {idx}/{len(test_cases)}")
        test_product_workflow(product, vector_store, odoo)

    print("\n" + "="*80)
    print("BATCH TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        batch_test_mode()
    else:
        interactive_mode()
