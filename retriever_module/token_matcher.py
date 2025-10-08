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

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into normalized alphanumeric tokens

        Args:
            text: Input text

        Returns:
            List of normalized tokens
        """
        if not text:
            return []

        # Convert to lowercase
        text = text.lower()

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

        return normalized

    def _calculate_token_overlap(self, tokens1: List[str], tokens2: List[str]) -> float:
        """
        Calculate overlap score between two token lists

        Args:
            tokens1: First token list
            tokens2: Second token list

        Returns:
            Overlap score (0.0 to 1.0)
        """
        if not tokens1 or not tokens2:
            return 0.0

        # Convert to sets for faster lookup
        set1 = set(tokens1)
        set2 = set(tokens2)

        # Count matches
        matches = len(set1 & set2)

        # Score = matches / length of query tokens
        # (We want to know what percentage of the query is matched)
        score = matches / len(set1)

        return score

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
                scored_products.append((score, product_copy))

        # Sort by score (highest first)
        scored_products.sort(reverse=True, key=lambda x: x[0])

        # Return top K
        results = [p for _, p in scored_products[:top_k]]

        if results:
            logger.debug(f"Top match: {results[0].get('default_code')} ({results[0]['similarity_score']:.2%})")

        return results

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
                return result

        return None
