"""
Test attribute extraction for failing products
"""
from orchestrator.mistral_agent import MistralAgent

# Initialize extractor
extractor = MistralAgent()

# Test cases
test_cases = [
    {
        'code': 'L1520',
        'name': '3M Klischee-Klebeband Cushion Mount L1520, 685 x 0,55 mm, Rolle à 33m'
    },
    {
        'code': 'L1320',
        'name': '3M Klischee-Klebeband Cushion Mount L1320, 685 x 0,55 mm, Rolle à 33m'
    },
    {
        'code': 'SDS1923',
        'name': 'SDS1923 Duro Seal Bobst Universal HS Cod 234'
    },
    {
        'code': '3M94',
        'name': 'Primer-Stift, 3M94, Inhalt: ca. 0,66ml, HS-Code 35069190'
    }
]

print("=" * 80)
print("ATTRIBUTE EXTRACTION TEST")
print("=" * 80)
print()

for i, test in enumerate(test_cases, 1):
    print(f"{i}. Product: {test['code']}")
    print(f"   Name: {test['name']}")

    # Extract attributes
    attrs = extractor.extract_product_attributes(test['name'])

    print(f"   Attributes:")
    for key, value in attrs.items():
        if value:
            print(f"      {key}: {value}")
    print()

print("=" * 80)
