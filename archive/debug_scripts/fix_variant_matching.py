"""
Enhanced Product Variant Matching
Handles products with multiple variants based on attributes (color, machine type, dimensions)
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class VariantMatcher:
    """Matches product variants using base code + attributes"""

    def __init__(self):
        self.machine_types = {
            '16S': ['16S', 'BOBST 16S'],
            '26S': ['26S', 'BOBST 26S'],
            '20SIX': ['20SIX', '20 SIX', 'BOBST 20SIX'],
            'W&H': ['W&H', 'W & H', 'WH'],
            'KBA': ['KBA']
        }

        self.colors = {
            'BLAU': ['BLAU', 'BLU', 'BLUE'],
            'GRY': ['GRY', 'GREY', 'GRAY'],
            'ORG': ['ORG', 'ORANGE'],
            'BLK': ['BLK', 'BLACK', 'SCHWARZ'],
            'MG': ['MG', 'MAGENTA']
        }

    def extract_base_code(self, product_code: str) -> str:
        """
        Extract base product code from variant code

        Examples:
        - SDS025B -> SDS025
        - SDS025177-K12 Blau -> SDS025
        - SDS2573 -> SDS2573

        Args:
            product_code: Full product code

        Returns:
            Base code without variant suffix
        """
        if not product_code:
            return ""

        # Pattern: Base code is letters + 3-4 digits at the start
        # SDS025, SDS2573, etc.
        base_match = re.match(r'^([A-Z]+\d{3,4})', product_code.upper())
        if base_match:
            return base_match.group(1)

        return product_code

    def extract_variant_attributes(self, product_name: str, product_code: str = "") -> Dict:
        """
        Extract variant-specific attributes from product name/code

        Args:
            product_name: Full product name
            product_code: Product code (optional)

        Returns:
            Dictionary of extracted attributes
        """
        text = f"{product_name} {product_code}".upper()

        attributes = {
            'machine_type': None,
            'color': None,
            'dimensions': [],
            'material_codes': []
        }

        # Extract machine type
        for machine_key, machine_variants in self.machine_types.items():
            for variant in machine_variants:
                if variant in text:
                    attributes['machine_type'] = machine_key
                    break
            if attributes['machine_type']:
                break

        # Extract color
        for color_key, color_variants in self.colors.items():
            for variant in color_variants:
                if variant in text:
                    attributes['color'] = color_key
                    break
            if attributes['color']:
                break

        # Extract material codes (177, 178, 544, etc.)
        material_pattern = r'\b(1\d{2}[A-Z]?)\b'
        attributes['material_codes'] = list(set(re.findall(material_pattern, text)))

        # Extract dimensions (e.g., "25x0.20")
        dimension_patterns = [
            r'(\d{1,3})\s*[xX]\s*(\d+[.,]\d+)',  # 25x0.20
            r'(\d{1,3})\s*mm',                    # 25mm
        ]
        for pattern in dimension_patterns:
            matches = re.findall(pattern, product_name)
            if matches:
                attributes['dimensions'].extend([str(m) if isinstance(m, str) else 'x'.join(m) for m in matches])

        return attributes

    def calculate_variant_similarity(self, search_attrs: Dict, db_attrs: Dict) -> float:
        """
        Calculate similarity between two variant attribute sets

        Args:
            search_attrs: Attributes from search query
            db_attrs: Attributes from database product

        Returns:
            Similarity score (0.0 to 1.0)
        """
        score = 0.0
        total_weight = 0.0

        # Machine type (high weight - critical for compatibility)
        if search_attrs.get('machine_type') and db_attrs.get('machine_type'):
            total_weight += 1.0
            if search_attrs['machine_type'] == db_attrs['machine_type']:
                score += 1.0

        # Color (medium weight)
        if search_attrs.get('color') and db_attrs.get('color'):
            total_weight += 0.7
            if search_attrs['color'] == db_attrs['color']:
                score += 0.7

        # Material codes (medium weight)
        if search_attrs.get('material_codes') and db_attrs.get('material_codes'):
            search_materials = set(search_attrs['material_codes'])
            db_materials = set(db_attrs['material_codes'])
            if search_materials and db_materials:
                total_weight += 0.5
                overlap = len(search_materials & db_materials) / len(search_materials | db_materials)
                score += 0.5 * overlap

        # Dimensions (low weight - often omitted in orders)
        if search_attrs.get('dimensions') and db_attrs.get('dimensions'):
            search_dims = set(search_attrs['dimensions'])
            db_dims = set(db_attrs['dimensions'])
            if search_dims and db_dims:
                total_weight += 0.3
                overlap = len(search_dims & db_dims) / len(search_dims | db_dims)
                score += 0.3 * overlap

        # Normalize score
        if total_weight > 0:
            return score / total_weight
        else:
            return 0.0

    def match_variant(self, search_name: str, search_code: str,
                     candidate_products: List[Dict]) -> Optional[Dict]:
        """
        Match the best variant from a list of candidates

        Args:
            search_name: Product name from email
            search_code: Product code from email (may be base or full)
            candidate_products: List of product variants with same base code

        Returns:
            Best matching product or None
        """
        if not candidate_products:
            return None

        # If only one candidate, return it
        if len(candidate_products) == 1:
            return {
                'product': candidate_products[0],
                'confidence': 1.0,
                'method': 'single_variant'
            }

        # Extract search attributes
        search_attrs = self.extract_variant_attributes(search_name, search_code)

        logger.debug(f"   [VARIANT] Matching among {len(candidate_products)} variants")
        logger.debug(f"   [VARIANT] Search attributes: {search_attrs}")

        # Score each candidate
        scored_candidates = []
        for product in candidate_products:
            db_attrs = self.extract_variant_attributes(
                product.get('name', ''),
                product.get('default_code', '')
            )

            similarity = self.calculate_variant_similarity(search_attrs, db_attrs)

            scored_candidates.append({
                'product': product,
                'score': similarity,
                'attributes': db_attrs
            })

            logger.debug(f"      {product.get('default_code')}: {similarity:.0%} - {db_attrs}")

        # Sort by score
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)

        # Get best match
        best = scored_candidates[0]

        # Check if best match is significantly better than second best
        if len(scored_candidates) > 1:
            second_best = scored_candidates[1]
            confidence = best['score']

            # If scores are too close, it's ambiguous
            if abs(best['score'] - second_best['score']) < 0.1:
                logger.warning(f"   [VARIANT] Ambiguous: Best={best['score']:.0%}, Second={second_best['score']:.0%}")
                return {
                    'product': best['product'],
                    'confidence': 0.5,
                    'method': 'variant_ambiguous',
                    'note': 'Multiple variants match equally - review required'
                }
        else:
            confidence = best['score']

        # If no attributes matched, return with low confidence
        if best['score'] == 0:
            logger.warning(f"   [VARIANT] No attributes matched - returning first variant")
            return {
                'product': best['product'],
                'confidence': 0.3,
                'method': 'variant_default',
                'note': 'No distinguishing attributes found'
            }

        logger.info(f"   [VARIANT] Best match: {best['product'].get('default_code')} ({confidence:.0%})")

        return {
            'product': best['product'],
            'confidence': confidence,
            'method': 'variant_match'
        }


def search_products_with_variants(vector_store, product_name: str, product_code: str = None) -> Dict:
    """
    Enhanced product search that handles variants

    Args:
        vector_store: VectorStore instance
        product_name: Product name from email
        product_code: Product code from email (optional)

    Returns:
        Match result with best variant
    """
    matcher = VariantMatcher()

    # Extract base code
    if product_code:
        base_code = matcher.extract_base_code(product_code)
        logger.info(f"   [SEARCH] Base code: {base_code} (from {product_code})")
    else:
        # Try to extract code from name
        code_patterns = [
            r'\b([A-Z]+\d{3,4})\b',  # SDS025, L1520, etc.
        ]
        base_code = None
        for pattern in code_patterns:
            match = re.search(pattern, product_name.upper())
            if match:
                base_code = match.group(1)
                logger.info(f"   [SEARCH] Base code extracted from name: {base_code}")
                break

    # Search for all products with this base code
    candidates = []
    if base_code:
        for product in vector_store.products_data:
            db_code = product.get('default_code', '')
            if db_code:
                db_base = matcher.extract_base_code(db_code)
                if db_base == base_code:
                    candidates.append(product)

        logger.info(f"   [SEARCH] Found {len(candidates)} variants for base code {base_code}")

    # If no candidates found by code, try name matching
    if not candidates:
        logger.info(f"   [SEARCH] No code match, trying name similarity...")
        # Use original vector store search
        result = vector_store.search_product_multilevel(
            product_name=product_name,
            product_code=product_code
        )
        return result

    # Match best variant
    variant_match = matcher.match_variant(product_name, product_code or "", candidates)

    if variant_match:
        return {
            'match': variant_match['product'],
            'confidence': variant_match['confidence'],
            'method': variant_match['method'],
            'requires_review': variant_match['confidence'] < 0.7,
            'note': variant_match.get('note'),
            'variant_count': len(candidates)
        }
    else:
        return {
            'match': None,
            'confidence': 0.0,
            'method': 'no_match',
            'requires_review': True
        }


# Test the variant matching
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    from retriever_module.vector_store import VectorStore

    vector_store = VectorStore()

    print("\n" + "="*80)
    print("VARIANT MATCHING TEST")
    print("="*80)

    test_cases = [
        {
            "name": "SDS025 with machine type",
            "product_name": "DuroSeal Bobst 26S Blau",
            "product_code": "SDS025"
        },
        {
            "name": "SDS025 with color only",
            "product_name": "DuroSeal Blue",
            "product_code": "SDS025"
        },
        {
            "name": "Full variant code",
            "product_name": "DuroSeal Bobst",
            "product_code": "SDS025B"
        },
        {
            "name": "Code in name",
            "product_name": "SDS025 DuroSeal Bobst 16S Grey",
            "product_code": None
        }
    ]

    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"  Input: '{test['product_name']}' + '{test['product_code']}'")

        result = search_products_with_variants(
            vector_store,
            test['product_name'],
            test['product_code']
        )

        if result['match']:
            print(f"  MATCHED: {result['match']['default_code']}")
            print(f"  Name: {result['match']['name'][:60]}")
            print(f"  Confidence: {result['confidence']:.0%}")
            print(f"  Method: {result['method']}")
            if result.get('variant_count'):
                print(f"  Variants: Selected 1 of {result['variant_count']}")
        else:
            print(f"  NO MATCH")

    print("\n" + "="*80)