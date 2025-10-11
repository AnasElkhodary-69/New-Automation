"""
Token-Based Product Matching

Matches products by counting overlapping tokens (words, numbers, codes)
instead of semantic similarity. Much more accurate for product matching.
"""

import re
import json
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.product_validator import is_valid_product_code, get_code_confidence

logger = logging.getLogger(__name__)


class TokenMatcher:
    """
    Token-based product matcher
    Matches products by counting exact token overlaps
    """

    def __init__(self, products_json: str = "odoo_database/odoo_products.json"):
        """
        Initialize token matcher

        Args:
            products_json: Path to products JSON file
        """
        self.products_json = products_json
        self.products = []

        # Synonym mappings for common variations
        self.synonyms = {
            'blk': 'black',
            'blu': 'blue',
            'wht': 'white',
            'grn': 'green',
            'red': 'red',
            'org': 'orange',
            'gry': 'grey',
            'gray': 'grey',
            'beg': 'beige',
            'sx': 'sx',
            'ak': 'ak',
            'mg': 'mg',
            'cr': 'cr',
            'mm': 'mm',
            'm': 'meter',
            'meters': 'meter',
        }

        logger.info(f"Initializing TokenMatcher with {products_json}")
        self._load_products()

    def _load_products(self):
        """Load products from JSON file"""
        try:
            with open(self.products_json, 'r', encoding='utf-8') as f:
                self.products = json.load(f)
            logger.info(f"Loaded {len(self.products)} products for token matching")
        except Exception as e:
            logger.error(f"Failed to load products: {e}")
            self.products = []

    def _extract_dimensions(self, text: str) -> List[str]:
        """
        Extract dimension patterns from text (e.g., 457x23, 685mm, 760x23mm)

        Args:
            text: Input text

        Returns:
            List of extracted dimension tokens
        """
        dimensions = []

        # Pattern 1: NNNxNN (e.g., 457x23, 760x23)
        patterns_1 = re.findall(r'(\d{2,4})\s*x\s*(\d{1,3})', text.lower())
        for width, height in patterns_1:
            dimensions.append(width)  # Width is most important
            dimensions.append(f"{width}x{height}")  # Also keep full dimension

        # Pattern 2: NNNmm (e.g., 457mm, 685mm)
        patterns_2 = re.findall(r'(\d{2,4})\s*mm', text.lower())
        dimensions.extend(patterns_2)

        # Pattern 3: Standalone numbers 3-4 digits (likely dimensions)
        # But only if we haven't found dimensions yet
        if not dimensions:
            standalone = re.findall(r'\b(\d{3,4})\b', text)
            dimensions.extend(standalone)

        return dimensions

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into normalized alphanumeric tokens
        ENHANCED: Also extracts and prioritizes dimensions

        Args:
            text: Input text

        Returns:
            List of normalized tokens (includes dimensions)
        """
        if not text:
            return []

        # Convert to lowercase
        text = text.lower()

        # Extract dimensions FIRST (priority tokens)
        dimension_tokens = self._extract_dimensions(text)

        # Replace common separators with spaces
        text = re.sub(r'[-_/\\,;]', ' ', text)

        # Extract alphanumeric sequences (words and numbers)
        tokens = re.findall(r'\w+', text)

        # Normalize tokens through synonyms
        normalized = []
        for token in tokens:
            # Apply synonym if exists
            normalized_token = self.synonyms.get(token, token)
            normalized.append(normalized_token)

        # Add dimension tokens at the beginning (higher priority in matching)
        return dimension_tokens + normalized

    def _is_numeric(self, token: str) -> bool:
        """Check if token is numeric (including decimals)"""
        try:
            float(token.replace(',', '.'))
            return True
        except:
            return False

    def _is_product_code(self, token: str) -> bool:
        """Check if token looks like a product code (alphanumeric with separators)"""
        return bool(re.match(r'^[A-Z0-9]+[-_]?[A-Z0-9]*$', token, re.IGNORECASE))

    def _numeric_variations(self, token: str) -> List[str]:
        """
        Generate numeric variations for fuzzy dimension matching

        Examples:
        "007" → ["0.07", "0.007", "7", "07"]
        "457" → ["457", "457.0"]
        "0.20" → ["0.20", "0.2", "20"]
        """
        try:
            num_str = token.replace(',', '.')
            num = float(num_str)

            variations = set()

            # Original
            variations.add(str(num))
            variations.add(token)

            # Common decimal formats
            if num < 1:
                variations.add(f"{num:.2f}")      # 0.07
                variations.add(f"{num:.3f}")      # 0.070
                variations.add(f"{num*10:.2f}")   # 0.7 (decimal shift)
                variations.add(f"{num*100:.1f}")  # 7.0
            else:
                variations.add(f"{num:.0f}")      # Integer
                variations.add(f"{num:.1f}")      # 1 decimal
                variations.add(f"{num/10:.2f}")   # Shift down

            # Remove leading/trailing zeros
            cleaned = num_str.lstrip('0').rstrip('0').rstrip('.')
            if cleaned:
                variations.add(cleaned)

            return list(variations)

        except:
            return [token]

    def _code_variations(self, token: str) -> List[str]:
        """
        Generate code variations while preserving prefix identity

        Examples:
        "E1320-457" → ["e1320-457", "e1320457", "e1320", "457"]
        "RPR-123965" → ["rpr-123965", "rpr123965", "rpr", "123965"]
        "L1920" → ["l1920", "L1920"] (prefix preserved - no numeric stripping)

        CRITICAL: We do NOT generate pure numeric variations for the main token
        to preserve prefix identity (L vs E, RPR vs SDS, etc.)
        """
        variations = set([token, token.upper(), token.lower()])

        # Remove separators (e.g., "E1320-457" → "e1320457")
        variations.add(token.replace('-', '').replace('_', ''))

        # Split on separators and add parts
        parts = re.split(r'[-_]', token)
        if len(parts) > 1:
            # Multi-part code: add each part separately
            for part in parts:
                if part:  # Skip empty parts
                    variations.add(part.lower())

        # DO NOT add numeric-only version of the full token
        # This was causing L1920 and E1920 to both match "1920"

        return list(variations)

    def _normalize_token(self, token: str) -> List[str]:
        """
        Normalize a token and return all possible variations
        This is the CORE of fuzzy matching

        Returns:
            List of normalized variations of this token
        """
        if not token:
            return []

        token_lower = token.lower()
        variations = [token_lower]  # Always include lowercase

        # 1. NUMERIC TOKENS - decimal dimension variations
        if self._is_numeric(token):
            variations.extend(self._numeric_variations(token))

        # 2. PRODUCT CODES - split and normalize
        elif self._is_product_code(token):
            variations.extend(self._code_variations(token))

        # 3. SYNONYMS - apply if exists
        if token_lower in self.synonyms:
            variations.append(self.synonyms[token_lower])

        return list(set(variations))  # Remove duplicates

    def _tokens_match_fuzzy(self, token1: str, token2: str) -> bool:
        """
        Check if two tokens match using fuzzy logic

        Returns True if:
        - Exact match
        - One is in the other's variations
        - Numeric values are close
        """
        # Get all variations
        vars1 = set(self._normalize_token(token1))
        vars2 = set(self._normalize_token(token2))

        # Check for intersection
        if vars1 & vars2:
            return True

        # Numeric tolerance check
        if self._is_numeric(token1) and self._is_numeric(token2):
            try:
                num1 = float(token1.replace(',', '.'))
                num2 = float(token2.replace(',', '.'))

                # Match if very close OR differ by factor of 10 (common error)
                if abs(num1 - num2) < 0.01:
                    return True
                if abs(num1 * 10 - num2) < 0.01:
                    return True
                if abs(num1 - num2 * 10) < 0.01:
                    return True
            except:
                pass

        return False

    def _calculate_token_overlap(self, tokens1: List[str], tokens2: List[str]) -> float:
        """
        Calculate overlap score between two token lists
        ENHANCED: Uses fuzzy matching for dimensions and codes

        Args:
            tokens1: First token list (query tokens)
            tokens2: Second token list (product tokens)

        Returns:
            Overlap score (0.0 to 1.0+, can exceed 1.0 for dimension matches)
        """
        if not tokens1 or not tokens2:
            return 0.0

        # Fuzzy matching: check each token in tokens1 against all tokens in tokens2
        matched_tokens = []
        dimension_bonus = 0.0

        for t1 in tokens1:
            matched = False
            for t2 in tokens2:
                if self._tokens_match_fuzzy(t1, t2):
                    matched_tokens.append(t1)
                    matched = True

                    # BONUS: Check if this is a dimension/numeric match
                    if self._is_numeric(t1) or self._is_numeric(t2):
                        if len(t1) >= 3 or len(t2) >= 3:
                            dimension_bonus += 0.3  # +30% per dimension match
                    elif 'x' in t1 or 'x' in t2:
                        dimension_bonus += 0.4  # +40% for full dimension pattern

                    break  # Move to next t1 token

        # Base score: matched tokens / total query tokens
        base_score = len(matched_tokens) / len(tokens1) if tokens1 else 0.0

        # Final score can exceed 1.0 if dimensions match
        final_score = base_score + dimension_bonus

        return final_score

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.4
    ) -> List[Dict]:
        """
        Search for products using token matching

        Args:
            query: Product name or description to search
            top_k: Number of results to return
            min_score: Minimum overlap score (0.0 to 1.0)

        Returns:
            List of products with overlap scores
        """
        if not query:
            return []

        # Validate product code (reject generic terms)
        is_valid, reason = is_valid_product_code(query)
        if not is_valid:
            logger.warning(f"[VALIDATOR] Rejected query: '{query}' - {reason}")
            return []

        # Tokenize query
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        logger.debug(f"Query tokens: {query_tokens}")

        # Score all products
        scored_products = []

        for product in self.products:
            # Build product text from code and name
            product_text_parts = []

            if product.get('default_code'):
                product_text_parts.append(product['default_code'])

            if product.get('name'):
                product_text_parts.append(product['name'])

            if product.get('display_name'):
                product_text_parts.append(product['display_name'])

            product_text = ' '.join(product_text_parts)
            product_tokens = self._tokenize(product_text)

            # Calculate overlap score
            score = self._calculate_token_overlap(query_tokens, product_tokens)

            if score >= min_score:
                product_copy = product.copy()
                product_copy['similarity_score'] = score
                product_copy['match_method'] = 'token_matching'

                # Add confidence score based on match quality
                match_type = "TOKEN" if score >= 0.75 else "FUZZY"
                product_copy['confidence'] = get_code_confidence(
                    product.get('default_code', ''),
                    match_type
                )

                scored_products.append((score, product_copy))

        # Sort by score (highest first)
        scored_products.sort(reverse=True, key=lambda x: x[0])

        # Return top K
        results = [p for _, p in scored_products[:top_k]]

        if results:
            logger.debug(f"Top match: {results[0].get('default_code')} ({results[0]['similarity_score']:.2%})")

        return results

    def find_top_matches(self, query: str, top_n: int = 10) -> List[Dict]:
        """
        Find top N matching products (wrapper for search with default top_n=10)

        Args:
            query: Product name or description to search
            top_n: Number of top matches to return (default: 10)

        Returns:
            List of top N products with scores
        """
        return self.search(query, top_k=top_n, min_score=0.3)  # Lower threshold to get more candidates

    def search_by_code(self, code: str) -> Optional[Dict]:
        """
        Search for exact product code match

        Args:
            code: Product code to search

        Returns:
            Product dict if found, None otherwise
        """
        if not code:
            return None

        code_upper = code.upper().strip()
        code_lower = code.lower().strip()

        for product in self.products:
            product_code = product.get('default_code', '')

            if not product_code:
                continue

            # Try exact match (case insensitive)
            if product_code.upper() == code_upper or product_code.lower() == code_lower:
                result = product.copy()
                result['similarity_score'] = 1.0
                result['match_method'] = 'exact_code'
                result['confidence'] = get_code_confidence(code, "EXACT")
                return result

        return None
