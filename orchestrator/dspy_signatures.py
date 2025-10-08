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
    """

    email_text: str = dspy.InputField(
        desc="Complete email content including body and attachments"
    )

    customer_name: str = dspy.OutputField(
        desc="Contact person's full name (empty string if not found)"
    )
    company: str = dspy.OutputField(
        desc="Company or organization name (empty string if not found)"
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

    For German invoices, look for structured tables with:
    - Pos. (Position number)
    - Artikel-Nr. (Customer's internal article number)
    - Ihre Artikel-Nr. (Supplier's article number - USE THIS!)
    - Beschreibung (Description - use only if no codes found)
    - Bestellmenge (Order quantity)
    - Preis/PE (Unit price)
    """

    email_text: str = dspy.InputField(
        desc="Complete email content including order details from attachments"
    )

    # Note: DSPy 3.0 supports structured outputs including lists of objects
    products_json: str = dspy.OutputField(
        desc="""JSON array of products. For each product, extract in this priority order:

1. "code": Extract from "Ihre Artikel-Nr." (Your Article No.) FIRST. If not found, use "Artikel-Nr." Examples: "3M L1020 685 33m", "SDS1951", "L1020-685"
2. "name": Full product name with specifications. Examples: "3M Cushion Mount Plus L1020 685mm", "Duro Seal Bobst"
3. "quantity": Integer quantity ordered
4. "unit_price": Float price per unit in EUR
5. "specifications": Additional specs like dimensions, color, material

CRITICAL RULES:
- ALWAYS prioritize "Ihre Artikel-Nr." over "Beschreibung" (description)
- Extract the FULL code including numbers and dimensions (e.g., "3M L1020 685 33m", not just "PLATTENKLEBEBAND")
- For 3M products, include width/length (e.g., "L1020 685 33m")
- If multiple codes exist for one product, prefer the supplier's code ("Ihre Artikel-Nr.")

Example: [{"name": "3M Cushion Mount Plus L1020 685mm", "code": "L1020-685-33", "quantity": 12, "unit_price": 356.00, "specifications": "33m length"}]"""
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
    Complete order entity extraction in a single pass.

    This is a comprehensive signature that extracts everything:
    - Customer information
    - Product list
    - Order details

    Used for end-to-end extraction with a single LM call.

    CRITICAL CUSTOMER IDENTIFICATION RULES:
    1. **SDS GmbH / SDS-Print / SDS Print Services** is the SELLER/RECIPIENT (that's us!) - **DO NOT extract as customer**
    2. If email is forwarded internally by SDS employees (e.g., k.el@sds-print.com, @sds-print.com), find the ORIGINAL customer
    3. Look for the BUYER/ORDERING COMPANY in fields like:
       - "Von:" (From:) in forwarded emails
       - "Lieferanschrift" (Delivery address)
       - "Rechnungsanschrift" (Billing address)
       - "Kunde" (Customer)
       - "Besteller" (Orderer)
    4. **IGNORE** any mention of SDS as recipient/seller - find the actual ordering customer
    5. If email is from customer directly, extract that company. If forwarded by SDS, extract the original sender's company

    CRITICAL PRODUCT EXTRACTION RULES:
    1. For German invoices, prioritize "Ihre Artikel-Nr." (Your Article No.) - this is the SUPPLIER's product code
    2. Extract FULL product codes with dimensions (e.g., "3M L1020 685 33m", "SDS1951", "L1020-685-33")
    3. DO NOT extract only generic descriptions like "PLATTENKLEBEBAND" - always get the specific code
    4. Look for structured tables with: Pos., Artikel-Nr., Ihre Artikel-Nr., Beschreibung, Bestellmenge, Preis/PE
    5. For 3M products, include width and length in the code (e.g., "L1020 685 33m" not just "L1020")
    """

    email_text: str = dspy.InputField(
        desc="Complete email body including all extracted attachment content (PDFs, images)"
    )

    # Customer info (as nested JSON for simplicity)
    customer_json: str = dspy.OutputField(
        desc="""JSON object with customer info (THE BUYER/ORDERING COMPANY, NOT SDS):

IMPORTANT: Extract the company that is ORDERING/BUYING products, NOT the seller/recipient.

- If email mentions "SDS GmbH" as recipient/seller, IGNORE IT and find the actual customer
- Look for: "Von:" (From), "Lieferanschrift" (delivery address), "Kunde" (customer), "Besteller" (orderer)
- For forwarded emails from SDS employees, extract the ORIGINAL sender's company

Format: {"name": "contact person name", "company": "CUSTOMER company name (NOT SDS)", "email": "customer email", "phone": "customer phone", "address": "customer address"}

DO NOT return SDS GmbH, SDS-Print, or SDS Print Services as the company - these are the seller."""
    )

    # Products (as JSON array)
    products_json: str = dspy.OutputField(
        desc="""JSON array of products. Extract each with:

1. "code": Product code - PRIORITY ORDER:
   a) "Ihre Artikel-Nr." (Your Article No.) - HIGHEST PRIORITY (supplier's code)
   b) "Artikel-Nr." or "Art.-No." (Article No.)
   c) Any product code near the item

   Examples: "3M L1020 685 33m", "SDS1951", "L1020-685-33", "KB-WK-MW-B3"

2. "name": Full product name with specifications
   Examples: "3M Cushion Mount Plus L1020 685mm", "Duro Seal Bobst", "PLATTENKLEBEBAND"

3. "quantity": Integer quantity ordered (from "Bestellmenge" or quantity field)

4. "unit_price": Float unit price in EUR (from "Preis/PE" or price field)

5. "specifications": Additional specs (dimensions, color, material, notes)

CRITICAL VALIDATION RULES:
- ONLY extract if you find a SPECIFIC product code (alphanumeric with letters AND numbers)
- DO NOT extract generic terms like:
  * "Klebeband" (adhesive tape)
  * "Rakel" (squeegee)
  * "Dichtung" (seal)
  * "Messer" (blade)
  * "Folie" (film)
  * "Anilox"
  * Any generic product category without a specific code
- If no specific code found, return empty array []
- ALWAYS extract the specific product code from "Ihre Artikel-Nr." field if present
- DO NOT use generic descriptions as codes

VALID codes: "3M851-50-66", "SDS1951", "L1020-685-33" (have letters AND numbers)
INVALID codes: "Klebeband", "tape", "adhesive", "Rakel" (generic terms only)

Format: [{"name": "3M Cushion Mount Plus", "code": "3M L1020 685 33m", "quantity": 12, "unit_price": 356.00, "specifications": "685mm x 33m"}]"""
    )

    # Order info (as nested JSON)
    order_info_json: str = dspy.OutputField(
        desc="""JSON object with order details: {"order_number": "", "date": "", "delivery_date": "", "urgency": "", "payment_terms": "", "shipping_terms": "", "notes": ""}"""
    )


# ============================================================
# Product Matching Signatures
# ============================================================

class MatchProductToDatabase(dspy.Signature):
    """
    Match an extracted product description to database products.

    This signature helps the LM reason about which database product
    best matches an extracted product from the email.
    """

    extracted_product: str = dspy.InputField(
        desc="Product name/description extracted from email"
    )
    extracted_code: str = dspy.InputField(
        desc="Product code extracted from email (may be empty)"
    )
    candidate_products: str = dspy.InputField(
        desc="JSON array of candidate products from database with their codes and names"
    )

    best_match_code: str = dspy.OutputField(
        desc="Product code of the best matching candidate (empty if no good match)"
    )
    match_confidence: float = dspy.OutputField(
        desc="Confidence in the match from 0.0 to 1.0"
    )
    reasoning: str = dspy.OutputField(
        desc="Explanation of why this product was selected as the best match"
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
