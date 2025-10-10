"""
Fix Corrupted Products in Database

Fixes products with empty default_code where the code is embedded
in brackets in the name field like: "[CODE] Product Name"

This corrupted data was causing all products to match to C-40-20-RPE-L1335
"""

import json
import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_corrupted_products():
    """Fix products with codes in brackets in name field"""

    products_file = Path("odoo_database/odoo_products.json")

    # Load products
    logger.info(f"Loading products from {products_file}...")
    with open(products_file, 'r', encoding='utf-8') as f:
        products = json.load(f)

    logger.info(f"Total products: {len(products)}")

    # Find corrupted products (empty default_code, code in brackets in name)
    pattern = r'^\[([^\]]+)\]\s*(.+)$'
    fixed_count = 0

    for product in products:
        default_code = product.get('default_code', '')
        name = product.get('name', '')

        # Check if default_code is empty and name has brackets
        if default_code == '' and '[' in name:
            match = re.match(pattern, name)
            if match:
                # Extract code from brackets
                code = match.group(1)
                clean_name = match.group(2).strip()

                logger.info(f"\nFixing product ID {product.get('id')}:")
                logger.info(f"  OLD: default_code='{default_code}'")
                logger.info(f"       name='{name}'")

                # Fix the product
                product['default_code'] = code
                product['name'] = clean_name

                logger.info(f"  NEW: default_code='{code}'")
                logger.info(f"       name='{clean_name}'")

                fixed_count += 1

    if fixed_count > 0:
        # Create backup
        backup_file = products_file.with_suffix('.json.backup')
        logger.info(f"\nCreating backup at {backup_file}...")
        with open(backup_file, 'w', encoding='utf-8') as f:
            # Re-load original to backup
            with open(products_file, 'r', encoding='utf-8') as orig:
                f.write(orig.read())

        # Save fixed products
        logger.info(f"Saving fixed products to {products_file}...")
        with open(products_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)

        logger.info(f"\n✓ Fixed {fixed_count} corrupted products!")
        logger.info(f"✓ Backup saved to {backup_file}")

        # Clear BERT cache so embeddings are recomputed
        logger.info("\n⚠ IMPORTANT: BERT embeddings cache needs to be cleared!")
        logger.info("   Delete .bert_cache/ directory to force recomputation of embeddings")
    else:
        logger.info("\nNo corrupted products found.")

    return fixed_count

if __name__ == "__main__":
    print("="*80)
    print("FIX CORRUPTED PRODUCTS")
    print("="*80)
    print()

    fixed = fix_corrupted_products()

    print()
    print("="*80)
    print(f"DONE - Fixed {fixed} products")
    print("="*80)
