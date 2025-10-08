"""
Enhanced extraction with proper product-attribute alignment
"""

import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def parse_structured_extraction(response_text: str) -> Dict:
    """
    Parse structured extraction response with product objects

    Args:
        response_text: Mistral response with structured JSON

    Returns:
        Parsed entities in both new and legacy format
    """
    import re

    # Remove markdown blocks
    cleaned = response_text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*\n', '', cleaned)
        cleaned = re.sub(r'\n```\s*$', '', cleaned)

    try:
        # Parse structured response
        data = json.loads(cleaned)

        # Convert to legacy format for compatibility
        entities = {
            # Customer info
            'customer_name': data.get('customer_info', {}).get('name', ''),
            'company_name': data.get('customer_info', {}).get('company', ''),
            'customer_emails': [data.get('customer_info', {}).get('email', '')] if data.get('customer_info', {}).get('email') else [],
            'phone_numbers': [data.get('customer_info', {}).get('phone', '')] if data.get('customer_info', {}).get('phone') else [],
            'addresses': [data.get('customer_info', {}).get('address', '')] if data.get('customer_info', {}).get('address') else [],

            # Order info
            'order_numbers': [data.get('order_info', {}).get('order_number', '')] if data.get('order_info', {}).get('order_number') else [],
            'dates': [data.get('order_info', {}).get('date', '')] if data.get('order_info', {}).get('date') else [],
            'urgency_level': data.get('order_info', {}).get('urgency', 'medium'),

            # Products - maintain alignment!
            'product_names': [],
            'product_codes': [],
            'product_quantities': [],
            'product_prices': [],

            # Store structured products for better matching
            'products_structured': data.get('products', [])
        }

        # Extract aligned arrays from product objects
        for product in data.get('products', []):
            entities['product_names'].append(product.get('name', ''))
            entities['product_codes'].append(product.get('code', ''))
            entities['product_quantities'].append(product.get('quantity', 1))
            entities['product_prices'].append(product.get('unit_price', 0))

        return entities

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse structured extraction: {e}")
        # Return empty structure
        return {
            'product_names': [],
            'product_codes': [],
            'product_quantities': [],
            'product_prices': [],
            'products_structured': []
        }


def fix_product_alignment(entities: Dict) -> Dict:
    """
    Fix misaligned product arrays using smart matching

    Args:
        entities: Extracted entities with potentially misaligned arrays

    Returns:
        Fixed entities with proper alignment
    """
    product_names = entities.get('product_names', [])
    product_codes = entities.get('product_codes', [])
    product_quantities = entities.get('product_quantities', [])
    product_prices = entities.get('product_prices', [])

    # If we have structured products, use those
    if entities.get('products_structured'):
        return entities

    # Otherwise, try to fix alignment
    aligned_products = []

    for i, name in enumerate(product_names):
        product = {
            'name': name,
            'code': '',
            'quantity': 1,
            'unit_price': 0
        }

        # Try to find matching code
        # Look for code in the product name itself
        import re
        code_patterns = [
            r'\b(SDS\d+[A-Z]?)\b',
            r'\b(L\d{4})\b',
            r'\b(E\d{4})\b',
            r'\b(\d{3,4}-\d{3})\b',
            r'\b(3M\s+\w+)\b'
        ]

        for pattern in code_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                product['code'] = match.group(1)
                break

        # If no code in name, try to use array if index exists
        if not product['code'] and i < len(product_codes):
            product['code'] = product_codes[i]

        # Add quantity if available
        if i < len(product_quantities):
            product['quantity'] = product_quantities[i]

        # Add price if available
        if i < len(product_prices):
            product['unit_price'] = product_prices[i]

        aligned_products.append(product)

    entities['products_structured'] = aligned_products
    return entities


def validate_extraction(entities: Dict) -> Dict:
    """
    Validate and report extraction quality

    Args:
        entities: Extracted entities

    Returns:
        Validation report
    """
    report = {
        'valid': True,
        'issues': [],
        'stats': {}
    }

    # Check product extraction
    products = entities.get('products_structured', [])
    if not products:
        products = [{'name': n} for n in entities.get('product_names', [])]

    report['stats']['total_products'] = len(products)
    report['stats']['products_with_codes'] = sum(1 for p in products if p.get('code'))
    report['stats']['products_with_quantities'] = sum(1 for p in products if p.get('quantity', 1) != 1)
    report['stats']['products_with_prices'] = sum(1 for p in products if p.get('unit_price', 0) > 0)

    # Check for issues
    if products and report['stats']['products_with_codes'] == 0:
        report['issues'].append("No product codes extracted")

    if products and report['stats']['products_with_quantities'] == 0:
        report['issues'].append("No quantities extracted")

    if len(report['issues']) > 0:
        report['valid'] = False

    return report


# Integration function for processor.py
def enhanced_extract_entities(mistral_agent, email_text: str) -> Dict:
    """
    Enhanced entity extraction with structured products

    Args:
        mistral_agent: MistralAgent instance
        email_text: Email body text

    Returns:
        Structured entities with aligned products
    """
    # First, try with new structured prompt
    import os
    from pathlib import Path

    prompt_path = Path("prompts/extraction_prompt_v2.txt")
    if prompt_path.exists():
        with open(prompt_path, 'r', encoding='utf-8') as f:
            structured_prompt = f.read()

        # Temporarily replace prompt
        old_prompt = mistral_agent.prompts.get('extraction')
        mistral_agent.prompts['extraction'] = structured_prompt

        # Extract with structured format
        entities = mistral_agent.extract_entities(email_text)

        # Restore old prompt
        mistral_agent.prompts['extraction'] = old_prompt

        # Fix alignment if needed
        entities = fix_product_alignment(entities)

        # Validate
        validation = validate_extraction(entities)
        if not validation['valid']:
            logger.warning(f"Extraction issues: {validation['issues']}")

        return entities

    else:
        # Fallback to original extraction
        entities = mistral_agent.extract_entities(email_text)
        return fix_product_alignment(entities)