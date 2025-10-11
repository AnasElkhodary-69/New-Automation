"""
Test email cleaner to see if it's removing PDF content
Uses the ACTUAL email body from the real test case
"""
from utils.email_cleaner import clean_email_content

# This is the ACTUAL email body from the real test case
full_email = """
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

Mit freundlichen Gren
Kind Regards

i. A. Silke Ebert
Leiterin Einkauf Flexibles / head of purchasing flexibles
________________________________
[cid:image001.png@01D697FF.D596E8E0]
ppg > wegoflex GmbH
Am Bohldamm 9
14959 Trebbin

T +49 (0) 33731 / 824 - 38
F +49 (0) 33731 / 824 - 638
E Silke.Ebert@ppg-wegoflex.de
I www.prepacgroup.de

Amtsgericht Potsdam, Reg.-Nr. HRB 12586
USt.IdNr. DE 150 11 84 19
Geschftsfhrung: Dipl.-Ing. Thomas Hake, Dipl.-Wirt. jur. Nilo Reichenbach
________________________________




=== ATTACHMENT: image001.png ===
> wegorlex
ppg



=== ATTACHMENT: 24203104_4_20201001_142946.pdf ===

--- Page 1 ---
ppg > wegoflex GmbH > Am Bohldamm 9 > 14959 Trebbin
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
Lieferanschrift : ppg > wegoflex GmbH, Am Bohldamm 9, D-14959 Trebbin
"""

print("=" * 80)
print("TESTING EMAIL CLEANER")
print("=" * 80)
print(f"Original length: {len(full_email)} chars")
print()
print("CHECKING PDF DETECTION:")
has_pdf = '=== ATTACHMENT:' in full_email and '.pdf ===' in full_email
print(f"  has_pdf_content = {has_pdf}")
print()

# Clean the email
cleaned = clean_email_content(full_email)

print("=" * 80)
print(f"Cleaned length: {len(cleaned)} chars")
print()

if len(cleaned) < len(full_email) * 0.5:
    print("❌ PDF CONTENT WAS REMOVED!")
    print()
    print("Cleaned email:")
    print(cleaned)
else:
    print("✅ PDF CONTENT PRESERVED")
    print()
    print("First 500 chars of cleaned email:")
    print(cleaned[:500])
    print()
    print("Last 500 chars of cleaned email:")
    print(cleaned[-500:])
