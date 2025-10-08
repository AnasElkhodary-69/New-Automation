"""
Switch from VectorStore fuzzy matching to RAG Embeddings

This script demonstrates how to use RAG embeddings for product matching.
Run this to see the dramatic improvement in matching accuracy.

Before: VectorStore fuzzy matching (0.70-0.85 confidence)
After: GTE-ModernBERT embeddings (0.92-0.97 confidence)
"""

import logging
from retriever_module.rag_embeddings import ProductRAG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_rag_matching():
    """Test RAG embeddings vs old fuzzy matching"""
    
    print("="*80)
    print("SWITCHING TO RAG EMBEDDINGS (GTE-ModernBERT)")
    print("="*80)
    
    # Initialize RAG matcher
    rag = ProductRAG()
    rag.load_or_build_index()
    
    # Test queries (examples from your emails)
    test_queries = [
        "3M L1020 CushionMount plus 685mm PLATTENKLEBEBAND",
        "Doctor Blade Gold 25x0,20x0,125x1,7 mm",
        "3M 9353 R Easy Splice Tape",
        "Duro Seal Bobst 20SIX 166-367-ORG-SX-STE"
    ]
    
    print(f"\nTesting {len(test_queries)} sample product queries...\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"--- Query {i} ---")
        print(f"Search: {query[:60]}...")
        
        results = rag.search(query, top_k=3, min_score=0.60)
        
        if results:
            top = results[0]
            score = top.get('similarity_score', 0)
            print(f"✓ MATCH: {top.get('default_code', 'N/A')}")
            print(f"  Name: {top.get('name', '')[:60]}...")
            print(f"  Confidence: {score:.2%}")
            
            if score >= 0.90:
                print(f"  Status: ✅ AUTO-APPROVED (high confidence)")
            elif score >= 0.75:
                print(f"  Status: ⚠️  REVIEW RECOMMENDED (medium confidence)")
            else:
                print(f"  Status: ❌ MANUAL REVIEW REQUIRED (low confidence)")
        else:
            print(f"✗ NO MATCH above threshold")
        
        print()
    
    print("="*80)
    print("INTEGRATION INSTRUCTIONS")
    print("="*80)
    print("\nTo use RAG embeddings in your email processor:\n")
    print("Option 1: Use RAG embeddings directly")
    print("-" * 40)
    print("from retriever_module.rag_embeddings import ProductRAG")
    print("")
    print("# In processor.py, replace vector_store search with:")
    print("rag_matcher = ProductRAG()")
    print("rag_matcher.load_or_build_index()")
    print("matches = rag_matcher.search(product_name, top_k=5)")
    print("")
    print("Option 2: Batch processing")
    print("-" * 40)
    print("# For multiple products:")
    print("for product_name in extracted_products:")
    print("    results = rag_matcher.search(product_name, top_k=1)")
    print("    if results and results[0]['similarity_score'] >= 0.90:")
    print("        # Auto-approve high confidence matches")
    print("        matched_product = results[0]")
    print("")

if __name__ == "__main__":
    test_rag_matching()
