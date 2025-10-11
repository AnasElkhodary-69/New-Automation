"""
DSPy Signatures for RAG Email System

This module defines all DSPy signatures (input/output schemas) for:
1. Intent Classification
2. Entity Extraction
3. Product Matching

Signatures replace manual prompt engineering with declarative,
type-safe specifications of what the LM should do.
"""

import dspy
from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================================
# Intent Classification Signatures
# ============================================================

class ClassifyEmailIntent(dspy.Signature):
    """
    Classify the intent and urgency of a customer email.

    This signature defines what information we need to extract to
    understand what the customer wants and how urgently they need it.
    """

    # Inputs
    subject: str = dspy.InputField(
        desc="Email subject line"
    )
    body: str = dspy.InputField(
        desc="Email body text including any extracted attachment content"
    )

    # Outputs
    intent_type: str = dspy.OutputField(
        desc="Primary intent: order_inquiry, product_inquiry, complaint, payment_inquiry, general, support_request"
    )
    sub_type: str = dspy.OutputField(
        desc="Specific sub-category of the intent (e.g., new_order, order_confirmation, pricing_request)"
    )
    confidence: float = dspy.OutputField(
        desc="Confidence score from 0.0 to 1.0 indicating how certain the classification is"
    )
    urgency: str = dspy.OutputField(
        desc="Urgency level: high, medium, low"
    )
    reasoning: str = dspy.OutputField(
        desc="Brief explanation of why this classification was chosen"
    )


# ============================================================
# Entity Extraction Signatures
# ============================================================

class ExtractCustomerInfo(dspy.Signature):
    """
    Extract customer contact information from email text.

    This includes company name, contact person, email, phone, and address.

    IMPORTANT: Never extract "SDS", "SDS GmbH", "SDS Print Services" as the customer.
    This is our company, not the buyer. Look for the actual buyer/ordering company.
    """

    email_text: str = dspy.InputField(
        desc="Complete email content including body and attachments"
    )

    customer_name: str = dspy.OutputField(
        desc="Contact person's full name (empty string if not found)"
    )
    company: str = dspy.OutputField(
        desc="Company or organization name - NEVER 'SDS' or 'SDS GmbH' (empty string if not found)"
    )
    email: str = dspy.OutputField(
        desc="Email address (empty string if not found)"
    )
    phone: str = dspy.OutputField(
        desc="Phone number with country code if available (empty string if not found)"
    )
    address: str = dspy.OutputField(
        desc="Complete shipping or billing address (empty string if not found)"
    )


class ProductInfo(BaseModel):
    """
    Pydantic model for product information.

    DSPy can work with Pydantic models for structured nested data.
    """
    name: str = Field(description="Product name or description")
    code: str = Field(default="", description="Product code or SKU")
    quantity: int = Field(default=0, description="Quantity ordered")
    unit_price: float = Field(default=0.0, description="Unit price per item")
    specifications: str = Field(default="", description="Product specifications or notes")


class ExtractProducts(dspy.Signature):
    """
    Extract product details from order email.

    This extracts a list of products with their codes, quantities,
    and prices from the email content.

    CRITICAL: Prioritize product codes from these fields (in order):
    1. "Ihre Artikel-Nr." or "Ihre Art.Nr" (Your Article No.) - HIGHEST PRIORITY
    2. "Artikel-Nr." or "Art.-No." (Article No.)
    3. "Article No.", "Item No.", "Product Code", "SKU"
    4. Any alphanumeric code near the product description
    """

    email_text: str = dspy.InputField(
        desc="Complete email content including order details from attachments"
    )

    # Note: DSPy 3.0 supports structured outputs including lists of objects
    products_json: str = dspy.OutputField(
        desc="""Extract ALL products with COMPLETE details from the order.

[CRITICAL] MULTI-LINE RULE:
================================================================================
**PRODUCT DETAILS OFTEN SPAN MULTIPLE LINES IN PDF TABLES**

When you see a product code/name, ALWAYS scan the NEXT LINE(s) for additional specs.

Example (Multi-line format):
```
RPR-123965 Cushion Mount Plus E1320 gelb
457x23 mm                            <-- THIS LINE IS PART OF THE SAME PRODUCT!
```
Extract: "Cushion Mount Plus E1320 Yellow 457x23 mm"

**Treat consecutive lines without a new product code as continuation of the previous product!**
================================================================================

EXTRACTION RULES:
1. Extract EVERYTHING visible: dimensions, colors, materials, model numbers, technical specs
2. Check next line ALWAYS: If next line has no product code, it's likely specifications
3. Translate to English: Convert German/other languages (gelb->Yellow, Grau->Gray)
4. Include dimensions in name: Put dimensions directly in the product name field
5. Prioritize "Ihre Artikel-Nr." over "Artikel-Nr." for product codes

Format: [{"code": "", "name": "", "quantity": 0, "unit_price": 0.0, "specifications": ""}]

The "name" field should contain the FULL product description with ALL details in ENGLISH."""
    )


class ExtractOrderInfo(dspy.Signature):
    """
    Extract order-level information from email.

    This includes order number, dates, delivery terms, payment terms, etc.
    """

    email_text: str = dspy.InputField(
        desc="Complete email content"
    )

    order_number: str = dspy.OutputField(
        desc="Purchase order or reference number (empty string if not found)"
    )
    order_date: str = dspy.OutputField(
        desc="Order date in YYYY-MM-DD format (empty string if not found)"
    )
    delivery_date: str = dspy.OutputField(
        desc="Requested or expected delivery date in YYYY-MM-DD format (empty string if not found)"
    )
    urgency: str = dspy.OutputField(
        desc="Order urgency or priority: high, medium, low, standard"
    )
    payment_terms: str = dspy.OutputField(
        desc="Payment terms and conditions (empty string if not found)"
    )
    shipping_terms: str = dspy.OutputField(
        desc="Shipping, delivery, or Incoterms (empty string if not found)"
    )
    notes: str = dspy.OutputField(
        desc="Any additional notes, special instructions, or important information"
    )


class ExtractOrderEntities(dspy.Signature):
    """
    Extract customer information, products, and order details from email.

    Extract only what is present in the email - do not make up or guess any information.
    """

    email_text: str = dspy.InputField(
        desc="Complete email body including all extracted attachment content (PDFs, images)"
    )

    # Customer info (as nested JSON for simplicity)
    customer_json: str = dspy.OutputField(
        desc="""Extract customer/buyer information from the email as JSON.

Rules:
- Extract the company that is BUYING/ORDERING the products
- **NEVER extract "SDS", "SDS GmbH", "SDS Print Services" as the customer - this is OUR company, not the buyer**
- If you see SDS in signatures/footers/headers, ignore it and find the ACTUAL buyer/customer
- Look for sender information, billing/delivery addresses, customer details in order header
- Extract EXACTLY what is written - do not invent names
- If no customer found, return empty strings

Format: {"name": "", "company": "", "email": "", "phone": "", "address": ""}"""
    )

    # Products (as JSON array)
    products_json: str = dspy.OutputField(
        desc="""Extract ALL products with COMPLETE details from the order.

[CRITICAL] MULTI-LINE RULE - READ CAREFULLY:
================================================================================
**PRODUCT DETAILS OFTEN SPAN MULTIPLE LINES IN PDF TABLES**

When you see a product code/name, ALWAYS scan the NEXT LINE(s) for additional specs:

Example 1 (Multi-line format):
```
9000841 Rakelmesser Edelstahl Gold 35x0,20
RPE Length 1335mm, 50 Stk. pro Box    <-- THIS LINE IS PART OF THE SAME PRODUCT!
```
Extract: "Doctor Blade Stainless Steel Gold 35x0.20 RPE Length 1335mm"

Example 2 (Multi-line format):
```
RPR-123965 Cushion Mount Plus E1320 gelb
457x23 mm                            <-- THIS LINE IS PART OF THE SAME PRODUCT!
```
Extract: "Cushion Mount Plus E1320 Yellow 457x23 mm"

Example 3 (Multi-line format):
```
9000826 DuroSeal W&H End Seals Miraflex
007 CR Grau                          <-- THIS LINE IS PART OF THE SAME PRODUCT!
```
Extract: "DuroSeal W&H End Seals Miraflex 007 CR Gray"

Example 4 (3-line product from real orders):
```
40000947 KL-Klebeband 640mmx23mx0,5mm
3M Cushion Mount Plus E1020
E1020, Weiß, 64mm x 23 m, 0.5 mm     <-- ALL 3 LINES = 1 PRODUCT!
```
Extract: Code="40000947", Name="3M Cushion Mount Plus E1020 White 640mm x 23m x 0.5mm"

Example 5 (Swiss format):
```
P1-18890 Schaumklebeband 3M L1720 grün
457 mm x 33 m / Dicke 0.55 mm
```
Extract: Code="P1-18890", Name="3M Foam Tape L1720 Green 457mm x 33m / Thickness 0.55mm"

Example 6 (Flxon multi-line format):
```
101964
Vendor code: [SDS115] 444-AK-CR-GRY
Seal Class: All Foam Seal
Thickness: 12 mm
Anilox Diameter: 220 mm
```
Extract: Code="101964", Name="Seal 444-AK-CR-GRY All Foam 12mm Thickness Anilox 220mm"

Example 7 (Code AFTER description - German format):
```
14 Rolle 3 M Cushion Mount 457mm x 23 m
Art.Nr.: E1520
Mat.-Nr. ppg > wf: 617625
Liefertermin: 08.10.2020 / KW 41 / 2020
```
Extract: Code="E1520", Name="3M Cushion Mount E1520 457mm x 23m", Quantity=14

Example 8 (Another code-after format):
```
2 Rolle 3 M Cushion Mount 600mm x 23m
Art.Nr.: E1820
Mat.-Nr. ppg > wf: 619378
```
Extract: Code="E1820", Name="3M Cushion Mount E1820 600mm x 23m", Quantity=2

**[CRITICAL]: Treat consecutive lines without a new product code as continuation of the previous product!**
**[IMPORTANT]: Product code can appear BEFORE or AFTER the description - check for "Art.Nr.:", "Artikel-Nr.:", "Part #"**
================================================================================

EXTRACTION RULES:
1. **Extract EVERYTHING visible**: dimensions, colors, materials, model numbers, technical specs
2. **Check next line ALWAYS**: If next line has no product code, it's likely specifications
3. **Translate to English**: Convert German/other languages to English (gelb->Yellow, Grau->Gray, Edelstahl->Stainless Steel)
4. **Include dimensions in name**: Put dimensions directly in the product name field
5. **Don't skip details**: Every specification helps identify the correct product

WHAT TO CAPTURE (Priority order):
1. **Product Code** (CRITICAL - database key)
   - Look for: "Art.Nr.", "Artikel-Nr.", "Part #", "Vendor code:", "Ihre Artikel-Nr."
   - Can appear BEFORE or AFTER product description
   - Examples: E1520, P1-18890, 9000841, 101964, 3M-E1520HW457

2. **Dimensions** (CRITICAL for matching)
   - Width x Length: "457mm x 23m", "600mm x 23m", "1372mm x 33m"
   - Width x Thickness: "35x0,20", "35x0.20" (comma OR dot separator)
   - Full: "640mmx23mx0,5mm" (width x length x thickness)
   - With labels: "Dicke 0.55mm" (Thickness), "Länge 1335mm" (Length)
   - Diameter: "Anilox Diameter: 220mm", "178mm"

3. **Color** (Required for product variants)
   - Translate German: gelb→Yellow, grün→Green, violett→Violet, Grau→Gray, weiß→White
   - Examples: Yellow, Blue, Gray, Beige, Orange, Black, Green, Violet

4. **Material** (When present)
   - Translate: Edelstahl→Stainless Steel, Schaumklebeband→Foam Tape
   - Examples: Stainless Steel, Gold, Carbon, All Foam, Duroseal

5. **Model/Series** (Product family)
   - Examples: E1320, E1520, E1820, L1720, L1520, DuroSeal, Miraflex, Cushion Mount Plus

6. **Technical specs and other details**
   - Machine types (W&H, Bobst, KBA, etc.)
   - Technical specs (RPE, B100, etc.)
   - Any other identifying information

Format: [{"code": "", "name": "", "quantity": 0, "unit_price": 0.0, "specifications": ""}]

The "name" field should contain the FULL product description with ALL details in ENGLISH."""
    )

    # Order info (as nested JSON)
    order_info_json: str = dspy.OutputField(
        desc="""JSON object with order details: {"order_number": "", "date": "", "delivery_date": "", "urgency": "", "payment_terms": "", "shipping_terms": "", "notes": ""}"""
    )


# ============================================================
# Product Matching Signatures
# ============================================================

class ConfirmAllProducts(dspy.Signature):
    """
    Select BEST matching product from database candidates for each customer request.

    Return the Odoo ID of the best match, or 0 for NO_MATCH.
    Compare carefully: colors, dimensions, materials, product lines, codes.
    """

    email_excerpt: str = dspy.InputField(
        desc="Email text with customer order"
    )
    products_with_candidates: str = dspy.InputField(
        desc="""JSON: requested products with database candidates (each has odoo_id from JSON DB):
        [
          {
            "requested": {"name": "...", "code": "..."},
            "candidates": [
              {"odoo_id": 123, "code": "...", "name": "..."},
              {"odoo_id": 456, "code": "...", "name": "..."}
            ]
          }
        ]"""
    )

    matches: str = dspy.OutputField(
        desc="""JSON - select ONE odoo_id per product:
        [
          {"requested": "...", "selected_odoo_id": 123, "confidence": 0.95, "reason": "..."}
        ]

        Use selected_odoo_id=0 for NO_MATCH"""
    )


class SemanticProductSearch(dspy.Signature):
    """
    Semantically search for products based on description.

    This signature generates search queries to find relevant products
    when exact code matching fails.
    """

    product_description: str = dspy.InputField(
        desc="Product name or description from customer email"
    )
    product_code: str = dspy.InputField(
        desc="Product code if available (may be empty or partial)"
    )

    search_terms: str = dspy.OutputField(
        desc="Comma-separated search terms to find this product in the database"
    )
    key_attributes: str = dspy.OutputField(
        desc="Key attributes to match: dimensions, material, brand, model, etc."
    )
    reasoning: str = dspy.OutputField(
        desc="Explanation of the search strategy"
    )


# ============================================================
# Validation Signatures
# ============================================================

class ValidateExtraction(dspy.Signature):
    """
    Validate that extracted information is complete and accurate.

    This signature helps check if we've extracted all required fields
    and if the extraction quality is sufficient.
    """

    original_email: str = dspy.InputField(
        desc="Original email text"
    )
    extracted_data: str = dspy.InputField(
        desc="JSON of extracted data"
    )

    is_valid: bool = dspy.OutputField(
        desc="True if extraction is complete and accurate, False otherwise"
    )
    missing_fields: str = dspy.OutputField(
        desc="Comma-separated list of important missing fields (empty if none)"
    )
    confidence: float = dspy.OutputField(
        desc="Overall confidence in the extraction quality (0.0 to 1.0)"
    )
    suggestions: str = dspy.OutputField(
        desc="Suggestions for improving extraction or handling missing data"
    )


# ============================================================
# Helper function to convert signatures to legacy format
# ============================================================

def dspy_result_to_legacy_format(result: dspy.Prediction, signature_type: str) -> dict:
    """
    Convert DSPy prediction results to legacy format for backward compatibility.

    Args:
        result: DSPy prediction result
        signature_type: Type of signature used ('intent', 'extraction', etc.)

    Returns:
        Dictionary in legacy format matching current system output
    """
    if signature_type == 'intent':
        return {
            'type': result.intent_type,
            'sub_type': result.sub_type,
            'confidence': float(result.confidence),
            'urgency': result.urgency,
            'reasoning': result.reasoning
        }

    elif signature_type == 'customer':
        return {
            'name': result.customer_name,
            'company': result.company,
            'email': result.email,
            'phone': result.phone,
            'address': result.address
        }

    # Add more conversions as needed
    return dict(result)
