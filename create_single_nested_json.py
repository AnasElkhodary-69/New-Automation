import json
import os

# Read all the individual product family files from DSPY-products folder
dspy_products_dir = 'DSPY-products'

all_product_families = {}

print("Reading all product family files...")

# Get all JSON files except the master index and summary
for filename in os.listdir(dspy_products_dir):
    if filename.endswith('.json') and not filename.startswith('_'):
        filepath = os.path.join(dspy_products_dir, filename)

        with open(filepath, 'r', encoding='utf-8') as f:
            product_data = json.load(f)
            family_name = product_data['product_family']
            all_product_families[family_name] = product_data

print(f"Loaded {len(all_product_families)} product families")

# Create the complete nested structure
complete_catalog = {
    "catalog_info": {
        "total_product_families": len(all_product_families),
        "total_variants": sum(family['total_variants'] for family in all_product_families.values()),
        "description": "Complete product catalog organized by product families with all variants, codes, dimensions, colors, and materials"
    },
    "product_families": all_product_families
}

# Save as single nested JSON
output_file = 'DSPY-products/COMPLETE_PRODUCT_CATALOG.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(complete_catalog, f, indent=2, ensure_ascii=False)

print(f"\nCreated {output_file}")
print(f"Total product families: {complete_catalog['catalog_info']['total_product_families']}")
print(f"Total variants: {complete_catalog['catalog_info']['total_variants']}")

# Also create a more compact version without descriptions
compact_catalog = {
    "catalog_info": complete_catalog["catalog_info"],
    "product_families": {}
}

for family_name, family_data in all_product_families.items():
    compact_catalog["product_families"][family_name] = {
        "total_variants": family_data["total_variants"],
        "all_codes": family_data["all_codes"],
        "all_sds_codes": family_data["all_sds_codes"],
        "all_dimensions": family_data["all_dimensions"],
        "all_colors": family_data["all_colors"],
        "all_materials": family_data["all_materials"],
        "price_range": family_data["price_range"],
        "variants": [
            {
                "full_name": v["full_name"],
                "default_code": v["default_code"],
                "sds_code": v["sds_code"],
                "dimensions": v["dimensions"],
                "colors": v["colors"],
                "materials": v["materials"],
                "price": v["price"]
            }
            for v in family_data["variants"]
        ]
    }

compact_output = 'DSPY-products/COMPACT_PRODUCT_CATALOG.json'
with open(compact_output, 'w', encoding='utf-8') as f:
    json.dump(compact_catalog, f, indent=2, ensure_ascii=False)

print(f"Created {compact_output} (compact version without descriptions)")
