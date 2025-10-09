"""
Hybrid Matcher Module

Combines BERT semantic understanding with Token-based dimension precision
for accurate product matching.

Two-Stage Architecture:
  Stage 1 (BERT Semantic Filter):
    - Filters products by semantic similarity (tape vs seal, blade vs adhesive)
    - Returns top 20 candidates with 60%+ semantic match
    - Handles multilingual queries (German ↔ English)
    - Eliminates false positives from wrong product categories

  Stage 2 (Token Dimension Refinement):
    - Re-ranks BERT candidates using dimension matching
    - Exact number matching (310 must match 310, not 120)
    - Dimension pattern matching (310x25, 1335mm, etc.)
    - Final score = bert_score * (1.0 + token_bonus * 0.5)

Benefits:
  - Eliminates semantic false positives (OPP tape → Foam seal)
  - Maintains dimension precision (310x25 ≠ 120x31)
  - Faster than pure token matching (20 candidates vs 1000+)
  - Backward compatible with fallback to TokenMatcher

Author: Claude Code
Date: 2025-10-09
"""

import re
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class HybridMatcher:
    """
    Hybrid product matcher combining BERT + Token matching.

    Uses two-stage pipeline:
      1. BERT semantic filter → Top 20 candidates
      2. Token dimension refinement → Final top K results
    """

    def __init__(
        self,
        products_json_path: str,
        use_bert: bool = True,
        bert_model_name: str = "Alibaba-NLP/gte-modernbert-base",
        cache_dir: str = ".bert_cache"
    ):
        """
        Initialize Hybrid Matcher.

        Args:
            products_json_path: Path to products JSON file
            use_bert: Enable BERT semantic matching (True recommended)
            bert_model_name: HuggingFace model identifier
            cache_dir: Directory for caching BERT embeddings
        """
        self.products_json_path = Path(products_json_path)
        self.use_bert = use_bert

        # Initialize Token Matcher (always available)
        from retriever_module.token_matcher import TokenMatcher
        self.token_matcher = TokenMatcher(str(products_json_path))
        logger.info("[OK] TokenMatcher initialized")

        # Initialize BERT Matcher (optional)
        self.bert_matcher = None
        if use_bert:
            try:
                from retriever_module.bert_semantic_matcher import BertSemanticMatcher
                self.bert_matcher = BertSemanticMatcher(
                    products_json_path=str(products_json_path),
                    model_name=bert_model_name,
                    cache_dir=cache_dir
                )
                logger.info(f"[OK] BertSemanticMatcher initialized with {bert_model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize BERT matcher: {e}")
                logger.warning("Falling back to TokenMatcher only")
                self.use_bert = False

    def _extract_dimensions(self, text: str) -> List[str]:
        """
        Extract dimension numbers from text.

        Returns list of dimension values for exact matching.

        Args:
            text: Text containing dimensions

        Returns:
            List of dimension numbers (e.g., ['310', '25', '1335'])
        """
        patterns = [
            r'\b(\d{2,4})\s*[xX*]\s*(\d{1,3}(?:[.,]\d{1,2})?)',  # 310x25, 35x0.20
            r'(?:Länge|Length|L)[\s:]*(\d{3,5})\s*mm',  # Länge 1335mm
            r'\b(\d{3,5})\s*mm\b',  # 1335mm
        ]

        dimensions = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Add all captured groups
                for group in match.groups():
                    if group:
                        # Normalize: remove spaces, convert comma to dot
                        normalized = group.replace(' ', '').replace(',', '.')
                        dimensions.append(normalized)

        return dimensions

    def _calculate_dimension_bonus(
        self,
        query: str,
        product_text: str,
        max_bonus: float = 0.4
    ) -> float:
        """
        Calculate dimension matching bonus.

        Awards bonus for exact dimension matches between query and product.
        Unlike the old token matcher, this only awards bonus for EXACT matches.

        Args:
            query: Search query
            product_text: Product description
            max_bonus: Maximum bonus multiplier (0.4 = +40%)

        Returns:
            Bonus multiplier (0.0 to max_bonus)
        """
        query_dims = set(self._extract_dimensions(query))
        product_dims = set(self._extract_dimensions(product_text))

        if not query_dims or not product_dims:
            return 0.0

        # Count exact matches
        matches = query_dims & product_dims
        total_query_dims = len(query_dims)

        if total_query_dims == 0:
            return 0.0

        # Award bonus proportional to match percentage
        match_ratio = len(matches) / total_query_dims
        bonus = match_ratio * max_bonus

        logger.debug(f"Dimension bonus: {bonus:.2f} (matched {len(matches)}/{total_query_dims})")
        return bonus

    def _get_product_text(self, product: Dict) -> str:
        """
        Get searchable text representation of product.

        Args:
            product: Product dictionary

        Returns:
            Combined text for token matching
        """
        parts = []
        if product.get('product_code'):
            parts.append(product['product_code'])
        if product.get('product_name'):
            parts.append(product['product_name'])
        return ' '.join(parts)

    def _token_rerank(
        self,
        query: str,
        bert_candidates: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Re-rank BERT candidates using token-based dimension matching.

        Args:
            query: Search query
            bert_candidates: Candidates from BERT stage
            top_k: Number of final results

        Returns:
            Re-ranked products with final scores
        """
        results = []

        for candidate in bert_candidates:
            # Get BERT score
            bert_score = candidate.get('bert_score', 0.0)

            # Calculate dimension bonus
            product_text = self._get_product_text(candidate)
            dimension_bonus = self._calculate_dimension_bonus(query, product_text)

            # Calculate final score
            # Formula: final = bert * (1.0 + dimension_bonus * 0.5)
            # Example: 80% BERT + 40% dim bonus = 80% * 1.2 = 96%
            final_score = bert_score * (1.0 + dimension_bonus * 0.5)

            # Add to result
            result = candidate.copy()
            result['final_score'] = final_score
            result['final_score_percent'] = f"{final_score * 100:.1f}%"
            result['dimension_bonus'] = dimension_bonus
            result['dimension_bonus_percent'] = f"{dimension_bonus * 100:.1f}%"

            results.append(result)

        # Sort by final score
        results.sort(key=lambda x: x['final_score'], reverse=True)

        # Return top K
        return results[:top_k]

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.5
    ) -> List[Dict]:
        """
        Search for products using hybrid BERT + Token matching.

        Pipeline:
          1. BERT semantic filter (if enabled) → 20 candidates @ 60% threshold
          2. Token dimension refinement → Top K results

        Args:
            query: Search query (product name, code, dimensions)
            top_k: Number of results to return
            min_score: Minimum final score threshold (0-1)

        Returns:
            List of matching products with scores
        """
        # Stage 1: BERT Semantic Filter
        if self.use_bert and self.bert_matcher:
            logger.info(f"Stage 1: BERT semantic filter for query: '{query}'")

            bert_candidates = self.bert_matcher.search(
                query=query,
                top_k=20,  # Get 20 candidates for refinement
                min_score=0.60  # 60% semantic threshold
            )

            if not bert_candidates:
                logger.warning("No BERT candidates found, falling back to token matching")
                # Fall back to pure token matching
                return self.token_matcher.search(query, top_k=top_k, min_score=min_score)

            logger.info(f"BERT stage: {len(bert_candidates)} candidates")

            # Stage 2: Token Dimension Refinement
            logger.info("Stage 2: Token dimension refinement")
            final_results = self._token_rerank(query, bert_candidates, top_k=top_k)

            # Filter by minimum final score
            final_results = [r for r in final_results if r['final_score'] >= min_score]

            logger.info(f"Final results: {len(final_results)} products")
            return final_results

        else:
            # Fall back to pure token matching
            logger.info("Using TokenMatcher only (BERT disabled)")
            return self.token_matcher.search(query, top_k=top_k, min_score=min_score)

    def search_by_code(
        self,
        product_code: str,
        min_score: float = 0.70
    ) -> Optional[Dict]:
        """
        Search for product by exact code.

        First tries exact match, then semantic search if BERT enabled.

        Args:
            product_code: Product code to search
            min_score: Minimum score for semantic fallback

        Returns:
            Matching product or None
        """
        # Try exact match in token matcher first (fastest)
        exact_match = self.token_matcher.search_by_code(product_code)
        if exact_match:
            logger.info(f"Exact code match: {product_code}")
            result = exact_match.copy()
            result['final_score'] = 1.0
            result['final_score_percent'] = "100%"
            return result

        # Fall back to BERT semantic search if available
        if self.use_bert and self.bert_matcher:
            logger.info(f"No exact match for '{product_code}', using BERT semantic search")
            results = self.search(product_code, top_k=1, min_score=min_score)
            return results[0] if results else None

        # No match found
        logger.warning(f"No match found for product code: {product_code}")
        return None

    def get_stats(self) -> Dict:
        """
        Get matcher statistics.

        Returns:
            Dictionary with matcher info and stats
        """
        stats = {
            'matcher_type': 'hybrid',
            'bert_enabled': self.use_bert,
            'products_loaded': len(self.token_matcher.products),
        }

        if self.bert_matcher:
            stats['bert_model'] = self.bert_matcher.model_name
            stats['bert_device'] = self.bert_matcher.device
            stats['embeddings_cached'] = True

        return stats


if __name__ == "__main__":
    # Test the hybrid matcher
    logging.basicConfig(level=logging.INFO)

    print("Initializing HybridMatcher...")
    matcher = HybridMatcher("products.json", use_bert=True)

    print("\n" + "="*80)
    print("Matcher Statistics:")
    print("="*80)
    for key, value in matcher.get_stats().items():
        print(f"  {key}: {value}")

    # Test queries
    test_queries = [
        "OPP Klischeeklebeband 310 x 25",
        "Rakelmesser Edelstahl Gold 35x0,20 RPE Länge 1335mm",
        "Foam Seal 120 x 31",
        "3M Cushion Mount Plus E1015"
    ]

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print('='*80)

        results = matcher.search(query, top_k=5)

        if not results:
            print("  No matches found")
            continue

        for i, result in enumerate(results, 1):
            print(f"\n{i}. [{result.get('final_score_percent', 'N/A')}] {result.get('product_code', 'N/A')}")
            print(f"   {result.get('product_name', 'N/A')}")
            print(f"   BERT: {result.get('bert_score_percent', 'N/A')} | "
                  f"Dimension Bonus: {result.get('dimension_bonus_percent', 'N/A')}")
