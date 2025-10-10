"""
Product Code Validator
Validates if extracted strings are valid product codes or generic terms
"""

import re
import logging

logger = logging.getLogger(__name__)

# Generic terms that should NOT be treated as product codes
GENERIC_TERMS = {
    # German terms
    'klebeband', 'tape', 'adhesive', 'kleber',
    'rakel', 'rakelmesser', 'doctor blade', 'squeegee',
    'dichtung', 'seal', 'gasket', 'dichtungen',
    'messer', 'blade', 'knife', 'blades',
    'folie', 'film', 'foil',
    'reiniger', 'cleaner', 'cleaning',
    'anilox',
    'roll', 'rolle', 'cylinder', 'zylinder',
    'plate', 'platte',
    # English terms
    'product', 'produkt', 'item', 'artikel',
    'order', 'bestellung',
    'inquiry', 'anfrage',
    'quote', 'angebot',
}

# Known brand/product prefixes that override generic term filtering
VALID_PREFIXES = {
    'sds',      # SDS Anilox Cleaner, etc.
    '3m',       # 3M products
    'rpr-',     # RPR codes
    'l1020',    # L1020 series
    'e1320',    # E1320 series
    'e1520',    # E1520 series
}

# Known brand names that indicate valid product codes
BRAND_NAMES = {
    'inoxswiss',    # InoxSwiss Doctor Blades
    'longlife',     # Longlife Doctor Blades
    'cushion mount', # 3M Cushion Mount
    'duroseal',     # DuroSeal products
    'miraflex',     # Miraflex products
}

def is_valid_product_code(code: str) -> tuple[bool, str]:
    """
    Validate if string is a valid product code

    Returns:
        (is_valid, reason)
    """

    if not code or not isinstance(code, str):
        return False, "Empty or invalid type"

    code_clean = code.strip()

    # Check minimum length
    if len(code_clean) < 3:
        return False, f"Too short ({len(code_clean)} chars)"

    code_lower = code_clean.lower()

    # Check if code starts with a known valid prefix (overrides generic term filtering)
    has_valid_prefix = any(code_lower.startswith(prefix) for prefix in VALID_PREFIXES)

    if has_valid_prefix:
        return True, f"Valid brand prefix detected"

    # Check if code contains a known brand name (overrides generic term filtering)
    has_brand_name = any(brand in code_lower for brand in BRAND_NAMES)

    if has_brand_name:
        return True, f"Valid brand name detected"

    # Check against generic terms (exact match)
    if code_lower in GENERIC_TERMS:
        return False, f"Generic term: '{code_clean}'"

    # Check if it's ONLY a generic term (no numbers and no brand)
    for term in GENERIC_TERMS:
        if term in code_lower:
            # If it contains a generic term, it must also have numbers or brand to be valid
            has_number = any(c.isdigit() for c in code_clean)
            if not has_number and not has_brand_name:
                return False, f"Generic term without code: '{code_clean}' (contains '{term}')"

    # Valid product codes should have both letters and numbers
    has_letter = any(c.isalpha() for c in code_clean)
    has_number = any(c.isdigit() for c in code_clean)

    # Special case: All-uppercase letter codes (likely product acronyms like RPE, OPP, SDS)
    if has_letter and not has_number and len(code_clean) >= 3:
        # Check if it's all uppercase letters (product acronym)
        alpha_only = ''.join(c for c in code_clean if c.isalpha())
        if alpha_only.isupper() and len(alpha_only) >= 3:
            return True, f"Uppercase acronym (3+ letters)"

    if not (has_letter and has_number):
        # Exception: could be all numbers (like "1951")
        if has_number and len(code_clean) >= 4:
            return True, "Numeric code (4+ digits)"
        return False, f"Missing alphanumeric pattern (letters: {has_letter}, numbers: {has_number})"

    # Additional validation: check for reasonable patterns
    # Valid: 3M851-50-66, SDS1951, L1020
    # Invalid: a, ab, 12

    alphanumeric_count = sum(1 for c in code_clean if c.isalnum())
    if alphanumeric_count < 3:
        return False, f"Too few alphanumeric chars ({alphanumeric_count})"

    return True, "Valid product code"

def validate_product_codes(products: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Validate a list of product dictionaries

    Args:
        products: List of product dicts with 'code' key

    Returns:
        (valid_products, invalid_products)
    """

    valid = []
    invalid = []

    for product in products:
        code = product.get('code', '')
        is_valid, reason = is_valid_product_code(code)

        if is_valid:
            valid.append(product)
        else:
            logger.warning(f"Rejected product code: '{code}' - {reason}")
            product_with_reason = product.copy()
            product_with_reason['rejection_reason'] = reason
            invalid.append(product_with_reason)

    logger.info(f"Product validation: {len(valid)} valid, {len(invalid)} rejected")

    return valid, invalid

def get_code_confidence(code: str, match_type: str = "unknown") -> float:
    """
    Calculate confidence score based on code validity and match type

    Args:
        code: Product code
        match_type: Type of match (EXACT, FUZZY, TOKEN, NAME)

    Returns:
        Confidence score (0.0-1.0)
    """

    is_valid, reason = is_valid_product_code(code)

    # Base confidence from validation
    if not is_valid:
        base_confidence = 0.3  # Low confidence for invalid codes
    else:
        base_confidence = 0.8  # Good confidence for valid codes

    # Adjust based on match type
    match_multipliers = {
        "EXACT": 1.0,      # 100% for exact code match
        "FUZZY": 0.95,     # 95% for fuzzy match
        "TOKEN": 0.90,     # 90% for token match
        "NAME": 0.70,      # 70% for name-only match
        "unknown": 0.80    # 80% default
    }

    multiplier = match_multipliers.get(match_type, 0.80)
    confidence = base_confidence * multiplier

    return min(confidence, 1.0)  # Cap at 1.0

# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_codes = [
        # Valid codes
        ("3M851-50-66", True),
        ("SDS1951", True),
        ("L1020-685-33", True),
        ("1234", True),  # Numeric (4+ digits)

        # Invalid codes
        ("Klebeband", False),
        ("tape", False),
        ("Rakel", False),
        ("12", False),  # Too short
        ("ab", False),  # Too short
        ("", False),  # Empty

        # Edge cases
        ("Klebeband 3M", True),  # Has number
        ("3M Klebeband", True),  # Has number
        ("Dichtung", False),  # Generic only
    ]

    print("="*80)
    print("PRODUCT CODE VALIDATION TESTS")
    print("="*80)
    print()

    for code, expected in test_codes:
        is_valid, reason = is_valid_product_code(code)
        status = "✓" if is_valid == expected else "✗"
        print(f"{status} '{code}': {is_valid} ({reason})")

    print()
    print("="*80)
