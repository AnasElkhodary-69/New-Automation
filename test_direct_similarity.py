"""
Test direct BERT similarity between customer query and SDS007 products
"""
from sentence_transformers import SentenceTransformer
import numpy as np
from pathlib import Path
import json

def test_similarity():
    """Test direct similarity scores"""

    # Load fine-tuned model
    model_path = Path("models/finetuned-product-matcher")

    if not model_path.exists():
        print(f"[ERROR] Fine-tuned model not found at {model_path}")
        return

    print(f"[INFO] Loading fine-tuned model from {model_path}")
    model = SentenceTransformer(str(model_path))

    # Customer query
    customer_query = "DuroSeal W&H End Seals Miraflex SDS 007 CR Grau"

    # Load products
    with open('odoo_database/odoo_products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)

    # Get SDS007H and SDS007C
    sds007h = next((p for p in products if p.get('default_code') == 'SDS007H'), None)
    sds007c = next((p for p in products if p.get('default_code') == 'SDS007C'), None)

    # Also test some wrong products that BERT is matching
    sds2573 = next((p for p in products if p.get('default_code') == 'SDS2573'), None)
    doctor_blade = next((p for p in products if 'C-40-20-RPE-L1335' in str(p.get('default_code', ''))), None)

    print(f"\n{'='*80}")
    print(f"Customer Query: '{customer_query}'")
    print(f"{'='*80}\n")

    # Encode query
    query_emb = model.encode(customer_query, convert_to_tensor=False)

    def test_product(product, label):
        if product is None:
            print(f"[ERROR] {label} not found")
            return

        code = product.get('default_code', '')
        name = product.get('name', '')
        full_text = f"{code} {name}"

        # Encode product
        product_emb = model.encode(full_text, convert_to_tensor=False)

        # Calculate cosine similarity
        similarity = np.dot(query_emb, product_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(product_emb))

        print(f"{label}:")
        print(f"  Code: {code}")
        print(f"  Name: {name}")
        print(f"  Full text: '{full_text}'")
        print(f"  Similarity: {similarity:.4f} ({similarity*100:.2f}%)")
        print()

    # Test correct products
    print("CORRECT PRODUCTS (Expected to match):")
    print("-" * 80)
    test_product(sds007h, "SDS007H")
    test_product(sds007c, "SDS007C")

    # Test wrong products
    print("\nWRONG PRODUCTS (Currently matching incorrectly):")
    print("-" * 80)
    test_product(sds2573, "SDS2573 (Foam Seal)")
    test_product(doctor_blade, "C-40-20-RPE-L1335 (Doctor Blade)")

    # Test with text variations to see if normalization helps
    print("\n" + "="*80)
    print("Testing Text Variations (Normalized):")
    print("="*80 + "\n")

    # Normalize customer query
    normalized_queries = [
        customer_query,  # Original
        "Duro Seal W&H End Seals Miraflex SDS007 CR GRY",  # Match DB format
        "DuroSeal W&H Miraflex SDS 007 CR Gray",  # Simplified
        "Duro Seal W&H Miraflex SDS007H CR-GRY",  # Exact match attempt
    ]

    if sds007h:
        code = sds007h.get('default_code', '')
        name = sds007h.get('name', '')
        product_text = f"{code} {name}"
        product_emb = model.encode(product_text, convert_to_tensor=False)

        print(f"Testing variations against SDS007H:")
        print(f"Product text: '{product_text}'")
        print()

        for i, query_var in enumerate(normalized_queries, 1):
            query_var_emb = model.encode(query_var, convert_to_tensor=False)
            similarity = np.dot(query_var_emb, product_emb) / (np.linalg.norm(query_var_emb) * np.linalg.norm(product_emb))
            print(f"  {i}. Query: '{query_var}'")
            print(f"     Similarity: {similarity:.4f} ({similarity*100:.2f}%)")
            print()

if __name__ == "__main__":
    test_similarity()
