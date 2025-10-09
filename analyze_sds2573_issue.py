"""
Analyze why SDS2573 (Foam Seal) is scoring higher than correct SDS007 products
"""
from sentence_transformers import SentenceTransformer
import numpy as np
from pathlib import Path
import json

def analyze_issue():
    """Analyze the SDS2573 matching issue"""

    # Load fine-tuned model
    model_path = Path("models/finetuned-product-matcher")
    print(f"[INFO] Loading fine-tuned model from {model_path}")
    model = SentenceTransformer(str(model_path))

    # Customer query
    customer_query = "DuroSeal W&H End Seals Miraflex SDS 007 CR Grau"

    # Load products
    with open('odoo_database/odoo_products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)

    # Get the problematic product
    sds2573 = next((p for p in products if p.get('default_code') == 'SDS2573'), None)
    sds007h = next((p for p in products if p.get('default_code') == 'SDS007H'), None)

    if not sds2573 or not sds007h:
        print("[ERROR] Products not found")
        return

    print(f"\n{'='*80}")
    print(f"PROBLEM ANALYSIS: Why SDS2573 scores higher than SDS007H")
    print(f"{'='*80}\n")

    print(f"Customer Query:")
    print(f"  '{customer_query}'")
    print(f"\nKey terms: DuroSeal, W&H, End Seals, Miraflex, SDS 007, CR Grau")
    print()

    print(f"CORRECT PRODUCT (SDS007H):")
    print(f"  Code: {sds007h.get('default_code')}")
    print(f"  Name: {sds007h.get('name')}")
    print(f"  Full: '{sds007h.get('default_code')} {sds007h.get('name')}'")
    print(f"\n  Matching keywords:")
    sds007h_text = f"{sds007h.get('default_code')} {sds007h.get('name')}".upper()
    if 'DURO SEAL' in sds007h_text or 'DUROSEAL' in sds007h_text:
        print(f"    - Duro Seal: YES")
    if 'W&H' in sds007h_text:
        print(f"    - W&H: YES")
    if 'MIRAFLEX' in sds007h_text:
        print(f"    - Miraflex: YES")
    if 'SDS007' in sds007h_text:
        print(f"    - SDS007: YES (code)")
    if 'CR' in sds007h_text and 'GR' in sds007h_text:
        print(f"    - CR-GRY: YES")
    print()

    print(f"WRONG PRODUCT (SDS2573 - Scoring HIGHER!):")
    print(f"  Code: {sds2573.get('default_code')}")
    print(f"  Name: {sds2573.get('name')}")
    print(f"  Full: '{sds2573.get('default_code')} {sds2573.get('name')}'")
    print(f"\n  Matching keywords:")
    sds2573_text = f"{sds2573.get('default_code')} {sds2573.get('name')}".upper()
    if 'DURO SEAL' in sds2573_text or 'DUROSEAL' in sds2573_text:
        print(f"    - Duro Seal: NO")
    else:
        print(f"    - Duro Seal: NO (but has 'Foam Seal')")
    if 'W&H' in sds2573_text:
        print(f"    - W&H: YES")
    else:
        print(f"    - W&H: NO")
    if 'MIRAFLEX' in sds2573_text:
        print(f"    - Miraflex: YES")
    else:
        print(f"    - Miraflex: NO")
    if 'SDS' in sds2573_text:
        print(f"    - SDS: YES (code starts with SDS)")
    if 'FOAM SEAL' in sds2573_text:
        print(f"    - Foam Seal: YES (similar to 'Duro Seal'?)")
    print()

    # Compute similarities
    query_emb = model.encode(customer_query, convert_to_tensor=False)
    sds007h_emb = model.encode(f"{sds007h.get('default_code')} {sds007h.get('name')}", convert_to_tensor=False)
    sds2573_emb = model.encode(f"{sds2573.get('default_code')} {sds2573.get('name')}", convert_to_tensor=False)

    sim_007h = np.dot(query_emb, sds007h_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(sds007h_emb))
    sim_2573 = np.dot(query_emb, sds2573_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(sds2573_emb))

    print(f"SIMILARITY SCORES:")
    print(f"  SDS007H (CORRECT): {sim_007h:.4f} ({sim_007h*100:.2f}%)")
    print(f"  SDS2573 (WRONG):   {sim_2573:.4f} ({sim_2573*100:.2f}%)")
    print(f"  Difference: {(sim_2573-sim_007h)*100:.2f}% (SDS2573 is HIGHER!)")
    print()

    # Hypothesis: Training issue
    print(f"{'='*80}")
    print(f"ROOT CAUSE HYPOTHESIS:")
    print(f"{'='*80}\n")

    print(f"1. SEMANTIC SIMILARITY ISSUE:")
    print(f"   - Both products have 'SDS' prefix (same category)")
    print(f"   - Both are 'seals' (Duro Seal vs Foam Seal)")
    print(f"   - BERT may have learned that 'Seal' products are similar")
    print(f"   - Fine-tuning created positive pairs between ALL SDS products")
    print()

    print(f"2. TRAINING PAIR GENERATION:")
    print(f"   - SDS007H and SDS2573 are both SDS products")
    print(f"   - Training likely created POSITIVE pairs between them!")
    print(f"   - This taught BERT they are SIMILAR (wrong!)")
    print()

    print(f"3. TEXT OVERLAP:")
    print(f"   - Customer: 'End Seals'")
    print(f"   - SDS007H: 'Duro Seal'")
    print(f"   - SDS2573: 'Foam Seal'")
    print(f"   - 'Seal' appears in all -> high similarity")
    print()

    # Check if they were paired in training
    print(f"{'='*80}")
    print(f"CHECKING TRAINING PAIRS:")
    print(f"{'='*80}\n")

    # Check if SDS007H and SDS2573 would be considered similar
    from retriever_module.bert_finetuner import BERTFineTuner
    finetuner = BERTFineTuner(
        products_json_path="odoo_database/odoo_products.json",
        base_model="Alibaba-NLP/gte-modernbert-base",
        output_model_path="models/finetuned-product-matcher",
        use_cuda_for_training=False
    )

    feat_007h = finetuner._extract_product_features(sds007h)
    feat_2573 = finetuner._extract_product_features(sds2573)

    print(f"SDS007H Features:")
    print(f"  Category: {feat_007h.get('category_prefix')}")
    print(f"  Dimensions: {feat_007h.get('dimensions')}")
    print(f"  Materials: {feat_007h.get('materials')}")
    print()

    print(f"SDS2573 Features:")
    print(f"  Category: {feat_2573.get('category_prefix')}")
    print(f"  Dimensions: {feat_2573.get('dimensions')}")
    print(f"  Materials: {feat_2573.get('materials')}")
    print()

    are_similar = finetuner._are_similar_products(sds007h, sds2573)
    print(f"Would these be POSITIVE training pairs? {are_similar}")
    print()

    if are_similar:
        print(f"[ISSUE CONFIRMED] SDS007H and SDS2573 were trained as SIMILAR products!")
        print(f"This is why SDS2573 scores so high for 'DuroSeal' queries.")
        print()

    print(f"{'='*80}")
    print(f"SOLUTION:")
    print(f"{'='*80}\n")
    print(f"Option 1: Refine similarity logic to distinguish Duro Seal from Foam Seal")
    print(f"Option 2: Add product sub-type to features (Duro vs Foam)")
    print(f"Option 3: Use negative pairs: (Duro Seal query, Foam Seal product)")
    print(f"Option 4: Increase BERT threshold from 60% to 95% (only very high matches)")

if __name__ == "__main__":
    analyze_issue()
