"""
Vector Store Module

Handles JSON-based fuzzy search for customers and products from Odoo exports
"""

import logging
import json
import re
from typing import List, Dict, Optional, Any
from pathlib import Path
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class VectorStore:
    """Class to handle JSON-based customer and product search with fuzzy matching"""

    def __init__(self, customers_json: str = "odoo_database/odoo_customers.json",
                 products_json: str = "odoo_database/odoo_products.json"):
        """
        Initialize Vector Store with JSON files

        Args:
            customers_json: Path to customers JSON file
            products_json: Path to products JSON file
        """
        self.customers_json = customers_json
        self.products_json = products_json
        self.customers_data = []
        self.products_data = []
        self._load_json_files()

    def _load_json_files(self):
        """Load customers and products from JSON files"""
        try:
            # Load customers
            customers_path = Path(self.customers_json)
            if customers_path.exists():
                with open(customers_path, 'r', encoding='utf-8') as f:
                    self.customers_data = json.load(f)
                logger.info(f"✅ Loaded {len(self.customers_data)} customers from {self.customers_json}")
            else:
                logger.warning(f"⚠️  Customers JSON not found: {self.customers_json}")

            # Load products
            products_path = Path(self.products_json)
            if products_path.exists():
                with open(products_path, 'r', encoding='utf-8') as f:
                    self.products_data = json.load(f)
                logger.info(f"✅ Loaded {len(self.products_data)} products from {self.products_json}")
            else:
                logger.warning(f"⚠️  Products JSON not found: {self.products_json}")

        except Exception as e:
            logger.error(f"❌ Error loading JSON files: {str(e)}")
            self.customers_data = []
            self.products_data = []

    def _normalize_search_term(self, term: str) -> List[str]:
        """
        Generate multiple normalized variations for fuzzy matching

        Args:
            term: Search term

        Returns:
            List of normalized variations
        """
        if not term:
            return []

        variations = [term.strip()]  # Always try original first

        # Variation 1: Normalize decimals (comma → period)
        if ',' in term:
            variations.append(term.replace(',', '.'))

        # Variation 2: Remove all spaces (for compact codes)
        no_spaces = term.replace(' ', '')
        if no_spaces != term and len(no_spaces) > 3:
            variations.append(no_spaces)

        # Variation 3: Uppercase
        variations.append(term.upper())

        # Variation 4: Extract key alphanumeric sequences
        key_terms = re.findall(r'\b[A-Z]*[0-9]+[A-Z0-9\-]*\b', term.upper())
        common_words = {'TAPE', 'PEN', 'SEAL', 'BLADE', 'GOLD', 'CARBON', 'METERS', 'DYN', 'MM', 'KG', 'G'}
        for kt in key_terms:
            if len(kt) >= 3 and kt not in common_words:
                variations.append(kt)

        # Variation 5: Extract brand+model patterns
        brand_model = re.findall(r'\b([A-Z0-9]+)\s+([A-Z0-9]+)', term.upper())
        for brand, model in brand_model:
            combined = brand + model
            if len(combined) >= 3:
                variations.append(combined)

        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for v in variations:
            if v and v not in seen:
                seen.add(v)
                unique_variations.append(v)

        return unique_variations

    def _similarity_score(self, str1: str, str2: str) -> float:
        """
        Calculate similarity score between two strings

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not str1 or not str2:
            return 0.0

        # Normalize both strings
        s1 = str1.lower().strip()
        s2 = str2.lower().strip()

        # Exact match
        if s1 == s2:
            return 1.0

        # Substring match
        if s1 in s2 or s2 in s1:
            return 0.9

        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, s1, s2).ratio()

    def search_customer(self, company_name: str = None, customer_name: str = None,
                       email: str = None, threshold: float = 0.6) -> Optional[Dict]:
        """
        Search for customer in JSON data with fuzzy matching

        Args:
            company_name: Company name to search
            customer_name: Customer name to search
            email: Email to search
            threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            Best matching customer dict or None
        """
        logger.info(f"[CUSTOMER SEARCH] Searching: company='{company_name}', name='{customer_name}', email='{email}'")

        if not self.customers_data:
            logger.warning("⚠️  No customer data loaded")
            return None

        best_match = None
        best_score = 0.0

        # Strategy 1: Search by company name (highest priority for B2B)
        if company_name:
            company_variations = self._normalize_search_term(company_name)
            logger.info(f"   Company variations: {company_variations[:3]}")

            for customer in self.customers_data:
                customer_company = customer.get('name', '') or customer.get('commercial_company_name', '')

                for variation in company_variations:
                    score = self._similarity_score(variation, customer_company)
                    if score > best_score:
                        best_score = score
                        best_match = customer

        # Strategy 2: Search by customer name
        if customer_name and best_score < threshold:
            name_variations = self._normalize_search_term(customer_name)
            logger.info(f"   Customer name variations: {name_variations[:3]}")

            for customer in self.customers_data:
                customer_contact = customer.get('name', '')

                for variation in name_variations:
                    score = self._similarity_score(variation, customer_contact)
                    if score > best_score:
                        best_score = score
                        best_match = customer

        # Strategy 3: Search by email (fallback)
        if email and best_score < threshold:
            for customer in self.customers_data:
                customer_email = customer.get('email', '')
                if customer_email and email.lower() in customer_email.lower():
                    best_score = 0.95
                    best_match = customer
                    break

        if best_match and best_score >= threshold:
            logger.info(f"   [MATCH] Customer found: {best_match.get('name')} (Score: {best_score:.0%})")
            logger.info(f"      Location: {best_match.get('city', 'N/A')}, {best_match.get('country_id', ['', 'N/A'])[1] if isinstance(best_match.get('country_id'), list) else 'N/A'}")
            logger.info(f"      Email: {best_match.get('email', 'N/A')}")
            logger.info(f"      Phone: {best_match.get('phone', 'N/A')}")
            logger.info(f"      Ref: {best_match.get('ref', 'N/A')}")
            return {**best_match, 'match_score': best_score}
        else:
            logger.warning(f"   [NO MATCH] No customer found (best score: {best_score:.0%}, threshold: {threshold:.0%})")
            return None

    def search_product(self, product_name: str = None, product_code: str = None,
                      threshold: float = 0.6) -> List[Dict]:
        """
        Search for product in JSON data with fuzzy matching

        Args:
            product_name: Product name to search
            product_code: Product code to search
            threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            List of matching products (sorted by score)
        """
        if not product_name and not product_code:
            return []

        search_term = product_code if product_code else product_name
        logger.debug(f"   Searching product: '{search_term}'")

        if not self.products_data:
            logger.warning("⚠️  No product data loaded")
            return []

        matches = []

        # Generate search variations
        variations = self._normalize_search_term(search_term)

        # Search through all products
        for product in self.products_data:
            product_fields = [
                product.get('name', ''),
                product.get('display_name', ''),
                product.get('default_code', ''),
                product.get('partner_ref', '')
            ]

            best_field_score = 0.0

            for field_value in product_fields:
                if not field_value:
                    continue

                for variation in variations:
                    score = self._similarity_score(variation, str(field_value))
                    best_field_score = max(best_field_score, score)

            if best_field_score >= threshold:
                matches.append({
                    **product,
                    'match_score': best_field_score,
                    'search_term': search_term
                })

        # Sort by score (descending)
        matches.sort(key=lambda x: x['match_score'], reverse=True)

        return matches[:3]  # Return top 3 matches

    def search_products_batch(self, product_names: List[str], product_codes: List[str] = None,
                             threshold: float = 0.6) -> List[Dict]:
        """
        Search for multiple products at once

        Args:
            product_names: List of product names
            product_codes: List of product codes (optional)
            threshold: Minimum similarity score

        Returns:
            List of all matched products
        """
        # Ensure product_codes list is same length as product_names (pad with None)
        if not product_codes:
            product_codes = [None] * len(product_names)
        elif len(product_codes) < len(product_names):
            # Pad with None if codes list is shorter
            product_codes = product_codes + [None] * (len(product_names) - len(product_codes))

        all_matches = []
        match_count = 0

        for idx, (name, code) in enumerate(zip(product_names, product_codes)):
            # Try code first, then name
            search_code = code if code else None
            matches = self.search_product(product_name=name, product_code=search_code, threshold=threshold)

            if matches:
                # Take best match
                best_match = matches[0]
                # Store the original extracted product name for tracking
                best_match['extracted_product_name'] = name
                all_matches.append(best_match)
                match_count += 1
                logger.info(f"   ✓ [{idx+1}/{len(product_names)}] '{name[:50]}' → {best_match.get('name', 'Unknown')[:50]} (Score: {best_match['match_score']:.0%}, Code: {best_match.get('default_code', 'N/A')})")
            else:
                logger.warning(f"   ✗ [{idx+1}/{len(product_names)}] '{name[:50]}' → NO MATCH FOUND")

        match_rate = (match_count / len(product_names) * 100) if product_names else 0
        logger.info(f"\n   📊 SUMMARY: Matched {match_count}/{len(product_names)} products ({match_rate:.0f}%)")

        if match_count < len(product_names):
            logger.warning(f"   ⚠️  {len(product_names) - match_count} product(s) NOT matched in JSON database")

        return all_matches

    def get_stats(self) -> Dict:
        """
        Get vector store statistics

        Returns:
            Statistics dictionary
        """
        return {
            'total_customers': len(self.customers_data),
            'total_products': len(self.products_data),
            'customers_file': self.customers_json,
            'products_file': self.products_json
        }

    def close(self):
        """Cleanup and close vector store"""
        logger.info("Closing JSON-based vector store...")
        # No cleanup needed for JSON files
        pass
