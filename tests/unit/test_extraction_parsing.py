"""
Test entity extraction JSON parsing with product_attributes
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestrator.mistral_agent import MistralAgent

def test_extraction():
    """Test extraction with a simple email"""
    agent = MistralAgent()

    # Simple test email with one product
    test_email = """
    Dear SDS Print,

    Please send me a quote for:
    - 3M Cushion Mount L1520, 685mm width, 0.55mm thick, 33m roll

    Quantity: 5 pieces
    Price: 150 EUR each

    Best regards,
    John Smith
    ABC Company GmbH
    Email: john@abc-company.de
    Phone: +49 89 1234567
    """

    print("=" * 80)
    print("TEST: Entity Extraction with product_attributes")
    print("=" * 80)
    print(f"\nTest Email:\n{test_email}\n")

    print("Calling Mistral API for entity extraction...")
    entities = agent.extract_entities(test_email)

    print("\n" + "=" * 80)
    print("EXTRACTED ENTITIES:")
    print("=" * 80)

    import json
    print(json.dumps(entities, indent=2, ensure_ascii=False))

    print("\n" + "=" * 80)
    print("VALIDATION:")
    print("=" * 80)

    # Check if extraction worked
    success = True

    if not entities.get('product_names'):
        print("X FAIL: No product names extracted")
        success = False
    else:
        print(f"OK Product names: {len(entities['product_names'])} extracted")
        for name in entities['product_names']:
            print(f"   - {name}")

    if not entities.get('product_codes'):
        print("X FAIL: No product codes extracted")
        success = False
    else:
        print(f"OK Product codes: {len(entities['product_codes'])} extracted")
        for code in entities['product_codes']:
            print(f"   - {code}")

    if 'product_attributes' in entities:
        print(f"OK Product attributes: {len(entities.get('product_attributes', []))} entries")
        for idx, attrs in enumerate(entities.get('product_attributes', [])):
            print(f"   Product {idx+1}:")
            print(f"      Brand: {attrs.get('brand')}")
            print(f"      Width: {attrs.get('width')}mm")
            print(f"      Thickness: {attrs.get('thickness')}mm")
    else:
        print("X WARNING: product_attributes field missing (will extract later)")

    if entities.get('company_name'):
        print(f"OK Company: {entities['company_name']}")
    else:
        print("X FAIL: No company name extracted")
        success = False

    if entities.get('customer_emails'):
        print(f"OK Emails: {entities['customer_emails']}")
    else:
        print("X FAIL: No email extracted")
        success = False

    print("\n" + "=" * 80)
    if success:
        print("TEST PASSED: All critical fields extracted")
    else:
        print("TEST FAILED: Some fields missing")
    print("=" * 80)

if __name__ == "__main__":
    test_extraction()
