"""
Test width extraction fix
"""
from orchestrator.mistral_agent import MistralAgent

extractor = MistralAgent()

# Test cases that previously extracted wrong widths
test_cases = [
    {
        'name': '3M Transfer-Klebeband 928-12-K 12mmx16.5',
        'expected_width': 12,
        'note': 'Should extract 12mm, NOT 928!'
    },
    {
        'name': 'SDS1923 Duro Seal Bobst Universal HS Cod 234',
        'expected_width': None,
        'note': 'Should NOT extract 234 (it\'s a code/quantity)'
    },
    {
        'name': '3M Klischee-Klebeband Cushion Mount L1520, 685 x 0,55 mm',
        'expected_width': 685,
        'note': 'Should extract 685mm correctly'
    },
    {
        'name': 'SpliceTape transparent, 3M9353R, Breite: 50mm, Länge: 33m',
        'expected_width': 50,
        'note': 'Should extract from "Breite: 50mm"'
    },
    {
        'name': '3M Transfer-Klebeband 904-12-G 12mm x 44',
        'expected_width': 12,
        'note': 'Should extract 12mm, NOT 904 or 44'
    }
]

print("=" * 80)
print("WIDTH EXTRACTION FIX TEST")
print("=" * 80)
print()

all_correct = True

for i, test in enumerate(test_cases, 1):
    attrs = extractor.extract_product_attributes(test['name'])
    extracted_width = attrs.get('dimensions', {}).get('width')

    is_correct = extracted_width == test['expected_width']
    status = "OK" if is_correct else "FAIL"

    if not is_correct:
        all_correct = False

    print(f"{i}. {test['name']}")
    print(f"   Expected: {test['expected_width']}mm")
    print(f"   Extracted: {extracted_width}mm")
    print(f"   Status: [{status}]")
    print(f"   Note: {test['note']}")
    print()

print("=" * 80)
if all_correct:
    print("SUCCESS: All width extractions correct!")
else:
    print("FAILURE: Some width extractions still wrong")
print("=" * 80)
