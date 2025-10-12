"""
Add Training Example for SDS Customer Extraction Fix

This script adds a training example to teach the entity extractor:
- When email shows "Lieferadresse: SDS GmbH", that's the RECIPIENT (supplier), not the customer
- The actual customer is the SENDER (e.g., Schur Star Systems GmbH)
"""

import json
from pathlib import Path
from datetime import datetime

# The training example
training_example = {
    "training_id": f"train_sds_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    "created_at": datetime.now().isoformat(),
    "signature_type": "EntityExtractor",  # or "CompleteExtractor"
    "description": "Fix SDS being extracted as customer when it's actually the supplier/recipient",
    "training_data": {
        "input": {
            "email_subject": "524557410",
            "email_body": """From: Anja Wicknig <anw@schur.com>
Date: Wed, 9 Dec 2020 13:58:02 +0000
Subject: 524557410

This information is automatically generated from the ERP system.

Best regards,
Anja Wicknig
Schur Star Systems GmbH
Direct: +49 461 9975 231
Mail: anw@schur.com
Web: www.schur.com

=== ATTACHMENT: 526848-524557410.pdf ===

Schur Star Systems GmbH
Liebigstraße 7
D-24941 Flensburg

Lieferadresse
SDS GmbH
Karim Elouahabi
Bachtelstrasse 51
8810 Horgen
Switzerland

Bestellung 524557410                      Datum 09.12.20
Ihre Referenz Karim Elouahabi
Ihre Lieferantennummer bei uns 526848    Währung EUR
Kontaktperson Anja Wicknig ANW
Zahlungsbedingungen 30 Tage netto

Mat.-Nr.    Beschreibung                        Menge    Preis
RPR-123965  Cushion Mount Plus E1320 gelb       3 Stück  165,00 / Stück
            457x23 mm
"""
        },
        "correct_output": {
            "entities": {
                "customer_name": "Anja Wicknig",
                "company_name": "Schur Star Systems GmbH",  # ← CORRECT: This is the sender
                "email": "anw@schur.com",
                "phone": "+49 461 9975 231",
                "address": "Liebigstraße 7, D-24941 Flensburg",
                "product_names": ["Cushion Mount Plus E1320 gelb 457x23 mm"],
                "product_codes": ["RPR-123965"],
                "quantities": [3],
                "prices": [165.0],
                "order_number": "524557410",
                "order_date": "09.12.20",
                "delivery_date": "",
                "urgency": "medium",
                "payment_terms": "30 Tage netto",
                "shipping_terms": "",
                "notes": "Lieferadresse: SDS GmbH (this is the delivery address/supplier, NOT the customer)"
            }
        },
        "reasoning": """
The email shows:
- Sender: Schur Star Systems GmbH (Anja Wicknig) ← This is the CUSTOMER
- Lieferadresse (Delivery Address): SDS GmbH ← This is the SUPPLIER/RECIPIENT (NOT the customer!)

Common mistake: Extracting "SDS GmbH" as the customer because it appears prominently in the purchase order.
Correct approach: Extract the sender company (Schur Star Systems) from the email header/signature.

Key indicators:
1. Email from: anw@schur.com → Domain = Schur
2. Signature: "Schur Star Systems GmbH" with contact details
3. "Lieferadresse" (Delivery Address) shows SDS → This is where the order is being SENT TO, not FROM

Purchase orders are sent FROM customer TO supplier, so:
- Schur Star Systems = Customer (sender)
- SDS = Supplier (recipient)
"""
    },
    "used_in_training": False,
    "applied_to_model": False
}

def add_training_example():
    """Add the training example to training_examples.json"""

    training_file = Path('feedback/training_examples.json')

    # Load existing examples
    if training_file.exists():
        with open(training_file, 'r', encoding='utf-8') as f:
            examples = json.load(f)
    else:
        examples = []

    # Check if similar example already exists
    for ex in examples:
        if ex.get('description') == training_example['description']:
            print(f"[WARNING] Similar training example already exists: {ex['training_id']}")
            print("  Skipping addition.")
            return

    # Add new example
    examples.append(training_example)

    # Save back
    training_file.parent.mkdir(exist_ok=True)
    with open(training_file, 'w', encoding='utf-8') as f:
        json.dump(examples, f, indent=2, ensure_ascii=False)

    print(f"[OK] Added training example: {training_example['training_id']}")
    print(f"  Total training examples: {len(examples)}")
    print(f"\nTo train the model with this example:")
    print(f"  python train_from_feedback.py")
    print(f"\nWhat this teaches:")
    print(f"  - SDS GmbH in 'Lieferadresse' = Supplier (recipient), NOT customer")
    print(f"  - Actual customer = Schur Star Systems GmbH (sender from email header)")
    print(f"  - Extract customer from email 'From:' field and signature, not delivery address")

if __name__ == '__main__':
    add_training_example()
