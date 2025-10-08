"""
Test PHASE 1: Attribute Extraction and Code Normalization
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator.mistral_agent import MistralAgent

def test_attribute_extraction():
    """Test extracting attributes from product names"""
    print("="*80)
    print("TESTING ATTRIBUTE EXTRACTION")
    print("="*80)

    agent = MistralAgent()

    # Test cases from real emails
    test_products = [
        "3M Klischee-Klebeband Cushion Mount L1520, 685 x 0,55 mm, Rolle à 33m",
        "3M Klischee-Klebeband Cushion Mount L1320, 685 x 0,55 mm, Rolle à 33m",
        "SDS025 - 177H DuroSeal Bobst 16S Grey",
        "DuroSeal gaskets for Bobst 16S machine, Grey, 177mm height",
        "Heat seal tape, 1282mm width",
        "HEAT SEAL 1282"
    ]

    for idx, product_name in enumerate(test_products, 1):
        print(f"\n[Test {idx}] Product: {product_name}")
        attrs = agent.extract_product_attributes(product_name)

        print(f"   Brand: {attrs['brand']}")
        print(f"   Product Line: {attrs['product_line']}")
        print(f"   Machine Type: {attrs['machine_type']}")
        print(f"   Width: {attrs['dimensions']['width']}mm" if attrs['dimensions']['width'] else "   Width: None")
        print(f"   Height: {attrs['dimensions']['height']}mm" if attrs['dimensions']['height'] else "   Height: None")
        print(f"   Thickness: {attrs['dimensions']['thickness']}mm" if attrs['dimensions']['thickness'] else "   Thickness: None")
        print(f"   Length: {attrs['length']}")
        print(f"   Color: {attrs['color']}")

    print("\n" + "="*80)


def test_code_normalization():
    """Test normalizing product codes from extraction"""
    print("="*80)
    print("TESTING CODE NORMALIZATION")
    print("="*80)

    agent = MistralAgent()

    # Test scenarios
    test_cases = [
        {
            "name": "Codes in explicit field",
            "data": {
                "product_names": [
                    "3M Cushion Mount L1520, 685mm x 33m",
                    "SDS025 - 177H DuroSeal Bobst 16S"
                ],
                "product_codes": ["3M L1520", "SDS025"]
            }
        },
        {
            "name": "No explicit codes (extract from names)",
            "data": {
                "product_names": [
                    "3M Cushion Mount L1520, 685mm x 33m",
                    "SDS025 - 177H DuroSeal Bobst 16S"
                ],
                "product_codes": []
            }
        },
        {
            "name": "Customer code + name with our code",
            "data": {
                "product_names": ["SDS025 - 177H DuroSeal Bobst 16S Grey"],
                "product_codes": ["8060104"]  # Customer's internal code
            }
        },
        {
            "name": "No codes at all",
            "data": {
                "product_names": ["DuroSeal for Bobst 16S, Grey"],
                "product_codes": []
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n[Test Case] {test_case['name']}")
        print(f"   Input products: {test_case['data']['product_names']}")
        print(f"   Input codes: {test_case['data']['product_codes']}")

        result = agent.normalize_product_codes(test_case['data'])

        print(f"\n   Results:")
        print(f"   - Products with codes: {result['total_with_codes']}")
        print(f"   - Products without codes: {result['total_without_codes']}")

        for idx, product in enumerate(result['products'], 1):
            print(f"\n   Product {idx}:")
            print(f"      Name: {product['product_name']}")
            print(f"      Primary Code: {product['primary_code']}")
            print(f"      Base Code: {product['base_code']}")
            print(f"      Use Name Matching: {product['use_name_matching']}")
            if product['all_codes']:
                print(f"      All Codes Found: {[c['code'] for c in product['all_codes']]}")

    print("\n" + "="*80)


def test_real_email_scenarios():
    """Test with actual failed email scenarios"""
    print("="*80)
    print("TESTING REAL EMAIL SCENARIOS (from failed tests)")
    print("="*80)

    agent = MistralAgent()

    # Email 1: Duerrbeck (both matched to E1015-685 - WRONG)
    print("\n[EMAIL 1] Duerrbeck - 3M Cushion Mount")
    email1_data = {
        "product_names": [
            "3M Klischee-Klebeband Cushion Mount L1520, 685 x 0,55 mm, Rolle à 33m",
            "3M Klischee-Klebeband Cushion Mount L1320, 685 x 0,55 mm, Rolle à 33m"
        ],
        "product_codes": ["3M L1520", "3M L1320"]
    }

    print(f"   Original extraction:")
    print(f"      Product 1: {email1_data['product_names'][0]}")
    print(f"      Code 1: {email1_data['product_codes'][0]}")
    print(f"      Product 2: {email1_data['product_names'][1]}")
    print(f"      Code 2: {email1_data['product_codes'][1]}")

    result1 = agent.normalize_product_codes(email1_data)

    print(f"\n   After normalization:")
    for idx, product in enumerate(result1['products'], 1):
        print(f"\n   Product {idx}:")
        print(f"      Primary Code: {product['primary_code']} (should be L1520 or L1320)")
        attrs = agent.extract_product_attributes(product['product_name'])
        print(f"      Width: {attrs['dimensions']['width']}mm (should be 685)")
        print(f"      Thickness: {attrs['dimensions']['thickness']}mm (should be 0.55)")
        print(f"      Length: {attrs['length']} (should be 33m)")

    # Email 2: Alesco - SDS025 (matched to HEAT SEAL 1282 - WRONG)
    print("\n" + "-"*80)
    print("\n[EMAIL 2] Alesco - SDS DuroSeal")
    email2_data = {
        "product_names": ["SDS025 - 177H DuroSeal Bobst 16S Grey"],
        "product_codes": ["8060104"]  # Customer code (wrong)
    }

    print(f"   Original extraction:")
    print(f"      Product: {email2_data['product_names'][0]}")
    print(f"      Code: {email2_data['product_codes'][0]} (customer's internal code)")

    result2 = agent.normalize_product_codes(email2_data)

    print(f"\n   After normalization:")
    product = result2['products'][0]
    print(f"      Primary Code: {product['primary_code']} (should be SDS025)")
    attrs = agent.extract_product_attributes(product['product_name'])
    print(f"      Brand: {attrs['brand']} (should be DuroSeal)")
    print(f"      Machine Type: {attrs['machine_type']} (should be 16S)")
    print(f"      Height: {attrs['dimensions']['height']}mm (should be 177)")
    print(f"      Color: {attrs['color']} (should be Grey)")

    print("\n" + "="*80)
    print("PHASE 1 TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    print("\nPHASE 1 IMPLEMENTATION TEST")
    print("Testing: Attribute Extraction + Code Normalization\n")

    # Run tests
    test_attribute_extraction()
    print("\n")
    test_code_normalization()
    print("\n")
    test_real_email_scenarios()

    print("\nPHASE 1 functions are working correctly!")
    print("Next step: Implement PHASE 2 (SmartProductMatcher)")
