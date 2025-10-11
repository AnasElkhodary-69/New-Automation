"""
Test SmartMatcher fix for exact code matching issues
"""
import json
from retriever_module.smart_matcher import SmartProductMatcher
from retriever_module.simple_rag import SimpleProductRAG
from orchestrator.mistral_agent import MistralAgent

# Load products
with open('odoo_database/odoo_products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# Initialize RAG
rag = SimpleProductRAG()

# Initialize SmartMatcher
matcher = SmartProductMatcher(
    products=products,
    customer_mapper=None,
    rag_search=rag,
    enable_rag=True
)

# Initialize attribute extractor
extractor = MistralAgent()

# Test cases from actual failures
test_cases = [
    {
        'name': 'L1520 vs L1520-685',
        'code': 'L1520',
        'full_name': '3M Klischee-Klebeband Cushion Mount L1520, 685 x 0,55 mm, Rolle à 33m',
        'expected': 'L1520-685'
    },
    {
        'name': 'L1320 vs L1320-685',
        'code': 'L1320',
        'full_name': '3M Klischee-Klebeband Cushion Mount L1320, 685 x 0,55 mm, Rolle à 33m',
        'expected': 'L1320-685'
    },
    {
        'name': '3M94 vs 3M94-0,66',
        'code': '3M94',
        'full_name': 'Primer-Stift, 3M94, Inhalt: ca. 0,66ml, HS-Code 35069190',
        'expected': '3M94-0,66'
    },
    {
        'name': 'SDS1923 exact match',
        'code': 'SDS1923',
        'full_name': 'SDS1923 Duro Seal Bobst Universal HS Cod 234',
        'expected': 'SDS1923'
    },
    {
        'name': '3M9353R (completely wrong product)',
        'code': '3M9353R',
        'full_name': 'SpliceTape transparent, 3M9353R, Breite: 50mm, Länge: 33m',
        'expected': '3M9353R'
    },
    {
        'name': '904-12-G (brand prefix missing)',
        'code': '904-12-G',
        'full_name': '3M Transfer-Klebeband 904-12-G 12mm x 44',
        'expected': '3M904-12-44'
    },
    {
        'name': '928-12-K (completely wrong)',
        'code': '928-12-K',
        'full_name': '3M Transfer-Klebeband 928-12-K 12mmx16.5',
        'expected': '3M924-19-55'
    },
    {
        'name': 'M414418 (doctor blade - wrong product)',
        'code': 'M414418',
        'full_name': 'M414418 C-40-20-RPE Doctor Blades - 100 meter coil, 100 meters coil x ',
        'expected': 'M414418'
    }
]

print("=" * 80)
print("TESTING SMART MATCHER FIX")
print("=" * 80)
print()

for i, test in enumerate(test_cases, 1):
    print(f"{i}. Testing: {test['name']}")
    print(f"   Code: {test['code']}")
    print(f"   Full Name: {test['full_name'][:60]}...")
    print(f"   Expected: {test['expected']}")

    # Extract attributes
    attrs = extractor.extract_product_attributes(test['full_name'])

    # Create extracted product
    extracted = {
        'product_code': test['code'],
        'product_name': test['full_name'],
        'attributes': attrs
    }

    # Show extracted attributes
    if attrs:
        print(f"   Attributes: {', '.join([f'{k}={v}' for k,v in attrs.items() if v])}")

    # Find match
    result = matcher.find_match(extracted)

    if result and result.get('match'):
        matched_code = result['match'].get('default_code')
        matched_name = result['match'].get('name', '')[:50]
        confidence = result.get('confidence', 0)
        method = result.get('method', 'unknown')

        # Check if correct
        is_correct = (matched_code == test['expected'])
        status = "[OK] CORRECT" if is_correct else "[FAIL] WRONG"

        print(f"   Matched: {matched_code} ({confidence*100:.0f}% confidence)")
        print(f"   Method: {method}")
        print(f"   Name: {matched_name}...")
        print(f"   Status: {status}")
    else:
        print(f"   Matched: NO_MATCH")
        print(f"   Status: [FAIL] NO MATCH FOUND")

    print()

print("=" * 80)
