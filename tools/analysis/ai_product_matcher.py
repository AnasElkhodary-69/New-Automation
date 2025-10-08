"""
AI-Assisted Product Matching
Uses Mistral to semantically match products when fuzzy matching fails
"""

import json
import logging
from typing import Dict, List, Optional
from mistralai import Mistral
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class AIProductMatcher:
    """Uses AI to semantically match products"""

    def __init__(self):
        self.client = Mistral(api_key=os.getenv('MISTRAL_API_KEY'))
        self.model = "mistral-small-latest"

    def match_product(self, search_product: Dict, candidates: List[Dict]) -> Optional[Dict]:
        """
        Use AI to match a product against candidates

        Args:
            search_product: Product from email with name, code, specifications
            candidates: List of potential matches from database

        Returns:
            Best match with confidence score or None
        """
        if not candidates:
            return None

        # Prepare prompt
        prompt = self._create_matching_prompt(search_product, candidates)

        try:
            # Call Mistral
            response = self.client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for deterministic matching
                max_tokens=500
            )

            result_text = response.choices[0].message.content
            logger.debug(f"AI Matching response: {result_text}")

            # Parse response
            result = self._parse_matching_response(result_text, candidates)
            return result

        except Exception as e:
            logger.error(f"AI matching failed: {e}")
            return None

    def _create_matching_prompt(self, search_product: Dict, candidates: List[Dict]) -> str:
        """Create prompt for AI matching"""

        # Format search product
        search_info = f"""
PRODUCT TO MATCH:
- Name: {search_product.get('name', 'N/A')}
- Code: {search_product.get('code', 'N/A')}
- Specifications: {search_product.get('specifications', 'N/A')}
"""

        # Format candidates
        candidates_info = "POSSIBLE MATCHES:\n"
        for i, candidate in enumerate(candidates, 1):
            candidates_info += f"""
{i}. Database Code: {candidate.get('default_code', 'N/A')}
   Name: {candidate.get('name', 'N/A')}
"""

        prompt = f"""You are a product matching expert for an industrial supplies company.

Your task: Match the customer's product to the correct product in our database.

{search_info}

{candidates_info}

MATCHING RULES:
1. Consider product type, brand, dimensions, specifications
2. Customer codes may differ from our internal codes
3. Focus on the FUNCTIONAL match, not exact name match
4. If multiple matches are possible, choose the most likely one
5. Be conservative - if no good match exists, say "NO_MATCH"

EXAMPLES:
- Customer: "DF-3068 W&H Miraflex Grau" → Database: "SDS006A Duro Seal W&H Miraflex" = MATCH (same product, different codes)
- Customer: "3M 904-12-G" → Database: "3M904-12-44 Scotch ATG 904 12mm x 44m" = MATCH (same 3M 904 tape, 12mm width)
- Customer: "Doctor Blade 40x0.20 RPE" → Database: "Doctor Blade 40x0.20 2°" = NO_MATCH (RPE ≠ 2°, different edge types)

Respond in this EXACT format:
{{
  "match_index": <number 1-{len(candidates)} or 0 for NO_MATCH>,
  "confidence": <0-100>,
  "reasoning": "<brief explanation>"
}}

Your response (JSON only):"""

        return prompt

    def _parse_matching_response(self, response_text: str, candidates: List[Dict]) -> Optional[Dict]:
        """Parse AI matching response"""
        try:
            # Remove markdown if present
            import re
            cleaned = response_text.strip()
            if cleaned.startswith('```'):
                cleaned = re.sub(r'^```(?:json)?\s*\n', '', cleaned)
                cleaned = re.sub(r'\n```\s*$', '', cleaned)

            # Parse JSON
            result = json.loads(cleaned)

            match_index = result.get('match_index', 0)
            confidence = result.get('confidence', 0) / 100.0  # Convert to 0-1
            reasoning = result.get('reasoning', '')

            # Validate
            if match_index == 0 or match_index > len(candidates):
                logger.info(f"   [AI] No match found. Reasoning: {reasoning}")
                return None

            matched_product = candidates[match_index - 1]

            logger.info(f"   [AI] Matched to candidate {match_index}: {matched_product.get('default_code')} ({confidence:.0%})")
            logger.info(f"   [AI] Reasoning: {reasoning}")

            return {
                'product': matched_product,
                'confidence': confidence,
                'method': 'ai_semantic_match',
                'reasoning': reasoning,
                'requires_review': confidence < 0.8
            }

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.debug(f"Response was: {response_text}")
            return None

    def get_relaxed_candidates(self, vector_store, product_name: str, product_code: str = None, max_candidates: int = 10) -> List[Dict]:
        """
        Get potential product matches using relaxed fuzzy matching

        Args:
            vector_store: VectorStore instance
            product_name: Product name
            product_code: Product code (optional)
            max_candidates: Maximum number of candidates to return

        Returns:
            List of candidate products
        """
        candidates = []
        seen_ids = set()

        # Extract key terms from product name
        import re

        # Get brand/key identifiers (3M, Scotch, W&H, Miraflex, etc.)
        brand_patterns = [
            (r'\b(3M)\b', 'brand'),
            (r'\b(Scotch)\b', 'brand'),
            (r'\b(Tesa)\b', 'brand'),
            (r'\b(Doctor\s*Blade)\b', 'product'),
            (r'\b(Duro\s*[Ss]eal)\b', 'product'),
            (r'\b(W\s*&\s*H)\b', 'brand'),
            (r'\b(Miraflex)\b', 'product_line'),
            (r'\b(Novoflex)\b', 'product_line'),
            (r'\b(Primaflex)\b', 'product_line'),
        ]
        brands = []
        for pattern, tag in brand_patterns:
            match = re.search(pattern, product_name, re.IGNORECASE)
            if match:
                brands.append((match.group(1), tag))

        # Get dimensions (12mm, 40x0.20, etc.)
        dimension_patterns = [
            r'\b(\d{1,3})\s*mm\b',
            r'\b(\d{1,3})\s*x\s*(\d+[.,]\d+)\b',
        ]
        dimensions = []
        for pattern in dimension_patterns:
            matches = re.findall(pattern, product_name, re.IGNORECASE)
            dimensions.extend([str(m) if isinstance(m, str) else 'x'.join(m) for m in matches])

        # Search by brands/key identifiers
        if brands:
            for brand, tag in brands:
                for product in vector_store.products_data:
                    if product.get('id') in seen_ids:
                        continue
                    product_text = f"{product.get('name', '')} {product.get('default_code', '')}".upper()
                    # Normalize brand for matching (remove spaces, case insensitive)
                    brand_normalized = brand.upper().replace(' ', '').replace('&', '')
                    product_normalized = product_text.replace(' ', '').replace('&', '')
                    if brand_normalized in product_normalized:
                        candidates.append(product)
                        seen_ids.add(product.get('id'))
                        if len(candidates) >= max_candidates * 2:  # Get more candidates if we have multiple brand keywords
                            break
                if len(candidates) >= max_candidates * 2:
                    break

        # Search by dimensions if brand didn't yield enough
        if len(candidates) < max_candidates and dimensions:
            for dim in dimensions:
                for product in vector_store.products_data:
                    if product.get('id') in seen_ids:
                        continue
                    product_text = f"{product.get('name', '')} {product.get('default_code', '')}".upper()
                    if dim.upper() in product_text:
                        candidates.append(product)
                        seen_ids.add(product.get('id'))
                        if len(candidates) >= max_candidates:
                            break
                if len(candidates) >= max_candidates:
                    break

        # Search by partial code match
        if product_code and len(candidates) < max_candidates:
            # Extract numeric part from code
            code_numbers = re.findall(r'\d+', product_code)
            for num in code_numbers:
                if len(num) >= 3:  # Only use meaningful numbers
                    for product in vector_store.products_data:
                        if product.get('id') in seen_ids:
                            continue
                        db_code = str(product.get('default_code', ''))
                        if num in db_code:
                            candidates.append(product)
                            seen_ids.add(product.get('id'))
                            if len(candidates) >= max_candidates:
                                break
                if len(candidates) >= max_candidates:
                    break

        # Search by key words in name (last resort)
        if len(candidates) < max_candidates:
            key_words = [w for w in re.findall(r'\b\w{4,}\b', product_name)
                        if w.lower() not in ['with', 'from', 'tape', 'seal', 'blade']]
            for word in key_words[:3]:  # Top 3 key words
                for product in vector_store.products_data:
                    if product.get('id') in seen_ids:
                        continue
                    product_text = f"{product.get('name', '')}".upper()
                    if word.upper() in product_text:
                        candidates.append(product)
                        seen_ids.add(product.get('id'))
                        if len(candidates) >= max_candidates:
                            break
                if len(candidates) >= max_candidates:
                    break

        logger.info(f"   [AI] Found {len(candidates)} candidates for AI matching")
        return candidates[:max_candidates]


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    from retriever_module.vector_store import VectorStore

    print("\n" + "="*80)
    print("AI PRODUCT MATCHING TEST")
    print("="*80)

    vs = VectorStore()
    matcher = AIProductMatcher()

    test_cases = [
        {
            "name": "W&H Miraflex case",
            "product": {
                "name": "Duroseal Dichtungen W&H End seals Miraflex Grau",
                "code": "DF-3068",
                "specifications": "100 Stick im Karton, Grau"
            }
        },
        {
            "name": "3M Transfer tape case",
            "product": {
                "name": "3M Transfer-Klebeband 904-12-G",
                "code": "904-12-G",
                "specifications": "12mm x 44m"
            }
        }
    ]

    for test in test_cases:
        print(f"\n{'='*80}")
        print(f"TEST: {test['name']}")
        print(f"{'='*80}")
        print(f"Product: {test['product']['name']}")
        print(f"Code: {test['product']['code']}")

        # Get candidates
        candidates = matcher.get_relaxed_candidates(
            vs,
            test['product']['name'],
            test['product']['code'],
            max_candidates=5
        )

        if candidates:
            print(f"\nCandidates found: {len(candidates)}")
            for i, c in enumerate(candidates, 1):
                print(f"  {i}. {c['default_code']}: {c['name'][:60]}")

            # AI match
            result = matcher.match_product(test['product'], candidates)

            if result:
                print(f"\nAI MATCH:")
                print(f"  Product: {result['product']['default_code']}")
                print(f"  Name: {result['product']['name'][:60]}")
                print(f"  Confidence: {result['confidence']:.0%}")
                print(f"  Reasoning: {result['reasoning']}")
            else:
                print("\nNo AI match found")
        else:
            print("\nNo candidates found")
