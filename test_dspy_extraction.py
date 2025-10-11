"""
Test DSPy extraction on the PPG Wegoflex PDF content
"""
import sys
sys.path.append('.')

from orchestrator.dspy_config import setup_dspy
from orchestrator.dspy_entity_extractor import EntityExtractor
from dotenv import load_dotenv

load_dotenv()

# Setup DSPy
setup_dspy()

# The actual PDF text from the PPG Wegoflex order
pdf_text = """ppg > wegoflex GmbH > Am Bohldamm 9 > 14959 Trebbin
SDS GmbH
Herr Elouahabi
Kruppstrasse 122
D-60388 Frankfurt Bearbeiter : Silke Ebert
Telefon : +49 (0)33731/824-38
Fax : +49 (0)33731/824-638
E-Mail : silke.ebert@ppg-wegoflex.de
Fax: 044 520 53 24 Datum : 01.10.2020
Bestellung Nr. 24203104
Sehr geehrter Herr Elouahabi,
wir bestellen hiermit nachfolgend aufgeführte Positionen:
Pos. Menge ME Beschreibung E-Preis per ME Gesamt
1 14 Rolle 3 M Cushion Mount 457mm x 23 m 164 EUR / Rolle 2.296,00 EUR
Art.Nr.: E1520
Mat.-Nr. ppg > wf: 617625
Liefertermin: 08.10.2020 / KW 41 / 2020
2 14 Rolle 3 M Cushion Mount 600mm x 23m 220 EUR / Rolle 3.080,00 EUR
Art.Nr.: E1520
Mat.-Nr. ppg > wf: 617626
Liefertermin: 08.10.2020 / KW 41 / 2020
3 2 Rolle 3 M Cushion Mount 457mm x 23 m 184 EUR / Rolle 368,00 EUR
Art.Nr.: E1820
Mat.-Nr. ppg > wf: 619379
Liefertermin: 08.10.2020 / KW 41 / 2020
4 2 Rolle 3 M Cushion Mount 600mm x 23m 244 EUR / Rolle 488,00 EUR
Art.Nr.: E1820
Mat.-Nr. ppg > wf: 619378
Liefertermin: 08.10.2020 / KW 41 / 2020
Zahlungskonditionen : 30 Tage nach Rechnungsdatum netto
Lieferbedingungen : frei Haus, einschl. Verpackung und Versicherung
Lieferanschrift : ppg > wegoflex GmbH, Am Bohldamm 9, D-14959 Trebbin"""

email_body = f"""
Original Email Details:
------------------------
From: "Ebert, Silke" <Silke.Ebert@ppg-wegoflex.de>
Date: Thu, 1 Oct 2020 12:33:32 +0000
Subject: 24203104_4_20201001_142946.pdf

------------------------
Original Message:
------------------------
Sehr geehrte Damen und Herren,

anbei unsere Bestellung.

Mit freundlichen Grüßen

------------------------
PDF Content:
------------------------
{pdf_text}
"""

print("=" * 80)
print("TESTING DSPy EXTRACTION")
print("=" * 80)
print(f"Email length: {len(email_body)} chars")
print()

# Create extractor
extractor = EntityExtractor(use_chain_of_thought=True)

# Extract
print("Extracting with DSPy...")
result = extractor.extract_complete(email_body, subject="24203104_4_20201001_142946.pdf")

print()
print("=" * 80)
print("EXTRACTION RESULTS:")
print("=" * 80)
print(f"Intent: {result['intent']['type']} ({result['intent']['confidence']:.0%})")
print(f"Company: {result['entities'].get('company_name', 'N/A')}")
print(f"Contact: {result['entities'].get('customer_name', 'N/A')}")
print(f"Products extracted: {len(result['entities'].get('product_names', []))}")
print()

if result['entities'].get('product_names'):
    print("PRODUCTS:")
    print("-" * 80)
    for i, name in enumerate(result['entities']['product_names'], 1):
        code = result['entities']['product_codes'][i-1] if i-1 < len(result['entities']['product_codes']) else 'N/A'
        qty = result['entities']['quantities'][i-1] if i-1 < len(result['entities']['quantities']) else 0
        price = result['entities']['prices'][i-1] if i-1 < len(result['entities']['prices']) else 0

        print(f"{i}. {name}")
        print(f"   Code: {code} | Qty: {qty} | Price: €{price}")
        print()
else:
    print("❌ NO PRODUCTS EXTRACTED")
    print()
    print("Raw result:")
    print(result.get('raw_result', {}))
