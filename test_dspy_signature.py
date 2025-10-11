"""
Test the new generic DSPy signature
"""
import json
import logging
from orchestrator.dspy_entity_extractor import EntityExtractor
from orchestrator.dspy_config import setup_dspy

# Setup logging
logging.basicConfig(level=logging.INFO)

# Setup DSPy with Mistral
setup_dspy()

# Test email with multi-line product format (from Maag)
test_email = """
From: Maag GmbH
To: SDS GmbH

Bestellung Bestell-Nr.: BE25/002223
Datum: 8. Oktober 2025

Artikelnr. Bezeichnung Menge ME Preis/PE % Betrag

9000841 Rakelmesser Edelstahl Gold 35x0,20 100 Stück 8,69 / Stück 869,00
RPELänge 1335mm, 50 Stk. pro Box

9000826 DuroSeal W&H End Seals Miraflex SDS 200 Stück 5,00 / Stück 1.000,00
007 CR Grau

Total EUR ohne USt. 1.869,00
"""

print("Testing NEW Generic DSPy Signature")
print("=" * 80)
print("\nTest Email Content:")
print(test_email)
print("\n" + "=" * 80)
print("Extracting with DSPy...")
print("=" * 80)

# Create extractor
extractor = EntityExtractor(use_chain_of_thought=True)

# Extract
result = extractor.extract(test_email)

print("\n✅ EXTRACTION RESULT:")
print(json.dumps(result, indent=2, ensure_ascii=False))

print("\n" + "=" * 80)
print("VALIDATION:")
print("=" * 80)

product_names = result.get('product_names', [])
product_codes = result.get('product_codes', [])
quantities = result.get('quantities', [])
prices = result.get('prices', [])

print(f"\nTotal products extracted: {len(product_names)}")

for i in range(len(product_names)):
    print(f"\nProduct {i+1}:")
    print(f"  Code: {product_codes[i] if i < len(product_codes) else 'N/A'}")
    print(f"  Name: {product_names[i] if i < len(product_names) else 'N/A'}")
    print(f"  Quantity: {quantities[i] if i < len(quantities) else 'N/A'}")
    print(f"  Price: {prices[i] if i < len(prices) else 'N/A'}")

    # Check if multi-line details captured
    name = p.get('name', '').lower()
    if i == 1:
        has_rpe = 'rpe' in name
        has_1335 = '1335' in name
        print(f"  ✓ Has RPE: {has_rpe}")
        print(f"  ✓ Has 1335mm: {has_1335}")
        if has_rpe and has_1335:
            print("  ✅ Product 1 is COMPLETE!")
        else:
            print("  ❌ Product 1 is INCOMPLETE - missing multi-line details!")

    if i == 2:
        has_007 = '007' in name
        has_cr = 'cr' in name or 'gray' in name or 'grey' in name
        print(f"  ✓ Has 007: {has_007}")
        print(f"  ✓ Has CR/Gray: {has_cr}")
        if has_007 and has_cr:
            print("  ✅ Product 2 is COMPLETE!")
        else:
            print("  ❌ Product 2 is INCOMPLETE - missing multi-line details!")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
