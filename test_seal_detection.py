"""
Test seal sub-type detection
"""
import json
from retriever_module.bert_finetuner import BERTFineTuner

# Load products
with open('odoo_database/odoo_products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# Get test products
sds007h = next((p for p in products if p.get('default_code') == 'SDS007H'), None)
sds2573 = next((p for p in products if p.get('default_code') == 'SDS2573'), None)

finetuner = BERTFineTuner(
    products_json_path="odoo_database/odoo_products.json",
    base_model="Alibaba-NLP/gte-modernbert-base",
    output_model_path="models/finetuned-product-matcher",
    use_cuda_for_training=False
)

print("SDS007H Product:")
print(f"  Code: {sds007h.get('default_code')}")
print(f"  Name: {sds007h.get('name')}")
print(f"  Full text: '{sds007h.get('default_code')} {sds007h.get('name')}'")

feat_007h = finetuner._extract_product_features(sds007h)
print(f"\nExtracted Features:")
print(f"  Category: {feat_007h.get('category')}")
print(f"  Dimensions: {feat_007h.get('dimensions')}")
print(f"  Materials: {feat_007h.get('materials')}")
print(f"  Seal Subtype: {feat_007h.get('seal_subtype')}")

print("\n" + "="*80)
print("\nSDS2573 Product:")
print(f"  Code: {sds2573.get('default_code')}")
print(f"  Name: {sds2573.get('name')}")
print(f"  Full text: '{sds2573.get('default_code')} {sds2573.get('name')}'")

feat_2573 = finetuner._extract_product_features(sds2573)
print(f"\nExtracted Features:")
print(f"  Category: {feat_2573.get('category')}")
print(f"  Dimensions: {feat_2573.get('dimensions')}")
print(f"  Materials: {feat_2573.get('materials')}")
print(f"  Seal Subtype: {feat_2573.get('seal_subtype')}")

print("\n" + "="*80)
print("\nAre they similar?", finetuner._are_similar_products(sds007h, sds2573))
