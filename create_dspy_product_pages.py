import json
import os
import re
from collections import defaultdict

# Read the Odoo products JSON
with open('odoo_database/odoo_products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

print(f"Total products loaded: {len(products)}")

# Function to extract product base name and company
def extract_product_family(product_name):
    """
    Extract the product family/base name from product name
    Examples:
    - "3M Cushion E1720 1000mm x 23m" -> "3M Cushion"
    - "Duro Seal W&H Miraflex 444-367BL-ORG-SX-BLU" -> "Duro Seal Miraflex"
    - "Novoflex CR-GRY" -> "Novoflex"
    """
    # Remove common dimension patterns
    name = re.sub(r'\d+mm\s*x\s*\d+m?', '', product_name)
    name = re.sub(r'\d+m\s*x\s*\d+mm?', '', product_name)
    name = re.sub(r'\d+"\s*x\s*\d+"', '', product_name)

    # Remove product codes (patterns like E1720, 444-367BL, etc.)
    name = re.sub(r'\b[A-Z]\d{4}\b', '', name)
    name = re.sub(r'\b\d{3}-\d{3}[A-Z]{2}-[A-Z]{3}-[A-Z]{2}-[A-Z]{3}\b', '', name)
    name = re.sub(r'\b[A-Z]{2}-[A-Z]{3}\b', '', name)

    # Clean up extra spaces
    name = ' '.join(name.split())

    return name.strip()

# Function to extract dimensions
def extract_dimensions(product_name, description):
    """Extract dimensions from product name or description"""
    dimensions = []

    text = f"{product_name} {description or ''}"

    # Pattern: 1000mm x 23m, 10m x 20mm, etc.
    dim_patterns = [
        r'(\d+(?:\.\d+)?mm?\s*x\s*\d+(?:\.\d+)?m)',
        r'(\d+(?:\.\d+)?m\s*x\s*\d+(?:\.\d+)?mm?)',
        r'(\d+(?:\.\d+)?"\s*x\s*\d+(?:\.\d+)?")',
        r'(\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?)',
    ]

    for pattern in dim_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dimensions.extend(matches)

    return list(set(dimensions))

# Function to extract colors
def extract_colors(product_name, description):
    """Extract colors from product name or description"""
    colors = []
    text = f"{product_name} {description or ''}".lower()

    # Common color patterns
    color_keywords = ['black', 'white', 'blue', 'red', 'green', 'yellow', 'orange',
                     'grey', 'gray', 'purple', 'pink', 'brown', 'beige', 'clear']

    # Color codes in product names (BLU, GRY, ORG, etc.)
    color_code_matches = re.findall(r'\b([A-Z]{3})\b', product_name)
    colors.extend(color_code_matches)

    for color in color_keywords:
        if color in text:
            colors.append(color)

    return list(set(colors))

# Function to extract material info
def extract_materials(product_name, description):
    """Extract material information"""
    materials = []
    text = f"{product_name} {description or ''}".lower()

    material_keywords = ['vinyl', 'rubber', 'foam', 'pvc', 'polyurethane', 'plastic',
                        'metal', 'steel', 'aluminum', 'cushion', 'flex', 'seal']

    for material in material_keywords:
        if material in text:
            materials.append(material)

    return list(set(materials))

# Function to extract SDS code
def extract_sds_code(product_name, default_code, description):
    """Extract SDS code from product information"""
    text = f"{product_name} {default_code or ''} {description or ''}"

    # Pattern: SDS007J, SDS123A, etc.
    sds_matches = re.findall(r'SDS\d{3,}[A-Z]?', text, re.IGNORECASE)

    return sds_matches[0] if sds_matches else None

# Group products by family
product_families = defaultdict(list)

for product in products:
    name = product.get('name', '')
    if not name:
        continue

    # Extract family name
    family_name = extract_product_family(name)
    if not family_name:
        family_name = name.split()[0] if name.split() else "Unknown"

    # Extract all relevant information
    product_info = {
        'full_name': name,
        'default_code': product.get('default_code', ''),
        'barcode': product.get('barcode', ''),
        'sds_code': extract_sds_code(name, product.get('default_code'), product.get('description')),
        'dimensions': extract_dimensions(name, product.get('description')),
        'colors': extract_colors(name, product.get('description')),
        'materials': extract_materials(name, product.get('description')),
        'price': product.get('list_price', 0),
        'uom': product.get('uom_name', ''),
        'description': product.get('description', ''),
        'description_sale': product.get('description_sale', ''),
        'category': product.get('categ_id', ['', ''])[1] if product.get('categ_id') else ''
    }

    product_families[family_name].append(product_info)

print(f"Product families identified: {len(product_families)}")

# Create individual files for each product family
output_dir = 'DSPY-products'
os.makedirs(output_dir, exist_ok=True)

# Also create a master index
master_index = {
    'total_families': len(product_families),
    'families': {}
}

for family_name, variants in product_families.items():
    # Create a safe filename
    safe_filename = re.sub(r'[^\w\s-]', '', family_name)
    safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
    safe_filename = safe_filename[:100]  # Limit length

    if not safe_filename:
        safe_filename = "Unknown_Product"

    # Organize the product family data
    family_data = {
        'product_family': family_name,
        'total_variants': len(variants),
        'variants': variants,
        'all_codes': list(set([v['default_code'] for v in variants if v['default_code']])),
        'all_sds_codes': list(set([v['sds_code'] for v in variants if v['sds_code']])),
        'all_dimensions': list(set([d for v in variants for d in v['dimensions']])),
        'all_colors': list(set([c for v in variants for c in v['colors']])),
        'all_materials': list(set([m for v in variants for m in v['materials']])),
        'price_range': {
            'min': min([v['price'] for v in variants if v['price']]) if any(v['price'] for v in variants) else 0,
            'max': max([v['price'] for v in variants if v['price']]) if any(v['price'] for v in variants) else 0
        }
    }

    # Save individual family file
    family_file = os.path.join(output_dir, f"{safe_filename}.json")
    with open(family_file, 'w', encoding='utf-8') as f:
        json.dump(family_data, f, indent=2, ensure_ascii=False)

    # Add to master index
    master_index['families'][family_name] = {
        'file': f"{safe_filename}.json",
        'variant_count': len(variants),
        'codes': family_data['all_codes'][:5],  # First 5 codes as preview
        'sds_codes': family_data['all_sds_codes']
    }

# Save master index
with open(os.path.join(output_dir, '_MASTER_INDEX.json'), 'w', encoding='utf-8') as f:
    json.dump(master_index, f, indent=2, ensure_ascii=False)

# Create a human-readable summary
with open(os.path.join(output_dir, '_SUMMARY.txt'), 'w', encoding='utf-8') as f:
    f.write("DSPY PRODUCT ORGANIZATION SUMMARY\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Total Product Families: {len(product_families)}\n")
    f.write(f"Total Products: {len(products)}\n\n")
    f.write("Product Families (sorted by variant count):\n")
    f.write("-" * 80 + "\n\n")

    for family_name, variants in sorted(product_families.items(), key=lambda x: len(x[1]), reverse=True):
        f.write(f"{family_name}\n")
        f.write(f"  Variants: {len(variants)}\n")

        codes = [v['default_code'] for v in variants if v['default_code']]
        if codes:
            f.write(f"  Codes: {', '.join(codes[:5])}")
            if len(codes) > 5:
                f.write(f" ... and {len(codes) - 5} more")
            f.write("\n")

        sds_codes = [v['sds_code'] for v in variants if v['sds_code']]
        if sds_codes:
            f.write(f"  SDS Codes: {', '.join(list(set(sds_codes)))}\n")

        dimensions = list(set([d for v in variants for d in v['dimensions']]))
        if dimensions:
            f.write(f"  Dimensions: {', '.join(dimensions[:3])}")
            if len(dimensions) > 3:
                f.write(f" ... and {len(dimensions) - 3} more")
            f.write("\n")

        colors = list(set([c for v in variants for c in v['colors']]))
        if colors:
            f.write(f"  Colors: {', '.join(colors[:5])}\n")

        f.write("\n")

print(f"\nCreated {len(product_families)} product family files in {output_dir}/")
print("Created _MASTER_INDEX.json for quick reference")
print("Created _SUMMARY.txt for human-readable overview")
