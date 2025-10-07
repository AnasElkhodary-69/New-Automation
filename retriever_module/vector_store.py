"""
Vector Store Module

Handles JSON-based fuzzy search for customers and products from Odoo exports
Implements multi-level product matching strategy for production B2B orders
"""

import logging
import json
import re
import os
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class VectorStore:
    """Class to handle JSON-based customer and product search with robust multi-level matching"""

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

        # Load matching thresholds from environment or use defaults
        self.code_exact_threshold = float(os.getenv('PRODUCT_CODE_EXACT_THRESHOLD', '1.0'))
        self.code_fuzzy_threshold = float(os.getenv('PRODUCT_CODE_FUZZY_THRESHOLD', '0.90'))
        self.attribute_threshold = float(os.getenv('PRODUCT_ATTRIBUTE_THRESHOLD', '0.80'))
        self.name_threshold = float(os.getenv('PRODUCT_NAME_THRESHOLD', '0.85'))
        self.auto_approve_threshold = float(os.getenv('PRODUCT_AUTO_APPROVE_THRESHOLD', '0.95'))
        self.review_threshold = float(os.getenv('PRODUCT_REVIEW_THRESHOLD', '0.70'))

        self._load_json_files()

    def _load_json_files(self):
        """Load customers and products from JSON files"""
        try:
            # Load customers
            customers_path = Path(self.customers_json)
            if customers_path.exists():
                with open(customers_path, 'r', encoding='utf-8') as f:
                    self.customers_data = json.load(f)
                logger.info(f"[OK] Loaded {len(self.customers_data)} customers from {self.customers_json}")
            else:
                logger.warning(f"[!] Customers JSON not found: {self.customers_json}")

            # Load products
            products_path = Path(self.products_json)
            if products_path.exists():
                with open(products_path, 'r', encoding='utf-8') as f:
                    self.products_data = json.load(f)
                logger.info(f"[OK] Loaded {len(self.products_data)} products from {self.products_json}")
            else:
                logger.warning(f"[!] Products JSON not found: {self.products_json}")

        except Exception as e:
            logger.error(f"[ERROR] Error loading JSON files: {str(e)}")
            self.customers_data = []
            self.products_data = []

    def is_supplier_code(self, code: str) -> bool:
        """
        Check if a code matches supplier code patterns (vs customer internal codes)

        Supplier codes: SDS###, L####, E####, 3M L###, etc.
        Customer codes: KB-WK-MW-*, MW-*, etc. (should be ignored)

        Args:
            code: Product code to validate

        Returns:
            True if this looks like a supplier code, False if customer code
        """
        if not code:
            return False

        code_upper = code.upper().strip()

        # Customer code patterns (REJECT these)
        customer_patterns = [
            r'^KB[-_]',      # KB-WK-MW-B3
            r'^MW[-_]',      # MW-*
            r'^WK[-_]',      # WK-*
            r'^ART[-_]',     # ART-*
            r'^CUST[-_]',    # CUST-*
        ]

        for pattern in customer_patterns:
            if re.match(pattern, code_upper):
                return False

        # Supplier code patterns (ACCEPT these)
        supplier_patterns = [
            r'^SDS\s*\d',           # SDS 06, SDS006, SDS1235
            r'^[3]M\s*[EL]\d',      # 3M L1020, 3M E1020
            r'^[EL]\d{3,4}',        # L1020, E1320
            r'^\d{3,6}[-_]\d',      # 444-444-159, 105092-377
        ]

        for pattern in supplier_patterns:
            if re.match(pattern, code_upper):
                return True

        # If code has letters + numbers and no dashes (normalized), accept it
        if re.match(r'^[A-Z]+\d+[A-Z]?$', code_upper.replace('-', '').replace('_', '').replace(' ', '')):
            return True

        return False

    def normalize_code(self, code: str) -> str:
        """
        Normalize product code for matching

        Handles: spaces, dashes, underscores, case differences, brand prefixes
        Example: "SDS 025" → "SDS025", "SDS-025" → "SDS025"
                 "3M L1020 685" → "L1020685"

        Args:
            code: Product code to normalize

        Returns:
            Normalized code (uppercase, no spaces/dashes, no brand prefixes)
        """
        if not code:
            return ""

        # Convert to uppercase and trim
        normalized = code.upper().strip()

        # Remove common brand prefixes
        brand_prefixes = ['3M ', 'TESA ', 'DUPONT ', 'NITTO ', 'LOHMANN ']
        for brand in brand_prefixes:
            if normalized.startswith(brand):
                normalized = normalized[len(brand):]
                break

        # Remove spaces, dashes, underscores
        normalized = re.sub(r'[\s\-_]', '', normalized)

        return normalized

    def normalize_code_variants(self, code: str) -> List[str]:
        """
        Generate multiple normalized variants of a code for better matching

        Args:
            code: Product code to normalize

        Returns:
            List of normalized variants
        """
        if not code:
            return []

        variants = []

        # Variant 1: Full normalization (no brand, no separators)
        variants.append(self.normalize_code(code))

        # Variant 2: Normalized without brand removal (keep brand but remove separators)
        normalized_with_brand = re.sub(r'[\s\-_]', '', code.upper().strip())
        if normalized_with_brand != variants[0]:
            variants.append(normalized_with_brand)

        # Variant 3: Original uppercase (preserve separators)
        original_upper = code.upper().strip()
        if original_upper not in variants:
            variants.append(original_upper)

        return list(set(variants))  # Remove duplicates

    def extract_dimension_from_name(self, product_name: str) -> Optional[str]:
        """
        Extract primary dimension (width) from product name

        Examples:
            "3M L1020 CushionMount plus 685mm" → "685"
            "Doctor Blade 25x0.20mm" → "25"
            "Tape 1372mm x 23m" → "1372"

        Args:
            product_name: Product name to extract dimension from

        Returns:
            Dimension string (without 'mm') or None if not found
        """
        if not product_name:
            return None

        # Pattern 1: Dimension followed by 'mm' (most common)
        # Examples: 685mm, 1372mm, 780mm
        match = re.search(r'(\d+)mm', product_name, re.IGNORECASE)
        if match:
            return match.group(1)

        # Pattern 2: Dimension with 'x' separator (width x length)
        # Examples: 1372mm x 23m, 25x0.20
        match = re.search(r'(\d+)\s*[xX×]\s*\d+', product_name)
        if match:
            return match.group(1)

        return None

    def build_code_with_dimension(self, base_code: str, product_name: str) -> List[str]:
        """
        Build possible product codes by combining base code with dimension from name

        Args:
            base_code: Base product code (e.g., "3M L1020 685", "L1020")
            product_name: Product name (e.g., "3M L1020 CushionMount plus 685mm")

        Returns:
            List of possible codes to try
        """
        codes = []

        # Add original code
        if base_code:
            codes.append(base_code)

        # Extract dimension from product name
        dimension = self.extract_dimension_from_name(product_name)

        if dimension and base_code:
            # Normalize base code
            normalized_base = self.normalize_code(base_code)

            # Remove any trailing digits from base code (they might be old dimension)
            base_without_digits = re.sub(r'\d+$', '', normalized_base)

            # Build code with dimension
            # Format: BASE-DIMENSION (e.g., L1020-685)
            code_with_dimension = f"{base_without_digits}-{dimension}"
            codes.append(code_with_dimension)

            # Also try without dash
            code_with_dimension_nodash = f"{base_without_digits}{dimension}"
            codes.append(code_with_dimension_nodash)

        return codes

    def extract_attributes(self, text: str) -> Dict[str, Any]:
        """
        Extract measurable product attributes from text

        Extracts: dimensions, colors, materials, brands, machine types

        Args:
            text: Product name or description

        Returns:
            Dictionary of extracted attributes
        """
        if not text:
            return {}

        text_upper = text.upper()
        attributes = {}

        # Extract dimensions (width, thickness, length)
        # Patterns: 25mm, 0.20mm, 600x23m, etc.
        width_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:MM|X)', text_upper)
        if width_match:
            attributes['width'] = width_match.group(1).replace(',', '.')

        thickness_match = re.search(r'(\d+[.,]\d+)\s*(?:MM)?', text)
        if thickness_match and ('.' in thickness_match.group(1) or ',' in thickness_match.group(1)):
            attributes['thickness'] = thickness_match.group(1).replace(',', '.')

        dimension_match = re.search(r'(\d+)\s*[Xx]\s*(\d+)', text)
        if dimension_match:
            attributes['dimensions'] = f"{dimension_match.group(1)}x{dimension_match.group(2)}"

        # Extract colors
        color_pattern = r'\b(GOLD|GOLDEN|SILVER|GREY|GRAY|BLACK|WHITE|BLUE|RED|GREEN|YELLOW|ORANGE)\b'
        color_match = re.search(color_pattern, text_upper)
        if color_match:
            attributes['color'] = color_match.group(1)

        # Extract materials
        material_pattern = r'\b(CARBON|STEEL|POLYESTER|ALUMINUM|PLASTIC|RUBBER|FOAM)\b'
        material_match = re.search(material_pattern, text_upper)
        if material_match:
            attributes['material'] = material_match.group(1)

        # Extract machine types
        machine_pattern = r'\b(BOBST|HEIDELBERG|KOMORI|ROLAND|MANROLAND|KBA)\b'
        machine_match = re.search(machine_pattern, text_upper)
        if machine_match:
            attributes['machine'] = machine_match.group(1)

        # Extract brands
        brand_pattern = r'\b(3M|TESA|DUPONT|NITTO|LOHMANN|ADHESIVE)\b'
        brand_match = re.search(brand_pattern, text_upper)
        if brand_match:
            attributes['brand'] = brand_match.group(1)

        # Extract product type keywords
        type_keywords = ['BLADE', 'TAPE', 'SEAL', 'CUSHION', 'MOUNT', 'DOCTOR', 'ADHESIVE']
        attributes['types'] = [kw for kw in type_keywords if kw in text_upper]

        return attributes

    def _calculate_attribute_similarity(self, attrs1: Dict, attrs2: Dict) -> float:
        """
        Calculate similarity between two attribute dictionaries

        Args:
            attrs1: First attribute dict
            attrs2: Second attribute dict

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not attrs1 or not attrs2:
            return 0.0

        matching_attributes = 0
        total_attributes = 0

        # Check exact matches for key attributes
        for key in ['width', 'thickness', 'color', 'material', 'machine', 'brand']:
            if key in attrs1 and key in attrs2:
                total_attributes += 1
                if attrs1[key] == attrs2[key]:
                    matching_attributes += 1

        # Check type overlap
        if 'types' in attrs1 and 'types' in attrs2:
            types1 = set(attrs1['types'])
            types2 = set(attrs2['types'])
            if types1 and types2:
                total_attributes += 1
                overlap = len(types1 & types2) / max(len(types1), len(types2))
                if overlap > 0.5:
                    matching_attributes += overlap

        if total_attributes == 0:
            return 0.0

        return matching_attributes / total_attributes

    def _calculate_similarity_safe(self, str1: str, str2: str) -> float:
        """
        Calculate similarity score between two strings (SAFE - no dangerous substring logic)

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

        # Check length difference - if too different, penalize
        len_diff = abs(len(s1) - len(s2)) / max(len(s1), len(s2))
        if len_diff > 0.5:
            # Lengths differ by more than 50% - unlikely to be same product
            return SequenceMatcher(None, s1, s2).ratio() * 0.7

        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, s1, s2).ratio()

    def _extract_components(self, product_name: str) -> Dict:
        """
        Extract key components from product name for matching

        Components:
        - Brand: 3M, SDS, TESA, etc.
        - Model/Code: L1020, E1320, SDS006, etc.
        - Dimensions: 685mm, 780mm, 25x020, etc.
        - Type: CushionMount, Doctor Blade, Seal, etc.
        - Colors: GRY, BLK, RED, etc.
        """
        components = {
            'brand': None,
            'model': None,
            'dimensions': [],
            'type': None,
            'colors': []
        }

        text = product_name.upper()

        # Extract Brand
        brands = ['3M', 'SDS', 'TESA', 'DUPONT', 'NITTO', 'LOHMANN']
        for brand in brands:
            if brand in text:
                components['brand'] = brand
                break

        # Extract Model/Code (alphanumeric codes)
        model_patterns = [
            r'\b(\d{3}-\d{2}-[A-Z])\b',     # 904-12-G, 928-12-K (3M tape codes)
            r'\b([EL]\d{3,4})\b',           # E1020, L1020
            r'\bSDS\s*(\d{2,4}[A-Z]?)\b',   # SDS006, SDS 06, SDS1235A
            r'\b([A-Z]-\d{2,4}-\d{2,4})\b', # C-40-20-RPE
        ]
        for pattern in model_patterns:
            match = re.search(pattern, text)
            if match:
                components['model'] = match.group(1) if len(match.groups()) > 0 else match.group(0)
                break

        # Extract Dimensions (numbers with mm, x separator, or standalone)
        dimension_patterns = [
            r'(\d+)\s*MM',              # 685mm
            r'(\d+)\s*X\s*(\d+)',       # 25x020
            r'\b(\d{3,4})\b',           # 685, 780 (standalone numbers)
        ]
        for pattern in dimension_patterns:
            matches = re.findall(pattern, text)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        components['dimensions'].extend([d for d in match if d])
                    else:
                        components['dimensions'].append(match)

        # Extract Type keywords
        type_keywords = ['CUSHION', 'MOUNT', 'DOCTOR', 'BLADE', 'SEAL', 'TAPE', 'FOAM']
        found_types = [kw for kw in type_keywords if kw in text]
        if found_types:
            components['type'] = ' '.join(found_types)

        # Extract Colors
        colors = ['GRY', 'GREY', 'BLK', 'BLACK', 'RED', 'BLUE', 'BLU', 'WHT', 'WHITE', 'YLL', 'YELLOW', 'GRAU']
        for color in colors:
            if color in text:
                components['colors'].append(color)

        return components

    def _match_by_full_name(self, product_name: str) -> Dict:
        """
        Match product by comparing KEY COMPONENTS (brand, model, dimensions)

        Example:
        Input:  "3M L1020 CushionMount plus 685mm PLATTENKLEBEBAND"
        Components: Brand=3M, Model=L1020, Dim=685, Type=CUSHION MOUNT

        Match:  "3MCushion Mount plus L1020 685mm x 23m"
        Components: Brand=3M, Model=L1020, Dim=685, Type=CUSHION MOUNT

        Score: 100% (all key components match!)

        Args:
            product_name: Full product name from extraction

        Returns:
            Match result dict if good match found, None otherwise
        """
        if not product_name or not self.products_data:
            return None

        # Extract components from search string
        search_components = self._extract_components(product_name)

        best_match = None
        best_score = 0.0
        best_details = ""

        for product in self.products_data:
            db_name = product.get('name', '')
            if not db_name:
                continue

            # Extract components from database name
            db_components = self._extract_components(db_name)

            # Calculate component-based score
            score = 0.0
            max_score = 0.0
            details = []

            # Brand matching (30 points)
            max_score += 30
            if search_components['brand'] and db_components['brand']:
                if search_components['brand'] == db_components['brand']:
                    score += 30
                    details.append(f"Brand[OK]")
                else:
                    details.append(f"Brand[X]")

            # Model matching (40 points - MOST IMPORTANT)
            max_score += 40
            if search_components['model'] and db_components['model']:
                # Normalize models for comparison
                search_model = search_components['model'].replace(' ', '').replace('-', '')
                db_model = db_components['model'].replace(' ', '').replace('-', '')
                if search_model == db_model or search_model in db_model or db_model in search_model:
                    score += 40
                    details.append(f"Model[OK]")
                else:
                    details.append(f"Model[X]")

            # Dimension matching (25 points)
            max_score += 25
            if search_components['dimensions'] and db_components['dimensions']:
                # Check if any dimension matches
                matched_dims = set(search_components['dimensions']) & set(db_components['dimensions'])
                if matched_dims:
                    score += 25
                    details.append(f"Dim[OK]({','.join(matched_dims)})")
                else:
                    details.append(f"Dim[X]")

            # Type matching (5 points - bonus)
            max_score += 5
            if search_components['type'] and db_components['type']:
                # Check if types overlap
                if any(word in db_components['type'] for word in search_components['type'].split()):
                    score += 5
                    details.append(f"Type[OK]")

            # Calculate final percentage
            if max_score > 0:
                final_score = score / max_score
            else:
                final_score = 0.0

            if final_score > best_score:
                best_score = final_score
                best_match = product
                best_details = ' '.join(details)

        # Log best match found
        if best_match:
            logger.info(f"   [NAME_MATCH] Best: {best_match.get('default_code')} - '{best_match.get('name')}' (score: {best_score:.0%}, {best_details})")

        # Return match if confidence is high enough
        if best_match and best_score >= 0.80:  # 80% threshold - need strong component match
            logger.info(f"   [NAME_MATCH] [OK] MATCHED!")
            return {
                'match': best_match,
                'confidence': best_score,
                'method': 'full_name_match',
                'requires_review': best_score < 0.90,
                'candidates': [],
                'search_input': {
                    'product_name': product_name,
                    'product_code': None
                }
            }

        logger.info(f"   [NAME_MATCH] Score below threshold (80%), continuing...")
        return None

    def search_product_multilevel(self, product_name: str = None, product_code: str = None) -> Dict:
        """
        Multi-level product search with confidence scoring

        Levels:
        1. Exact code match (100% confidence)
        2. Fuzzy code match (90-95% confidence)
        3. Attribute-based match (80-90% confidence)
        4. Name similarity match (70-85% confidence)
        5. No match (requires manual review)

        Args:
            product_name: Product name from email
            product_code: Product code from email (if available)

        Returns:
            Match result with confidence score and method
        """
        result = {
            'match': None,
            'confidence': 0.0,
            'method': 'no_match',
            'requires_review': True,
            'candidates': [],
            'search_input': {
                'product_name': product_name,
                'product_code': product_code
            }
        }

        if not self.products_data:
            logger.warning("[!] No product data loaded")
            return result

        # NEW APPROACH: Use full name matching FIRST
        # Extract: "3M L1020 CushionMount plus 685mm PLATTENKLEBEBAND"
        # Database: "3MCushion Mount plus L1020 685mm x 23m"
        # These should match directly!

        # PRIORITY 1: Direct name-based matching
        if product_name:
            logger.info(f"   [P1] Searching by full product name...")
            name_match = self._match_by_full_name(product_name)
            if name_match:
                return name_match

        # PRIORITY 2: Use supplier code if provided
        code_to_use = product_code
        if product_code and self.is_supplier_code(product_code):
            logger.info(f"   [P2] Using supplier code: '{product_code}'")
            code_to_use = product_code
        elif product_code:
            logger.info(f"   [P3] Customer code detected ('{product_code}'), extracting from name instead...")
            code_to_use = None

        # PRIORITY 3: Extract code from product name as fallback
        if not code_to_use and product_name:
            code_patterns = [
                r'\b(\d{3}-\d{2}-[A-Z])\b',              # 904-12-G, 928-12-K (3M tape codes)
                r'\b([A-Z]-\d{2,4}-\d{2,4}-[A-Z]+)\b',   # C-40-20-RPE
                r'\b(3M\s+[A-Z]?\d{3,4})\b',             # 3M L1520
                r'\b([A-Z]+\d{3,4}[A-Z]?)\b',            # SDS025
                r'\b([A-Z]-\d{2,4}-\d{2,4})\b',          # G-25-20-125
            ]

            for pattern in code_patterns:
                match = re.search(pattern, product_name.upper())
                if match:
                    extracted_code = match.group(1).replace(' ', '')

                    # Special handling: If we extracted a 3-digit code like "904-12-G" from a 3M product,
                    # prepend "3M" to make it "3M904-12-G" to match database codes like "3M904-12-44"
                    if re.match(r'^\d{3}-\d{2}-[A-Z]$', extracted_code) and '3M' in product_name.upper():
                        extracted_code = '3M' + extracted_code
                        logger.info(f"   [L0] Code extracted from 3M product: '{extracted_code}'")
                    else:
                        logger.info(f"   [L0] Code extracted from name: '{extracted_code}'")

                    code_to_use = extracted_code
                    break

        product_code = code_to_use

        # LEVEL 1: Exact Product Code Match (with attribute refinement for variants)
        if product_code:
            normalized_search_code = self.normalize_code(product_code)
            logger.debug(f"   [L1] Exact code search: '{normalized_search_code}'")

            code_matches = []
            for product in self.products_data:
                db_code = self.normalize_code(product.get('default_code', ''))
                if db_code and db_code == normalized_search_code:
                    code_matches.append(product)

            # If single match, return it
            if len(code_matches) == 1:
                result['match'] = code_matches[0]
                result['confidence'] = 1.0
                result['method'] = 'exact_code'
                result['requires_review'] = False
                logger.info(f"   [L1] [OK] Exact code match: {code_matches[0].get('default_code')} ({result['confidence']:.0%})")
                return result

            # If multiple matches (variants), use attributes to select best one
            elif len(code_matches) > 1 and product_name:
                logger.debug(f"   [L1] Found {len(code_matches)} variants, using attributes to refine...")
                search_attrs = self.extract_attributes(product_name)

                if search_attrs:
                    best_variant = None
                    best_attr_score = 0.0

                    for product in code_matches:
                        product_text = f"{product.get('name', '')} {product.get('display_name', '')}"
                        product_attrs = self.extract_attributes(product_text)
                        attr_score = self._calculate_attribute_similarity(search_attrs, product_attrs)

                        if attr_score > best_attr_score:
                            best_attr_score = attr_score
                            best_variant = product

                    # Use the variant with best attribute match
                    if best_variant and best_attr_score >= 0.5:  # At least 50% attribute match
                        result['match'] = best_variant
                        result['confidence'] = 1.0
                        result['method'] = 'exact_code_with_attributes'
                        result['requires_review'] = False
                        logger.info(f"   [L1] [OK] Exact code match (variant refined by attributes): {best_variant.get('default_code')} (attr: {best_attr_score:.0%})")
                        return result
                    elif best_variant:
                        # Use best variant even with low attribute match
                        result['match'] = best_variant
                        result['confidence'] = 0.95
                        result['method'] = 'exact_code_low_attr'
                        result['requires_review'] = True
                        logger.info(f"   [L1] [!] Exact code match (low attr confidence): {best_variant.get('default_code')} (attr: {best_attr_score:.0%})")
                        return result

                # No attributes or no good match - return first variant
                result['match'] = code_matches[0]
                result['confidence'] = 0.90
                result['method'] = 'exact_code_first_variant'
                result['requires_review'] = True
                logger.info(f"   [L1] [!] Exact code match (first variant, no attribute match): {code_matches[0].get('default_code')}")
                return result

        # LEVEL 1.5: Base Code Match (for product variants)
        # If exact code didn't match, try matching as base code
        if product_code:
            # Special case: 3M tape codes like "3M904-12-G" → base "3M904-12"
            # Check BEFORE normalization because normalization removes "3M" prefix and dashes
            three_m_tape_match = re.match(r'^(3M\d{3}-\d{2})', product_code.upper())
            if three_m_tape_match:
                base_code = three_m_tape_match.group(1)
                base_codes_to_try = [base_code]
                logger.info(f"   [L1.5] 3M tape base code search: {base_codes_to_try}")

                # Find all products that start with this base code
                variant_matches = []
                for product in self.products_data:
                    db_code = product.get('default_code', '')
                    if isinstance(db_code, str) and db_code.upper().startswith(base_code):
                        variant_matches.append(product)

                if len(variant_matches) > 0:
                    logger.info(f"   [L1.5] Found {len(variant_matches)} 3M tape variants for base code {base_code}")

                    # Use attributes to select best variant if multiple matches
                    if product_name and len(variant_matches) > 1:
                        search_attrs = self.extract_attributes(product_name)
                        best_variant = None
                        best_score = 0.0

                        for product in variant_matches:
                            product_text = f"{product.get('name', '')} {product.get('display_name', '')}"
                            product_attrs = self.extract_attributes(product_text)
                            attr_score = self._calculate_attribute_similarity(search_attrs, product_attrs)

                            if attr_score > best_score:
                                best_score = attr_score
                                best_variant = product

                        if best_variant:
                            result['match'] = best_variant
                            result['confidence'] = 0.85 + (best_score * 0.15)  # 85-100%
                            result['method'] = '3m_base_code_variant'
                            result['requires_review'] = best_score < 0.7
                            logger.info(f"   [L1.5] [OK] 3M base code variant: {best_variant.get('default_code')} (attr: {best_score:.0%})")
                            return result

                    # Single variant or no attribute matching
                    if len(variant_matches) == 1:
                        result['match'] = variant_matches[0]
                        result['confidence'] = 0.95
                        result['method'] = '3m_base_code_single'
                        result['requires_review'] = False
                        logger.info(f"   [L1.5] [OK] 3M base code single variant: {variant_matches[0].get('default_code')}")
                        return result
                    elif len(variant_matches) > 1:
                        # Return first variant if no good attribute match
                        result['match'] = variant_matches[0]
                        result['confidence'] = 0.80
                        result['method'] = '3m_base_code_first'
                        result['requires_review'] = True
                        logger.info(f"   [L1.5] [!] 3M base code first variant: {variant_matches[0].get('default_code')}")
                        return result

            # Continue with standard normalization for other code types (non-3M tape codes)
            normalized_search_code = self.normalize_code(product_code)

            # Extract base code for standard format (e.g., SDS025 from SDS025A, SDS06 from SDS006A)
            base_code_match = re.match(r'^([A-Z]+)(\d{2,})', normalized_search_code)
            if base_code_match:
                letters = base_code_match.group(1)
                digits = base_code_match.group(2)

                # Try with and without leading zero (SDS06 → try both SDS06 and SDS006)
                base_codes_to_try = [letters + digits]
                if len(digits) == 2:
                    base_codes_to_try.append(letters + '0' + digits)  # Add leading zero

                logger.debug(f"   [L1.5] Base code variant search: {base_codes_to_try}")

                # Find all products that start with any of these base codes
                variant_matches = []
                for product in self.products_data:
                    db_code = self.normalize_code(product.get('default_code', ''))
                    if db_code:
                        for base_code in base_codes_to_try:
                            if db_code.startswith(base_code):
                                variant_matches.append(product)
                                break  # Don't add same product twice

                if len(variant_matches) > 0:
                    logger.info(f"   [L1.5] Found {len(variant_matches)} variants for base codes {base_codes_to_try}")

                    # Use attributes to select best variant
                    if product_name and len(variant_matches) > 1:
                        search_attrs = self.extract_attributes(product_name)

                        best_variant = None
                        best_score = 0.0

                        for product in variant_matches:
                            product_text = f"{product.get('name', '')} {product.get('display_name', '')}"
                            product_attrs = self.extract_attributes(product_text)
                            attr_score = self._calculate_attribute_similarity(search_attrs, product_attrs)

                            if attr_score > best_score:
                                best_score = attr_score
                                best_variant = product

                        if best_variant and best_score >= 0.4:  # Lower threshold for variants
                            result['match'] = best_variant
                            result['confidence'] = 0.85 + (best_score * 0.15)  # 85-100%
                            result['method'] = 'base_code_variant'
                            result['requires_review'] = best_score < 0.7
                            logger.info(f"   [L1.5] [OK] Base code variant match: {best_variant.get('default_code')} (attr: {best_score:.0%})")
                            return result

                    # If only one variant or no good attribute match, return first variant
                    if len(variant_matches) == 1:
                        result['match'] = variant_matches[0]
                        result['confidence'] = 0.95
                        result['method'] = 'base_code_single'
                        result['requires_review'] = False
                        logger.info(f"   [L1.5] [OK] Base code match (single variant): {variant_matches[0].get('default_code')}")
                        return result
                    elif len(variant_matches) > 1:
                        # Multiple variants but no good attribute match - needs review
                        result['match'] = variant_matches[0]
                        result['confidence'] = 0.70
                        result['method'] = 'base_code_ambiguous'
                        result['requires_review'] = True
                        logger.warning(f"   [L1.5] [!] Base code match (ambiguous - {len(variant_matches)} variants): {variant_matches[0].get('default_code')}")
                        return result

        # LEVEL 2: Fuzzy Product Code Match (handle typos)
        if product_code:
            normalized_search_code = self.normalize_code(product_code)
            logger.debug(f"   [L2] Fuzzy code search: '{normalized_search_code}'")

            fuzzy_matches = []
            for product in self.products_data:
                db_code = self.normalize_code(product.get('default_code', ''))
                if db_code and len(db_code) > 2:
                    similarity = self._calculate_similarity_safe(normalized_search_code, db_code)
                    if similarity >= self.code_fuzzy_threshold:
                        fuzzy_matches.append({
                            'product': product,
                            'score': similarity,
                            'db_code': db_code
                        })

            if fuzzy_matches:
                # Sort by score
                fuzzy_matches.sort(key=lambda x: x['score'], reverse=True)
                best = fuzzy_matches[0]

                # If top match is significantly better than second, use it
                if len(fuzzy_matches) == 1 or (best['score'] - fuzzy_matches[1]['score']) > 0.05:
                    result['match'] = best['product']
                    result['confidence'] = best['score']
                    result['method'] = 'fuzzy_code'
                    result['requires_review'] = best['score'] < self.auto_approve_threshold
                    logger.info(f"   [L2] [OK] Fuzzy code match: {best['db_code']} ({result['confidence']:.0%})")
                    return result

        # LEVEL 3: Attribute-Based Matching
        if product_name:
            logger.debug(f"   [L3] Attribute search: '{product_name[:50]}...'")
            search_attrs = self.extract_attributes(product_name)

            if search_attrs and len(search_attrs) >= 2:  # Need at least 2 attributes
                attribute_matches = []

                for product in self.products_data:
                    product_text = f"{product.get('name', '')} {product.get('display_name', '')}"
                    product_attrs = self.extract_attributes(product_text)

                    attr_similarity = self._calculate_attribute_similarity(search_attrs, product_attrs)
                    if attr_similarity >= self.attribute_threshold:
                        attribute_matches.append({
                            'product': product,
                            'score': attr_similarity,
                            'matched_attrs': product_attrs
                        })

                if attribute_matches:
                    attribute_matches.sort(key=lambda x: x['score'], reverse=True)
                    best = attribute_matches[0]

                    if len(attribute_matches) == 1 or (best['score'] - attribute_matches[1]['score']) > 0.1:
                        result['match'] = best['product']
                        result['confidence'] = best['score']
                        result['method'] = 'attribute_match'
                        result['requires_review'] = True  # Always review attribute matches
                        logger.info(f"   [L3] [OK] Attribute match: {best['product'].get('default_code')} ({result['confidence']:.0%})")
                        return result
                    else:
                        # Multiple similar matches - return candidates
                        result['candidates'] = [m['product'] for m in attribute_matches[:3]]
                        result['method'] = 'multiple_attribute_matches'
                        logger.info(f"   [L3] [!] Multiple attribute matches found ({len(attribute_matches)})")

        # LEVEL 4: Name Similarity Matching (high threshold only)
        if product_name:
            logger.debug(f"   [L4] Name similarity search: '{product_name[:50]}...'")
            name_matches = []

            for product in self.products_data:
                product_text = product.get('name', '') or product.get('display_name', '')
                if product_text:
                    similarity = self._calculate_similarity_safe(product_name, product_text)
                    if similarity >= self.name_threshold:
                        name_matches.append({
                            'product': product,
                            'score': similarity
                        })

            if name_matches:
                name_matches.sort(key=lambda x: x['score'], reverse=True)
                best = name_matches[0]

                if best['score'] >= 0.90:  # Very high confidence
                    result['match'] = best['product']
                    result['confidence'] = best['score']
                    result['method'] = 'name_similarity'
                    result['requires_review'] = True
                    logger.info(f"   [L4] [OK] Name similarity match: {best['product'].get('default_code')} ({result['confidence']:.0%})")
                    return result
                else:
                    # Lower confidence - return candidates
                    result['candidates'] = [m['product'] for m in name_matches[:3]]
                    result['confidence'] = best['score']
                    result['method'] = 'low_confidence_name'
                    logger.info(f"   [L4] [!] Low confidence name match ({result['confidence']:.0%})")

        # LEVEL 5: AI Semantic Matching (fallback for difficult cases)
        logger.debug(f"   [L5] Attempting AI semantic matching...")
        try:
            from ai_product_matcher import AIProductMatcher
            ai_matcher = AIProductMatcher()

            # Get relaxed candidates for AI evaluation
            candidates = ai_matcher.get_relaxed_candidates(
                self,
                product_name or "",
                product_code,
                max_candidates=10
            )

            if candidates:
                # Prepare product for AI matching
                search_product = {
                    'name': product_name or "",
                    'code': product_code or "",
                    'specifications': ""  # Could extract from product_name if needed
                }

                # Let AI decide the best match
                ai_result = ai_matcher.match_product(search_product, candidates)

                if ai_result:
                    result['match'] = ai_result['product']
                    result['confidence'] = ai_result['confidence']
                    result['method'] = 'ai_semantic_match'
                    result['reasoning'] = ai_result.get('reasoning', '')
                    result['requires_review'] = ai_result.get('requires_review', True)
                    logger.info(f"   [L5] [OK] AI semantic match: {ai_result['product'].get('default_code')} ({result['confidence']:.0%})")
                    return result
        except Exception as e:
            logger.debug(f"   [L5] AI matching unavailable or failed: {e}")

        # LEVEL 6: No reliable match found
        logger.warning(f"   [L6] [X] No reliable match found for: {product_name or product_code}")
        result['method'] = 'no_match'
        result['requires_review'] = True

        return result

    def search_products_batch(self, product_names: List[str], product_codes: List[str] = None,
                             threshold: float = None) -> List[Dict]:
        """
        Search for multiple products at once with multi-level matching

        NEW: Tries ALL extracted codes for each product (handles multiple codes per product)

        Args:
            product_names: List of product names
            product_codes: List of ALL product codes extracted (may be more than product_names)
            threshold: Deprecated (uses multi-level thresholds now)

        Returns:
            List of match results with confidence scores
        """
        all_matches = []
        stats = {
            'exact_code': 0,
            'fuzzy_code': 0,
            'attribute': 0,
            'name_similarity': 0,
            'no_match': 0,
            'auto_approved': 0,
            'review_required': 0
        }

        logger.info(f"[SEARCH] Searching {len(product_names)} products with multi-level matching...")
        if product_codes:
            logger.info(f"   Found {len(product_codes)} codes to try for {len(product_names)} products")

        for idx, name in enumerate(product_names, 1):
            logger.debug(f"\n--- Product {idx}/{len(product_names)} ---")
            logger.debug(f"   Name: {name[:80]}...")

            match_result = None
            best_match = None

            # Strategy 1: Use the corresponding code for this product (1-to-1 pairing)
            codes_to_try = []

            if product_codes and len(product_codes) >= idx:
                # Get the code for THIS product (index-based pairing)
                code_for_this_product = product_codes[idx - 1]  # idx is 1-based

                # Build variants with dimension from product name
                dimension_codes = self.build_code_with_dimension(code_for_this_product, name)
                codes_to_try.extend(dimension_codes)

                # Remove duplicates while preserving order
                seen = set()
                codes_to_try = [c for c in codes_to_try if not (c in seen or seen.add(c))]

                logger.debug(f"   Code for this product: '{code_for_this_product}'")
                logger.debug(f"   Built {len(codes_to_try)} code variants from dimension extraction")

                for code in codes_to_try:
                    if not code:
                        continue

                    logger.debug(f"     Testing code: '{code}'")
                    temp_result = self.search_product_multilevel(product_name=name, product_code=code)

                    if temp_result['match']:
                        # Found a match! Use it if it's better than previous
                        if not best_match or temp_result['confidence'] > best_match['confidence']:
                            best_match = temp_result
                            logger.debug(f"       [OK] Match found! (confidence: {temp_result['confidence']:.0%})")

                            # If exact match with high confidence, stop searching
                            if temp_result['method'] in ['exact_code', 'exact_code_with_attributes'] and temp_result['confidence'] >= 0.95:
                                logger.debug(f"       → High-confidence match found, stopping search")
                                break

                if best_match:
                    match_result = best_match

            # Strategy 2: If no code match, try name-only matching
            if not match_result:
                logger.debug(f"   No code match, trying name-only matching...")
                match_result = self.search_product_multilevel(product_name=name, product_code=None)

            # Process result
            if match_result and match_result['match']:
                # Make a COPY of the matched product to avoid modifying the original
                import copy
                product_copy = copy.deepcopy(match_result['match'])

                # Add extracted product name for tracking
                product_copy['extracted_product_name'] = name
                product_copy['match_score'] = match_result['confidence']
                product_copy['match_method'] = match_result['method']
                product_copy['requires_review'] = match_result['requires_review']

                all_matches.append(product_copy)

                # Update stats
                stats[match_result['method']] = stats.get(match_result['method'], 0) + 1
                if match_result['requires_review']:
                    stats['review_required'] += 1
                else:
                    stats['auto_approved'] += 1

                code_str = match_result['match'].get('default_code', 'N/A')
                logger.info(f"   [OK] Product {idx}: Matched {code_str} (method: {match_result['method']}, confidence: {match_result['confidence']:.0%})")
            else:
                stats['no_match'] += 1
                stats['review_required'] += 1
                logger.warning(f"   [X] Product {idx}: No match found")

        # Log summary
        total = len(product_names)
        matched = len(all_matches)
        logger.info(f"\n[STATS] Matching Summary:")
        logger.info(f"   Total: {total} products")
        logger.info(f"   Matched: {matched}/{total} ({matched/total*100:.0f}%)")
        logger.info(f"   Auto-approved: {stats['auto_approved']} ({stats['auto_approved']/total*100:.0f}%)")
        logger.info(f"   Review required: {stats['review_required']} ({stats['review_required']/total*100:.0f}%)")
        logger.info(f"\n   Methods used:")
        logger.info(f"     Exact code: {stats.get('exact_code', 0)}")
        logger.info(f"     Fuzzy code: {stats.get('fuzzy_code', 0)}")
        logger.info(f"     Attributes: {stats.get('attribute', 0)}")
        logger.info(f"     Name similarity: {stats.get('name_similarity', 0)}")
        logger.info(f"     No match: {stats['no_match']}")

        return all_matches

    # Deprecated old methods - keep for backward compatibility but use new multilevel
    def search_product(self, product_name: str = None, product_code: str = None,
                      threshold: float = 0.85) -> List[Dict]:
        """
        Legacy method - calls new multilevel search
        """
        result = self.search_product_multilevel(product_name, product_code)
        if result['match']:
            return [result['match']]
        return []

    def search_customer(self, company_name: str = None, customer_name: str = None,
                       email: str = None, threshold: float = 0.6) -> Optional[Dict]:
        """
        Search for customer in JSON data with fuzzy matching
        (Customer matching logic unchanged - working well)
        """
        if not self.customers_data:
            logger.warning("No customer data loaded")
            return None

        best_match = None
        best_score = 0.0

        # Strategy 1: Search by company name
        if company_name:
            for customer in self.customers_data:
                customer_company = customer.get('name', '') or customer.get('commercial_company_name', '')
                score = self._calculate_similarity_safe(company_name, customer_company)
                if score > best_score:
                    best_score = score
                    best_match = customer

        # Strategy 2: Search by customer name
        if customer_name and best_score < threshold:
            for customer in self.customers_data:
                customer_contact = customer.get('name', '')
                score = self._calculate_similarity_safe(customer_name, customer_contact)
                if score > best_score:
                    best_score = score
                    best_match = customer

        # Strategy 3: Search by email
        if email and best_score < threshold:
            for customer in self.customers_data:
                customer_email = customer.get('email', '')
                if customer_email and email.lower() in customer_email.lower():
                    best_score = 0.95
                    best_match = customer
                    break

        if best_match and best_score >= threshold:
            logger.info(f"Customer match: {best_match.get('name')} ({best_score:.0%})")
            return {**best_match, 'match_score': best_score}
        else:
            logger.warning(f"No customer match (score: {best_score:.0%})")
            return None

    def get_stats(self) -> Dict:
        """Get vector store statistics"""
        return {
            'total_customers': len(self.customers_data),
            'total_products': len(self.products_data),
            'customers_file': self.customers_json,
            'products_file': self.products_json,
            'thresholds': {
                'code_exact': self.code_exact_threshold,
                'code_fuzzy': self.code_fuzzy_threshold,
                'attribute': self.attribute_threshold,
                'name': self.name_threshold,
                'auto_approve': self.auto_approve_threshold,
                'review': self.review_threshold
            }
        }

    def close(self):
        """Cleanup and close vector store"""
        logger.info("Closing JSON-based vector store...")
        pass
