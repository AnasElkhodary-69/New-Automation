"""
Test complete fix for SDS 06 extraction issue
Tests both:
1. AI semantic matching (even without SDS 06 code)
2. Product matching workflow
"""
from retriever_module.vector_store import VectorStore
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

print("="*80)
print("COMPLETE FIX TEST - SDS 06 Extraction Issue")
print("="*80)

vs = VectorStore()

# Test case 1: With only customer code (DF-3068) - simulates current extraction
print("\n" + "="*80)
print("TEST 1: Search with customer code only (DF-3068)")
print("="*80)
print("Scenario: Mistral extracted only 'DF-3068', missed 'SDS 06'")
print()

result = vs.search_product_multilevel(
    product_name="Duroseal Dichtungen W&H End seals Miraflex Grau",
    product_code="DF-3068"
)

print(f"\nResult:")
print(f"  Method: {result.get('method')}")
print(f"  Confidence: {result.get('confidence', 0):.0%}")
if result.get('match'):
    print(f"  Matched: {result['match'].get('default_code')}")
    print(f"  Name: {result['match'].get('name')}")
    if result.get('reasoning'):
        print(f"  Reasoning: {result['reasoning']}")
else:
    print("  No match found")
    if result.get('candidates'):
        print(f"  Candidates: {len(result['candidates'])}")

# Test case 2: With SDS code (ideal scenario)
print("\n" + "="*80)
print("TEST 2: Search with SDS code (SDS06)")
print("="*80)
print("Scenario: Mistral correctly extracted 'SDS 06' from 'Art. Nr.' field")
print()

result2 = vs.search_product_multilevel(
    product_name="Duroseal Dichtungen W&H End seals Miraflex Grau",
    product_code="SDS06"
)

print(f"\nResult:")
print(f"  Method: {result2.get('method')}")
print(f"  Confidence: {result2.get('confidence', 0):.0%}")
if result2.get('match'):
    print(f"  Matched: {result2['match'].get('default_code')}")
    print(f"  Name: {result2['match'].get('name')}")
else:
    print("  No match found")
    if result2.get('candidates'):
        print(f"  Candidates: {len(result2['candidates'])}")

# Test case 3: 3M 904 tape
print("\n" + "="*80)
print("TEST 3: Search for 3M 904-12-G tape")
print("="*80)

result3 = vs.search_product_multilevel(
    product_name="3M Transfer-Klebeband 904-12-G",
    product_code="904-12-G"
)

print(f"\nResult:")
print(f"  Method: {result3.get('method')}")
print(f"  Confidence: {result3.get('confidence', 0):.0%}")
if result3.get('match'):
    print(f"  Matched: {result3['match'].get('default_code')}")
    print(f"  Name: {result3['match'].get('name')}")
    if result3.get('reasoning'):
        print(f"  Reasoning: {result3['reasoning']}")
else:
    print("  No match found")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
