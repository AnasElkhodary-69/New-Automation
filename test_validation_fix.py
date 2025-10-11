#!/usr/bin/env python3
"""
Test Product Validation Fix
Simulates processing the "Klebeband" email to verify validation works
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.product_validator import is_valid_product_code, validate_product_codes, get_code_confidence
from retriever_module.token_matcher import TokenMatcher

print("="*100)
print("TESTING PRODUCT VALIDATION FIX")
print("="*100)
print()

# Test 1: Validate generic terms are rejected
print("[TEST 1] Product Code Validation")
print("-"*100)

test_codes = [
    ("Klebeband", False, "Generic term"),
    ("3M851-50-66", True, "Valid code"),
    ("tape", False, "Generic term"),
    ("SDS1951", True, "Valid code"),
    ("Rakel", False, "Generic term"),
    ("L1020-685-33", True, "Valid code"),
]

for code, expected_valid, description in test_codes:
    is_valid, reason = is_valid_product_code(code)
    status = "[OK]" if is_valid == expected_valid else "[FAIL]"
    print(f"{status} '{code}': {is_valid} ({reason}) - {description}")

print()
print()

# Test 2: Validate products list
print("[TEST 2] Product List Validation")
print("-"*100)

products = [
    {"code": "Klebeband", "name": "Generic adhesive tape"},
    {"code": "3M851-50-66", "name": "3M 851 Polyester Tape"},
    {"code": "Rakel", "name": "Doctor blade"},
    {"code": "SDS1951", "name": "SDS Doctor Blade 1951"},
]

valid, invalid = validate_product_codes(products)

print(f"Valid products: {len(valid)}")
for prod in valid:
    print(f"  - {prod['code']}: {prod['name']}")

print()
print(f"Invalid products: {len(invalid)}")
for prod in invalid:
    print(f"  - {prod['code']}: {prod['rejection_reason']}")

print()
print()

# Test 3: Token Matcher rejects generic terms
print("[TEST 3] Token Matcher Integration")
print("-"*100)

matcher = TokenMatcher()

# Should reject generic term
print("\nSearching for 'Klebeband' (should be rejected):")
results = matcher.search("Klebeband", top_k=3)
if len(results) == 0:
    print("  [OK] Generic term rejected - no results returned")
else:
    print(f"  [FAIL] Generic term not rejected - {len(results)} results returned")
    for r in results[:3]:
        print(f"    - {r.get('default_code')}: {r.get('similarity_score', 0):.0%}")

print()

# Should accept valid code
print("Searching for '3M851-50-66' (should match):")
results = matcher.search("3M851-50-66", top_k=3)
if len(results) > 0:
    print(f"  [OK] Valid code matched - {len(results)} results")
    for r in results[:3]:
        print(f"    - {r.get('default_code')}: {r.get('similarity_score', 0):.0%} (confidence: {r.get('confidence', 0):.0%})")
else:
    print("  [FAIL] Valid code not matched")

print()
print()

# Test 4: Confidence scoring
print("[TEST 4] Confidence Scoring")
print("-"*100)

test_matches = [
    ("3M851-50-66", "EXACT", "Should be 100%"),
    ("3M851-50-66", "FUZZY", "Should be ~95%"),
    ("3M851-50-66", "TOKEN", "Should be ~90%"),
    ("3M851-50-66", "NAME", "Should be ~70%"),
]

for code, match_type, expected in test_matches:
    confidence = get_code_confidence(code, match_type)
    print(f"{match_type:8s}: {confidence:.0%} - {expected}")

print()
print("="*100)
print("VALIDATION FIX TEST COMPLETE")
print("="*100)
