import json
from collections import defaultdict

# Read the Odoo products JSON
with open('odoo_database/odoo_products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# Organized structure for DSPy
organized_products = []

for product in products:
    # Extract basic product info
    product_info = {
        'product_id': product.get('id'),
        'name': product.get('name', ''),
        'default_code': product.get('default_code', ''),
        'barcode': product.get('barcode', ''),
        'category': product.get('categ_id', ['', ''])[1] if product.get('categ_id') else '',
        'product_type': product.get('type', ''),
        'list_price': product.get('list_price', 0),
        'standard_price': product.get('standard_price', 0),
        'uom': product.get('uom_name', ''),
        'description': product.get('description', ''),
        'description_sale': product.get('description_sale', ''),
        'variants': []
    }

    # Extract attributes (colors, dimensions, etc.)
    attributes = {}
    if product.get('attribute_line_ids'):
        for attr_line in product.get('attribute_line_ids', []):
            attr_name = attr_line.get('attribute_id', ['', ''])[1] if attr_line.get('attribute_id') else ''
            attr_values = [v[1] for v in attr_line.get('value_ids', []) if len(v) > 1]
            if attr_name:
                attributes[attr_name] = attr_values

    product_info['attributes'] = attributes

    # Extract product variants
    if product.get('product_variant_ids'):
        for variant_ref in product.get('product_variant_ids', []):
            # Find the variant details in the products list
            variant_id = variant_ref[0] if isinstance(variant_ref, list) else variant_ref

            # Look for variant in products
            variant_data = next((p for p in products if p.get('id') == variant_id), None)

            if variant_data and variant_data.get('id') != product.get('id'):
                variant_info = {
                    'variant_id': variant_data.get('id'),
                    'name': variant_data.get('name', ''),
                    'default_code': variant_data.get('default_code', ''),
                    'barcode': variant_data.get('barcode', ''),
                    'list_price': variant_data.get('list_price', 0),
                    'standard_price': variant_data.get('standard_price', 0),
                    'variant_attributes': {}
                }

                # Extract variant-specific attributes
                if variant_data.get('product_template_attribute_value_ids'):
                    for attr_val_ref in variant_data.get('product_template_attribute_value_ids', []):
                        # This would need to be matched with actual attribute values
                        pass

                product_info['variants'].append(variant_info)

    organized_products.append(product_info)

# Group by category for better organization
products_by_category = defaultdict(list)
for prod in organized_products:
    category = prod.get('category', 'Uncategorized')
    products_by_category[category].append(prod)

# Create final structured output
final_output = {
    'total_products': len(organized_products),
    'categories': list(products_by_category.keys()),
    'products_by_category': dict(products_by_category),
    'all_products': organized_products
}

# Save organized products
with open('organized_products_for_dspy.json', 'w', encoding='utf-8') as f:
    json.dump(final_output, f, indent=2, ensure_ascii=False)

# Create a simplified flat list for DSPy training
dspy_training_data = []
for product in organized_products:
    # Main product entry
    entry = {
        'product_name': product['name'],
        'product_code': product['default_code'],
        'category': product['category'],
        'price': product['list_price'],
        'attributes': product['attributes'],
        'description': product['description_sale'] or product['description'],
        'has_variants': len(product['variants']) > 0,
        'variant_count': len(product['variants'])
    }
    dspy_training_data.append(entry)

    # Add variant entries
    for variant in product['variants']:
        variant_entry = {
            'product_name': variant['name'],
            'product_code': variant['default_code'],
            'category': product['category'],
            'price': variant['list_price'],
            'attributes': variant['variant_attributes'],
            'description': f"Variant of {product['name']}",
            'is_variant': True,
            'parent_product': product['name']
        }
        dspy_training_data.append(variant_entry)

with open('dspy_product_training_data.json', 'w', encoding='utf-8') as f:
    json.dump(dspy_training_data, f, indent=2, ensure_ascii=False)

# Create a summary report
summary = {
    'total_products': len(organized_products),
    'total_entries_with_variants': len(dspy_training_data),
    'categories': {},
    'attribute_types': set()
}

for product in organized_products:
    cat = product['category'] or 'Uncategorized'
    if cat not in summary['categories']:
        summary['categories'][cat] = 0
    summary['categories'][cat] += 1

    for attr_name in product['attributes'].keys():
        summary['attribute_types'].add(attr_name)

summary['attribute_types'] = list(summary['attribute_types'])

with open('product_organization_summary.txt', 'w', encoding='utf-8') as f:
    f.write("PRODUCT ORGANIZATION SUMMARY\n")
    f.write("=" * 50 + "\n\n")
    f.write(f"Total Products: {summary['total_products']}\n")
    f.write(f"Total Entries (including variants): {summary['total_entries_with_variants']}\n\n")
    f.write("Products by Category:\n")
    for cat, count in sorted(summary['categories'].items(), key=lambda x: x[1], reverse=True):
        f.write(f"  {cat}: {count}\n")
    f.write(f"\nAttribute Types Found: {', '.join(summary['attribute_types'])}\n")

print("Created organized_products_for_dspy.json (full structure with categories)")
print("Created dspy_product_training_data.json (flattened for DSPy training)")
print("Created product_organization_summary.txt (summary report)")
print(f"\nProcessed {len(organized_products)} products")
print(f"Generated {len(dspy_training_data)} training entries (including variants)")
