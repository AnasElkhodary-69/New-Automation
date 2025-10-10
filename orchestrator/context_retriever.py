"""
Context Retriever Module

Handles retrieval of context from JSON databases and Odoo
Separated from EmailProcessor for better modularity
"""

import logging
from typing import Dict, List, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.product_validator import is_valid_product_code, validate_product_codes

logger = logging.getLogger(__name__)


class ContextRetriever:
    """Handles context retrieval from JSON and Odoo databases"""

    def __init__(self, vector_store, token_matcher=None, hybrid_matcher=None):
        """
        Initialize Context Retriever

        Args:
            vector_store: VectorStore instance for fallback matching
            token_matcher: TokenMatcher instance for product matching (optional, deprecated)
            hybrid_matcher: HybridMatcher instance for BERT+Token matching (recommended)
        """
        self.vector_store = vector_store

        # Prefer hybrid matcher over token matcher
        if hybrid_matcher is not None:
            self.matcher = hybrid_matcher
            self.use_hybrid_matching = True
            self.use_token_matching = False
            logger.info("   [INIT] Using HybridMatcher (BERT + Token)")
        elif token_matcher is not None:
            self.matcher = token_matcher
            self.use_hybrid_matching = False
            self.use_token_matching = True
            logger.info("   [INIT] Using TokenMatcher only")
        else:
            self.matcher = None
            self.use_hybrid_matching = False
            self.use_token_matching = False
            logger.info("   [INIT] No matcher available, using VectorStore fallback")

        # Keep reference for backward compatibility
        self.token_matcher = token_matcher

    def _extract_dimensions(self, text: str) -> set:
        """Extract dimension numbers from text for validation."""
        import re
        patterns = [
            r'\b(\d{2,4})\s*[xX*]\s*(\d{1,3}(?:[.,]\d{1,2})?)',  # 343x22.85
            r'\b(\d{3,5})\s*mm\b',  # 343mm
        ]
        dimensions = set()
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                for group in match.groups():
                    if group:
                        normalized = group.replace(' ', '').replace(',', '.')
                        # Only keep significant dimensions (width/length, typically 3+ digits)
                        if len(normalized.replace('.', '')) >= 2:
                            dimensions.add(normalized)
        return dimensions

    def _validate_dimension_match(self, query: str, product_text: str) -> bool:
        """
        Validate that dimensions in query match dimensions in product.

        Returns True if:
        - No dimensions in query (nothing to validate)
        - Product has no dimensions in DB (can't validate, accept match)
        - Dimensions in query match dimensions in product

        Returns False if:
        - Dimensions in query DON'T match product dimensions
        """
        query_dims = self._extract_dimensions(query)
        product_dims = self._extract_dimensions(product_text)

        # If no dimensions in query, nothing to validate
        if not query_dims:
            return True

        # If dimensions in query but no dimensions in product, ACCEPT (can't validate)
        if query_dims and not product_dims:
            logger.warning(f"      [DIMENSION MISSING] Product has no dimensions in DB, accepting match anyway")
            return True  # Accept the match - dimensions can't be validated

        # Check if at least one dimension from query matches product
        matches = query_dims & product_dims

        if not matches:
            logger.warning(f"      [DIMENSION MISMATCH] Query dims {query_dims} don't match product dims {product_dims}")
            return False

        logger.info(f"      [DIMENSION OK] Matched dimensions: {matches}")
        return True

    def retrieve_order_context_json(self, entities: Dict) -> Dict:
        """
        Retrieve order-related context from JSON

        Args:
            entities: Extracted entities

        Returns:
            Order context with matched products
        """
        logger.info("   Retrieving order/product context from JSON...")

        order_context = {
            'products': []
        }

        try:
            # Search for products mentioned in order
            product_names = entities.get('product_names', [])
            product_codes = entities.get('product_codes', [])

            if product_names:
                # Validate extracted product codes (reject generic terms)
                products_to_validate = [
                    {'code': code, 'name': product_names[i]}
                    for i, code in enumerate(product_codes) if i < len(product_names)
                ]

                valid_products, invalid_products = validate_product_codes(products_to_validate)

                # Log rejections
                if invalid_products:
                    logger.warning(f"   [VALIDATOR] Rejected {len(invalid_products)} generic terms:")
                    for prod in invalid_products[:5]:  # Show first 5
                        logger.warning(f"      - '{prod['code']}': {prod['rejection_reason']}")

                # Update product lists to only include valid ones
                if valid_products:
                    product_codes = [p['code'] for p in valid_products]
                    product_names = [p['name'] for p in valid_products]
                else:
                    # All products were invalid
                    logger.warning(f"   [VALIDATOR] All extracted products were generic terms")
                    return order_context

                logger.info(f"   [SEARCH] Searching {len(product_names)} products...")

                if self.use_token_matching or self.use_hybrid_matching:
                    # HYBRID MATCHING: Always use full product name with dimensions for accurate matching
                    matched_products = []
                    for i, product_name in enumerate(product_names):
                        product_code = product_codes[i] if i < len(product_codes) else None
                        match = None

                        # Build search query: Always include product name (with dimensions)
                        # If code exists, prepend it to query
                        query = product_name
                        if product_code:
                            query = f"{product_code} {product_name}"

                        # STRATEGY 1: Try exact code lookup (only if no dimensions in product name)
                        # Skip exact code lookup if dimensions are present - they must be validated
                        import re
                        has_dimensions = bool(re.search(r'\d{2,4}\s*[xX*]\s*\d{1,3}', product_name))

                        if product_code and not has_dimensions:
                            match = self.matcher.search_by_code(product_code)

                            if match:
                                # Exact code match found (no dimensions to validate)
                                match['match_score'] = 1.0  # 100% confidence for exact code
                                match['match_method'] = 'exact_code'
                                match['extracted_product_name'] = product_name
                                match['requires_review'] = False
                                logger.info(f"      [{i+1}] {product_code} [EXACT] (100%)")

                        # STRATEGY 2: Hybrid/Token matching with dimension validation
                        if not match:
                            # Search using matcher (hybrid or token)
                            # Lowered threshold to 0.60 to match BERT semantic threshold
                            results = self.matcher.search(query, top_k=1, min_score=0.60)

                            if results:
                                candidate = results[0]

                                # CRITICAL: Validate dimensions before accepting match
                                product_text = f"{candidate.get('default_code', '')} {candidate.get('product_code', '')} {candidate.get('product_name', '')}"
                                dimension_valid = self._validate_dimension_match(query, product_text)

                                if dimension_valid:
                                    match = candidate
                                    # Get score (different field names for hybrid vs token)
                                    score = match.get('final_score') or match.get('similarity_score', 0)

                                    # Add metadata for downstream processing
                                    match['match_score'] = score
                                    if self.use_hybrid_matching:
                                        match['match_method'] = 'hybrid_bert_token'
                                    else:
                                        match['match_method'] = 'token_matching'
                                    match['extracted_product_name'] = product_name
                                    match['requires_review'] = score < 0.80

                                    # Log result with confidence level
                                    code = match.get('default_code') or match.get('product_code', 'N/A')
                                    method_label = 'HYBRID' if self.use_hybrid_matching else 'TOKEN'

                                    if score >= 0.80:
                                        logger.info(f"      [{i+1}] {code} [{method_label}] ({score:.0%})")
                                    elif score >= 0.60:
                                        logger.info(f"      [{i+1}] {code} [REVIEW] ({score:.0%})")
                                    else:
                                        logger.warning(f"      [{i+1}] {code} [MANUAL] ({score:.0%})")
                                else:
                                    # Dimension mismatch - REJECT this match
                                    logger.warning(f"      [{i+1}] REJECTED match {candidate.get('default_code', 'N/A')} - dimension mismatch")

                        if match:
                            matched_products.append(match)
                        else:
                            logger.warning(f"      [{i+1}] NO MATCH for '{product_name[:40]}'")
                else:
                    # Fallback to VectorStore fuzzy matching
                    logger.info(f"   [!] Using VectorStore fallback (Token Matcher unavailable)")
                    matched_products = self.vector_store.search_products_batch(
                        product_names=product_names,
                        product_codes=product_codes,
                        threshold=0.6
                    )

                order_context['products'] = matched_products
                logger.info(f"   [OK] Product search complete: {len(matched_products)} matches found")

        except Exception as e:
            logger.error(f"   [ERROR] Error retrieving order context: {e}")

        return order_context

    def retrieve_invoice_context_json(self, entities: Dict) -> Dict:
        """
        Retrieve invoice-related context from JSON

        Args:
            entities: Extracted entities

        Returns:
            Invoice context
        """
        logger.info("   Retrieving invoice context from JSON...")

        invoice_context = {
            'invoices': [],
            'customer': None
        }

        try:
            # Search for customer
            customer_search = entities.get('company_name') or entities.get('customer_name')
            if customer_search:
                customer_result = self.vector_store.search_customer(customer_search, threshold=0.7)
                if customer_result:
                    invoice_context['customer'] = customer_result
                    logger.info(f"   [OK] Customer found: {customer_result.get('name')}")

            # Search for invoice by reference
            references = entities.get('references', [])
            if references:
                # TODO: Implement invoice search by reference
                logger.info(f"   [INFO] Invoice search by reference not implemented yet")

        except Exception as e:
            logger.error(f"   [ERROR] Error retrieving invoice context: {e}")

        return invoice_context

    def retrieve_product_context_json(self, entities: Dict) -> Dict:
        """
        Retrieve product inquiry context from JSON

        Args:
            entities: Extracted entities

        Returns:
            Product context
        """
        logger.info("   Retrieving product inquiry context from JSON...")

        product_context = {
            'products': []
        }

        try:
            product_names = entities.get('product_names', [])
            product_codes = entities.get('product_codes', [])

            if product_names:
                if self.use_token_matching or self.use_hybrid_matching:
                    # Use hybrid/token matching
                    matched_products = []
                    for i, product_name in enumerate(product_names):
                        product_code = product_codes[i] if i < len(product_codes) else None

                        if product_code:
                            match = self.matcher.search_by_code(product_code)
                            if match:
                                match['match_score'] = match.get('final_score') or match.get('similarity_score') or 1.0
                                match['match_method'] = 'exact_code'
                                matched_products.append(match)
                                continue

                        # Try hybrid/token matching
                        query = product_name
                        if product_code:
                            query = f"{product_code} {product_name}"

                        # Lowered threshold to 0.60 to match BERT semantic threshold
                        results = self.matcher.search(query, top_k=3, min_score=0.60)
                        matched_products.extend(results)
                else:
                    # Fallback to VectorStore
                    matched_products = self.vector_store.search_products_batch(
                        product_names=product_names,
                        product_codes=product_codes,
                        threshold=0.5,
                        top_k=3
                    )

                product_context['products'] = matched_products
                logger.info(f"   [OK] Found {len(matched_products)} product matches")

        except Exception as e:
            logger.error(f"   [ERROR] Error retrieving product context: {e}")

        return product_context

    def retrieve_context(self, intent: Dict, entities: Dict, email: Dict) -> Dict:
        """
        Retrieve relevant context from JSON files (main entry point)

        Args:
            intent: Intent classification result
            entities: Extracted entities
            email: Original email data

        Returns:
            Retrieved context based on intent
        """
        intent_type = intent.get('type', 'unknown')

        context = {
            'customer_info': None,
            'json_data': {}
        }

        try:
            # Always try to find customer first
            customer_search = entities.get('company_name') or entities.get('customer_name')
            if customer_search:
                logger.info(f"   Searching for customer: '{customer_search}'...")
                customer_result = self.vector_store.search_customer(customer_search, threshold=0.6)
                if customer_result:
                    context['customer_info'] = customer_result
                    logger.info(f"   [OK] Customer found: {customer_result.get('name')} (score: {customer_result.get('match_score', 0):.0%})")
                else:
                    logger.warning(f"   [!] Customer not found in database")

            # Retrieve intent-specific context
            if intent_type == 'order_inquiry':
                context['json_data'] = self.retrieve_order_context_json(entities)
            elif intent_type == 'invoice_inquiry':
                context['json_data'] = self.retrieve_invoice_context_json(entities)
            elif intent_type == 'product_inquiry':
                context['json_data'] = self.retrieve_product_context_json(entities)
            else:
                logger.info(f"   [INFO] No specific context retrieval for intent: {intent_type}")

        except Exception as e:
            logger.error(f"   [ERROR] Error in context retrieval: {e}")

        return context
