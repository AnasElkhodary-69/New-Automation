"""
Smart Product Matcher - PHASE 2

Implements 7-level intelligent product matching cascade:
- Level 0: Customer code translation
- Level 1: Exact code + attribute validation
- Level 2: Fuzzy code + attribute validation
- Level 3: Pure attribute matching (NO CODE scenarios)
- Level 4: RAG semantic search
- Level 5: Keyword name matching
- Level 6: Partial match with human review
- Level 7: No match
"""

import logging
import re
from typing import Dict, List, Optional, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class SmartProductMatcher:
    """Intelligent multi-level product matcher with attribute validation"""

    def __init__(self, products: List[Dict], customer_mapper=None, rag_search=None, enable_rag: bool = True):
        """
        Initialize SmartProductMatcher

        Args:
            products: List of product dictionaries from database
            customer_mapper: CustomerCodeMapper instance (optional)
            rag_search: SimpleProductRAG instance (optional)
            enable_rag: Enable RAG semantic search
        """
        self.products = products
        self.customer_mapper = customer_mapper
        self.rag = rag_search
        self.enable_rag = enable_rag and rag_search is not None
        self.matched_products = []  # Track matched product IDs to prevent duplicates

    def find_match(self, extracted_product: Dict, customer_id: Optional[str] = None) -> Dict:
        """
        Main matching function - tries all 7 levels

        Args:
            extracted_product: {
                'product_code': 'SDS025' or 'NO_CODE_FOUND',
                'product_name': 'SDS025 - 177H DuroSeal Bobst 16S Grey',
                'attributes': {
                    'brand': 'DuroSeal',
                    'machine_type': '16S',
                    'dimensions': {'width': 177, 'height': None, 'thickness': None},
                    'color': 'Grey',
                    'length': None
                }
            }
            customer_id: Odoo customer ID for code translation

        Returns:
            Match result dictionary
        """
        code = extracted_product.get('product_code', '')
        name = extracted_product.get('product_name', '')
        attrs = extracted_product.get('attributes', {})

        logger.info(f"\n   [SMART MATCHER] Finding match for: {name[:60]}...")
        logger.info(f"   Code: {code}, Has attributes: {bool(attrs)}")

        # Level 0: Customer Code Translation
        if customer_id and self.customer_mapper and code and code != 'NO_CODE_FOUND':
            translated = self.customer_mapper.translate_code(customer_id, code)
            if translated != code:
                logger.info(f"   [L0] Customer code translation: {code} → {translated}")
                code = translated
                extracted_product['product_code'] = translated

        # Level 1: Exact Code Match + Validation
        if code and code != 'NO_CODE_FOUND':
            result = self._exact_code_match(code, name, attrs)
            if result and self._validate_not_duplicate(result['match']):
                logger.info(f"   [L1] [OK] Exact match: {result['match'].get('default_code')}")
                return result

        # Level 2: Fuzzy Code Match + Validation
        if code and code != 'NO_CODE_FOUND':
            result = self._fuzzy_code_match(code, name, attrs)
            if result and self._validate_not_duplicate(result['match']):
                logger.info(f"   [L2] [OK] Fuzzy match: {result['match'].get('default_code')}")
                return result

        # Level 3: Attribute-Based Matching (for NO_CODE scenarios)
        if attrs and self._has_useful_attributes(attrs):
            result = self._attribute_match(attrs, name)
            if result and self._validate_not_duplicate(result['match']):
                logger.info(f"   [L3] [OK] Attribute match: {result['match'].get('default_code')}")
                return result

        # Level 4: RAG Semantic Search
        if self.enable_rag and self.rag and name:
            result = self._rag_semantic_search(name, attrs)
            if result and self._validate_not_duplicate(result['match']):
                logger.info(f"   [L4] [OK] RAG match: {result['match'].get('default_code')}")
                return result

        # Level 5: Keyword Name Matching
        if name:
            result = self._keyword_name_match(name, attrs)
            if result and self._validate_not_duplicate(result['match']):
                logger.info(f"   [L5] [OK] Keyword match: {result['match'].get('default_code')}")
                return result

        # Level 6: Partial Match (human review)
        candidates = self._get_partial_matches(code, name, attrs)
        if candidates:
            logger.warning(f"   [L6] [!] Multiple candidates, review needed")
            return {
                'match': candidates[0],
                'candidates': candidates[1:3],
                'confidence': 0.50,
                'method': 'partial_match_review_required',
                'requires_review': True
            }

        # Level 7: No Match
        logger.error(f"   [L7] [X] No match found for: {name[:60]}")
        return {
            'match': None,
            'confidence': 0.0,
            'method': 'no_match',
            'requires_review': True
        }

    def _exact_code_match(self, code: str, name: str, attrs: Dict) -> Optional[Dict]:
        """
        Level 1: Exact code match with attribute validation

        Tries:
        1. Exact code match
        2. Prefix match (L1520 → L1520-685)
        3. Validates with attributes
        """
        # Normalize code
        clean_code = code.replace("3M ", "").strip()
        base_code = clean_code.split('-')[0]

        candidates = []

        # Try exact match
        for p in self.products:
            p_code = str(p.get('default_code', '')).strip()  # FIX: Strip whitespace from DB codes
            if p_code == clean_code:
                candidates.append(p)

        # Try prefix match (L1520 → L1520-685-33)
        if not candidates:
            for p in self.products:
                p_code = str(p.get('default_code', '')).strip()  # FIX: Strip whitespace from DB codes
                # Must start with base code followed by dash or exact match
                if p_code.startswith(base_code + '-') or p_code == base_code:
                    candidates.append(p)

        if not candidates:
            return None

        logger.debug(f"      Found {len(candidates)} code candidates")

        # Validate with attributes
        validated = self._validate_candidates_with_attributes(candidates, attrs, name)

        if validated:
            attr_match_score = validated['attribute_match_score']

            # Determine confidence based on attribute match
            if attr_match_score >= 0.9:
                confidence = 1.0
            elif attr_match_score >= 0.7:
                confidence = 0.95
            else:
                confidence = 0.90

            return {
                'match': validated['product'],
                'confidence': confidence,
                'method': 'exact_code_with_attributes',
                'attribute_match': attr_match_score,
                'requires_review': confidence < 0.95
            }

        # CRITICAL FIX: Code matched but attributes don't validate
        # TRUST THE CODE MATCH - it's more reliable than attributes!
        logger.warning(f"      Code {code} matched but attributes weak - trusting code match anyway")
        return {
            'match': candidates[0],
            'confidence': 0.85,  # High confidence for exact code, even without attribute validation
            'method': 'exact_code_only',
            'attribute_match': 0.0,
            'requires_review': False  # Exact code is reliable
        }

    def _fuzzy_code_match(self, code: str, name: str, attrs: Dict) -> Optional[Dict]:
        """
        Level 2: Fuzzy code match with strict attribute validation

        MUST validate with attributes to prevent wrong matches (e.g., L1520 vs E1015)
        """
        clean_code = code.replace("3M ", "").strip().upper()
        base_code = clean_code.split('-')[0]

        candidates = []

        # Find similar codes
        for p in self.products:
            p_code = str(p.get('default_code', '')).upper()

            # Check similarity
            similarity = SequenceMatcher(None, clean_code, p_code).ratio()

            if similarity >= 0.8:  # High threshold for fuzzy code matching
                candidates.append({
                    'product': p,
                    'code_similarity': similarity
                })

        if not candidates:
            return None

        logger.debug(f"      Found {len(candidates)} fuzzy code candidates")

        # MUST validate with attributes for fuzzy matches
        if not attrs or not self._has_useful_attributes(attrs):
            logger.warning("      Fuzzy code match requires attributes for validation")
            return None

        # Sort by code similarity
        candidates.sort(key=lambda x: x['code_similarity'], reverse=True)

        # Try to validate top candidates
        for candidate in candidates[:5]:
            product_list = [candidate['product']]
            validated = self._validate_candidates_with_attributes(product_list, attrs, name)

            if validated and validated['attribute_match_score'] >= 0.8:
                return {
                    'match': validated['product'],
                    'confidence': 0.85,
                    'method': 'fuzzy_code_with_attributes',
                    'code_similarity': candidate['code_similarity'],
                    'attribute_match': validated['attribute_match_score'],
                    'requires_review': True  # Always review fuzzy matches
                }

        return None

    def _attribute_match(self, attrs: Dict, name: str) -> Optional[Dict]:
        """
        Level 3: Pure attribute-based matching (NO CODE scenario)

        Matches products based on:
        - Brand (required if available)
        - Machine type (required if available)
        - Width (required if available)
        - Color (optional)
        - Product line (optional)
        """
        # Build attribute requirements
        required_attrs = {}
        optional_attrs = {}

        if attrs.get('brand'):
            required_attrs['brand'] = attrs['brand']

        if attrs.get('machine_type'):
            required_attrs['machine_type'] = attrs['machine_type']

        if attrs.get('dimensions', {}).get('width'):
            required_attrs['width'] = attrs['dimensions']['width']

        if attrs.get('dimensions', {}).get('height'):
            required_attrs['height'] = attrs['dimensions']['height']

        if attrs.get('color'):
            optional_attrs['color'] = attrs['color']

        if attrs.get('product_line'):
            optional_attrs['product_line'] = attrs['product_line']

        if not required_attrs:
            logger.debug("      No required attributes for matching")
            return None

        logger.debug(f"      Matching on required: {list(required_attrs.keys())}")

        # Search products matching ALL required attributes
        candidates = []

        for product in self.products:
            p_name = str(product.get('name', ''))
            p_code = str(product.get('default_code', ''))
            combined_text = f"{p_name} {p_code}".upper()

            matches = 0
            total_required = len(required_attrs)

            # Check required attributes
            for attr_name, attr_value in required_attrs.items():
                if attr_name in ['width', 'height']:
                    # Allow ±5mm tolerance for dimensions
                    if self._check_dimension_in_text(attr_value, combined_text):
                        matches += 1
                elif str(attr_value).upper() in combined_text:
                    matches += 1

            # Need ALL required attributes to match
            if matches == total_required and total_required > 0:
                # Check optional attributes for scoring
                optional_matches = 0
                for attr_name, attr_value in optional_attrs.items():
                    if str(attr_value).upper() in combined_text:
                        optional_matches += 1

                total_attrs = total_required + len(optional_attrs)
                match_score = (matches + optional_matches) / total_attrs if total_attrs > 0 else 0

                candidates.append({
                    'product': product,
                    'score': match_score,
                    'required_matches': matches,
                    'optional_matches': optional_matches
                })

        if not candidates:
            logger.debug("      No attribute matches found")
            return None

        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)
        best = candidates[0]

        logger.debug(f"      Best attribute match score: {best['score']:.2f}")

        # Set confidence based on match quality
        if best['score'] >= 0.8:
            confidence = 0.80
        elif best['score'] >= 0.6:
            confidence = 0.70
        else:
            confidence = 0.60

        return {
            'match': best['product'],
            'confidence': confidence,
            'method': 'attribute_matching',
            'attribute_match_score': best['score'],
            'required_matches': best['required_matches'],
            'optional_matches': best['optional_matches'],
            'requires_review': confidence < 0.75
        }

    def _rag_semantic_search(self, name: str, attrs: Dict) -> Optional[Dict]:
        """
        Level 4: RAG semantic search with attribute filtering
        """
        if not self.rag:
            return None

        try:
            logger.debug(f"      RAG search for: {name[:50]}...")

            # Search with RAG
            results = self.rag.search(name, top_k=5, min_score=0.40)

            if not results:
                return None

            # Filter by attributes if available
            if attrs and self._has_useful_attributes(attrs):
                filtered_results = []
                for result in results:
                    # Check if attributes match
                    attr_score = self._calculate_attribute_similarity(result, attrs)
                    if attr_score >= 0.5:  # Minimum attribute alignment
                        result['combined_score'] = (result['similarity_score'] + attr_score) / 2
                        filtered_results.append(result)

                if filtered_results:
                    filtered_results.sort(key=lambda x: x['combined_score'], reverse=True)
                    best = filtered_results[0]

                    return {
                        'match': best,
                        'confidence': best['combined_score'],
                        'method': 'rag_semantic_with_attributes',
                        'similarity_score': best['similarity_score'],
                        'attribute_alignment': attr_score,
                        'requires_review': True  # Always review RAG matches
                    }

            # No attribute filtering or no filtered results - use best RAG match
            best = results[0]
            return {
                'match': best,
                'confidence': best['similarity_score'],
                'method': 'rag_semantic',
                'similarity_score': best['similarity_score'],
                'requires_review': True
            }

        except Exception as e:
            logger.error(f"      RAG search failed: {e}")
            return None

    def _keyword_name_match(self, name: str, attrs: Dict) -> Optional[Dict]:
        """
        Level 5: Keyword-based name matching

        Extracts key terms and finds products with most matches
        """
        # Extract keywords from name
        keywords = self._extract_keywords(name)

        if len(keywords) < 2:
            return None

        logger.debug(f"      Keyword matching with: {keywords[:5]}")

        candidates = []

        for product in self.products:
            p_name = str(product.get('name', '')).upper()
            p_code = str(product.get('default_code', '')).upper()
            combined = f"{p_name} {p_code}"

            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in combined)

            if matches >= 2:  # At least 2 keywords must match
                score = matches / len(keywords)
                candidates.append({
                    'product': product,
                    'score': score,
                    'matches': matches
                })

        if not candidates:
            return None

        candidates.sort(key=lambda x: x['score'], reverse=True)
        best = candidates[0]

        return {
            'match': best['product'],
            'confidence': 0.60,
            'method': 'keyword_name_matching',
            'keyword_match_score': best['score'],
            'keywords_matched': best['matches'],
            'requires_review': True
        }

    def _get_partial_matches(self, code: str, name: str, attrs: Dict) -> List[Dict]:
        """
        Level 6: Get partial matches for human review

        Returns top 3 candidates that partially match
        """
        candidates = []

        # Try loose code matching
        if code and code != 'NO_CODE_FOUND':
            clean_code = code.upper()
            for p in self.products:
                p_code = str(p.get('default_code', '')).upper()
                if clean_code[:3] in p_code or p_code[:3] in clean_code:
                    candidates.append(p)

        # Try loose name matching
        if name and len(candidates) < 5:
            name_upper = name.upper()
            for p in self.products:
                p_name = str(p.get('name', '')).upper()
                similarity = SequenceMatcher(None, name_upper[:30], p_name[:30]).ratio()
                if similarity >= 0.5 and p not in candidates:
                    candidates.append(p)

        return candidates[:3]

    def _validate_candidates_with_attributes(self, candidates: List[Dict], attrs: Dict, name: str) -> Optional[Dict]:
        """
        Validate product candidates against extracted attributes

        Returns best match or None
        """
        if not attrs or not self._has_useful_attributes(attrs):
            # No attributes to validate - return first candidate
            logger.debug(f"      No attributes for validation, returning first candidate")
            return {'product': candidates[0], 'attribute_match_score': 0.5}

        best_match = None
        best_score = 0.0

        for product in candidates:
            score = self._calculate_attribute_similarity(product, attrs)
            logger.debug(f"      Candidate {product.get('default_code')}: score={score:.2f}")

            if score > best_score:
                best_score = score
                best_match = product

        # Lower threshold to 0.4 for exact code matches (was 0.6)
        # If the code matched exactly, we should trust it more
        min_threshold = 0.4 if candidates else 0.6

        if best_match and best_score >= min_threshold:
            logger.debug(f"      Best match: {best_match.get('default_code')} (score={best_score:.2f})")
            return {'product': best_match, 'attribute_match_score': best_score}

        logger.debug(f"      No candidates passed validation (best score: {best_score:.2f}, threshold: {min_threshold})")
        return None

    def _calculate_attribute_similarity(self, product: Dict, attrs: Dict) -> float:
        """
        Calculate how well product attributes match extracted attributes

        Returns score 0.0 - 1.0
        """
        p_name = str(product.get('name', '')).upper()
        p_code = str(product.get('default_code', '')).upper()
        combined = f"{p_name} {p_code}"

        score = 0.0
        checks = 0

        # Machine type (critical - 30% weight)
        if attrs.get('machine_type'):
            checks += 1
            if str(attrs['machine_type']).upper() in combined:
                score += 0.3

        # Width (critical - 30% weight)
        if attrs.get('dimensions', {}).get('width'):
            checks += 1
            if self._check_dimension_in_text(attrs['dimensions']['width'], combined):
                score += 0.3

        # Height (important - 15% weight)
        if attrs.get('dimensions', {}).get('height'):
            checks += 1
            if self._check_dimension_in_text(attrs['dimensions']['height'], combined):
                score += 0.15

        # Brand (important - 15% weight)
        if attrs.get('brand'):
            checks += 1
            if str(attrs['brand']).upper() in combined:
                score += 0.15

        # Color (nice to have - 10% weight)
        if attrs.get('color'):
            checks += 1
            if str(attrs['color']).upper() in combined:
                score += 0.10

        # Normalize score
        if checks > 0:
            return score
        else:
            return 0.5  # No attributes to check

    def _check_dimension_in_text(self, dimension: int, text: str) -> bool:
        """Check if dimension appears in text (with ±5mm tolerance)"""
        dim_str = str(dimension)

        # Exact match
        if dim_str in text:
            return True

        # Check with tolerance
        for offset in range(-5, 6):
            if str(dimension + offset) in text:
                return True

        return False

    def _has_useful_attributes(self, attrs: Dict) -> bool:
        """Check if attributes dict has useful data for matching"""
        if not attrs:
            return False

        return any([
            attrs.get('brand'),
            attrs.get('machine_type'),
            attrs.get('dimensions', {}).get('width'),
            attrs.get('dimensions', {}).get('height'),
            attrs.get('color')
        ])

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from product name"""
        # Remove common words
        stop_words = {'THE', 'A', 'AN', 'AND', 'OR', 'FOR', 'WITH', 'MM', 'M', 'X'}

        # Extract words (3+ chars)
        words = re.findall(r'\b\w{3,}\b', text.upper())

        # Filter stop words and numbers only
        keywords = [w for w in words if w not in stop_words and not w.isdigit()]

        return keywords

    def _validate_not_duplicate(self, product: Optional[Dict]) -> bool:
        """
        Prevent matching same product twice

        Critical for catching errors like L1520 and L1320 both matching E1015
        """
        if product is None:
            return False

        product_id = product.get('id') or product.get('product_tmpl_id')
        if isinstance(product_id, list):
            product_id = product_id[0] if product_id else None

        if product_id in self.matched_products:
            logger.error(f"      [X] DUPLICATE: {product.get('default_code')} already matched!")
            return False

        self.matched_products.append(product_id)
        return True

    def reset_matched_products(self):
        """Reset matched products tracker (call between orders)"""
        self.matched_products = []
