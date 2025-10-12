"""
Odoo Matcher Module

Handles matching JSON results to actual Odoo database records
Separated from EmailProcessor for better modularity
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OdooMatcher:
    """Handles matching products and customers in Odoo database"""

    def __init__(self, odoo_connector, use_dspy_customer_matching: bool = True):
        """
        Initialize Odoo Matcher

        Args:
            odoo_connector: OdooConnector instance
            use_dspy_customer_matching: If True, use DSPy AI for customer matching (recommended)
        """
        self.odoo = odoo_connector
        self.use_dspy_customer_matching = use_dspy_customer_matching

        # Initialize DSPy customer matcher if enabled
        self.customer_matcher = None
        if use_dspy_customer_matching:
            try:
                from orchestrator.dspy_customer_matcher import CustomerMatcher
                self.customer_matcher = CustomerMatcher(use_chain_of_thought=True)
                logger.info("   [INIT] DSPy Customer Matcher enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize DSPy Customer Matcher: {e}")
                logger.warning("Falling back to direct Odoo matching")
                self.use_dspy_customer_matching = False

    def match_in_odoo(self, context: Dict, entities: Dict) -> Dict:
        """
        Match JSON results to Odoo database records

        Args:
            context: Context with JSON matches
            entities: Extracted entities

        Returns:
            Odoo matching results with IDs
        """
        logger.info("   Matching results in Odoo database...")

        odoo_matches = {
            'customer': None,
            'products': [],
            'match_summary': {
                'customer_matched': False,
                'products_matched': 0,
                'products_total': 0
            }
        }

        try:
            # Match customer in Odoo
            # STRATEGY: Use JSON match first (has Odoo ID), fallback to extracted name
            json_customer = context.get('customer_info')
            extracted_company = entities.get('company_name')
            extracted_email = entities.get('email')

            # Filter out SDS (our own company) from customer matching
            excluded_companies = ['SDS', 'SDS GmbH', 'SDS Print Services', 'SDS Print Services GmbH']
            is_sds_company = any(excl.upper() in extracted_company.upper() for excl in excluded_companies) if extracted_company else False

            if is_sds_company:
                logger.info(f"   [1/2] Skipping SDS company (our own company): {extracted_company}")
                odoo_matches['customer'] = {'found': False, 'reason': 'SDS company excluded'}
            elif json_customer and json_customer.get('id'):
                # JSON match has Odoo ID - but check confidence before accepting
                json_odoo_id = json_customer.get('id')
                json_customer_name = json_customer.get('name')
                json_confidence = json_customer.get('match_score', 1.0)  # VectorStore match score

                logger.info(f"   [1/2] Verifying customer from JSON match (ID: {json_odoo_id}, Name: {json_customer_name}, Confidence: {json_confidence:.0%})...")

                # If JSON confidence is low (<80%), use DSPy AI to verify the match
                if json_confidence < 0.80 and self.use_dspy_customer_matching and self.customer_matcher:
                    logger.info(f"      JSON confidence {json_confidence:.0%} is low, using DSPy AI to verify...")

                    # Try full name search first
                    domain = [['name', 'ilike', extracted_company], ['is_company', '=', True]]
                    candidate_customers = self.odoo.models.execute_kw(
                        self.odoo.db, self.odoo.uid, self.odoo.password,
                        'res.partner', 'search_read',
                        [domain],
                        {'fields': ['id', 'name', 'email', 'phone', 'ref'], 'limit': 10}
                    )

                    # If no results, try broader search (first word only)
                    if not candidate_customers and extracted_company:
                        first_word = extracted_company.split()[0] if extracted_company.split() else extracted_company
                        if len(first_word) >= 3:  # Only if first word is meaningful
                            logger.info(f"      No exact match, trying broader search: '{first_word}'...")
                            domain = [['name', 'ilike', first_word], ['is_company', '=', True]]
                            candidate_customers = self.odoo.models.execute_kw(
                                self.odoo.db, self.odoo.uid, self.odoo.password,
                                'res.partner', 'search_read',
                                [domain],
                                {'fields': ['id', 'name', 'email', 'phone', 'ref', 'city', 'country_id'], 'limit': 10}
                            )

                    if candidate_customers:
                        logger.info(f"      Found {len(candidate_customers)} candidate(s), asking DSPy AI to verify...")
                        dspy_result = self.customer_matcher.match_customer(
                            extracted_company=extracted_company,
                            candidate_customers=candidate_customers,
                            min_confidence=0.70  # Accept subsidiary matches at 70-84% confidence
                        )

                        if dspy_result:
                            odoo_matches['customer'] = {
                                'found': True,
                                'id': dspy_result.get('id'),
                                'name': dspy_result.get('name'),
                                'ref': dspy_result.get('ref', ''),
                                'email': dspy_result.get('email', ''),
                                'phone': dspy_result.get('phone', ''),
                                'match_method': 'dspy_ai_verified_json',
                                'confidence': dspy_result.get('confidence'),
                                'reasoning': dspy_result.get('reasoning', '')[:200]
                            }
                            odoo_matches['match_summary']['customer_matched'] = True
                            logger.info(f"      [OK] DSPy AI selected: {dspy_result.get('name')} (ID: {dspy_result.get('id')}, confidence: {dspy_result.get('confidence'):.0%})")

                            # Log if DSPy corrected the JSON match
                            if dspy_result.get('id') != json_odoo_id:
                                logger.info(f"      [CORRECTED] DSPy rejected JSON match '{json_customer_name}' (ID: {json_odoo_id})")
                        else:
                            logger.warning(f"      [!] DSPy rejected all candidates including JSON match")
                            odoo_matches['customer'] = {'found': False, 'reason': 'DSPy rejected JSON match (low confidence)'}
                    else:
                        # No candidates found, fall back to verifying JSON match
                        logger.warning(f"      No candidates found in Odoo, verifying JSON match anyway...")
                        result = self.odoo.query_customer_info(customer_id=json_odoo_id)
                        if result:
                            odoo_matches['customer'] = {
                                'found': True,
                                'id': result.get('id'),
                                'name': result.get('name'),
                                'ref': result.get('ref', ''),
                                'email': result.get('email', ''),
                                'phone': result.get('phone', '')
                            }
                            odoo_matches['match_summary']['customer_matched'] = True
                            logger.info(f"      [OK] Customer verified in Odoo (ID: {result.get('id')})")
                        else:
                            odoo_matches['customer'] = {'found': False}
                else:
                    # High confidence JSON match or DSPy disabled - verify it exists in Odoo
                    result = self.odoo.query_customer_info(customer_id=json_odoo_id)

                    if result:
                        odoo_matches['customer'] = {
                            'found': True,
                            'id': result.get('id'),
                            'name': result.get('name'),
                            'ref': result.get('ref', ''),
                            'email': result.get('email', ''),
                            'phone': result.get('phone', '')
                        }
                        odoo_matches['match_summary']['customer_matched'] = True
                        logger.info(f"      [OK] Customer verified in Odoo (ID: {result.get('id')})")
                    else:
                        logger.warning(f"      [!] JSON customer ID {json_odoo_id} not found in Odoo, trying extracted name...")
                        # Fallback to extracted name search
                        result = self.odoo.query_customer_info(
                            company_name=extracted_company,
                            email=extracted_email
                        )
                        if result:
                            odoo_matches['customer'] = {
                                'found': True,
                                'id': result.get('id'),
                                'name': result.get('name'),
                                'ref': result.get('ref', ''),
                                'email': result.get('email', ''),
                                'phone': result.get('phone', '')
                            }
                            odoo_matches['match_summary']['customer_matched'] = True
                            logger.info(f"      [OK] Customer found by name (ID: {result.get('id')})")
                        else:
                            logger.warning(f"      [!] Customer '{extracted_company}' not found in Odoo")
                            odoo_matches['customer'] = {'found': False}
            elif extracted_company:
                # No JSON match, search by extracted name with DSPy
                logger.info(f"   [1/2] No JSON match, searching by extracted name in Odoo...")

                # Get candidate customers from Odoo (fuzzy search)
                domain = [['name', 'ilike', extracted_company], ['is_company', '=', True]]
                candidate_customers = self.odoo.models.execute_kw(
                    self.odoo.db, self.odoo.uid, self.odoo.password,
                    'res.partner', 'search_read',
                    [domain],
                    {'fields': ['id', 'name', 'email', 'phone', 'ref'], 'limit': 10}
                )

                if not candidate_customers:
                    logger.warning(f"      [!] No candidate customers found for '{extracted_company}'")
                    odoo_matches['customer'] = {'found': False}
                else:
                    logger.info(f"      Found {len(candidate_customers)} candidate(s)")

                    # Use DSPy AI matcher to pick best match (if enabled)
                    if self.use_dspy_customer_matching and self.customer_matcher:
                        logger.info(f"      Using DSPy AI to select best match...")
                        result = self.customer_matcher.match_customer(
                            extracted_company=extracted_company,
                            candidate_customers=candidate_customers,
                            min_confidence=0.70  # Accept subsidiary matches at 70-84% confidence
                        )

                        if result:
                            odoo_matches['customer'] = {
                                'found': True,
                                'id': result.get('id'),
                                'name': result.get('name'),
                                'ref': result.get('ref', ''),
                                'email': result.get('email', ''),
                                'phone': result.get('phone', ''),
                                'match_method': 'dspy_ai',
                                'confidence': result.get('confidence'),
                                'reasoning': result.get('reasoning', '')[:200]  # Truncate reasoning
                            }
                            odoo_matches['match_summary']['customer_matched'] = True
                            logger.info(f"      [OK] Customer matched by DSPy AI (ID: {result.get('id')}, confidence: {result.get('confidence'):.0%})")
                        else:
                            logger.warning(f"      [!] DSPy rejected all candidates (confidence too low or no match)")
                            odoo_matches['customer'] = {'found': False, 'reason': 'No confident match found'}
                    else:
                        # Fallback: Use first candidate (old behavior)
                        logger.info(f"      Using first candidate (DSPy disabled)")
                        result = candidate_customers[0]
                        odoo_matches['customer'] = {
                            'found': True,
                            'id': result.get('id'),
                            'name': result.get('name'),
                            'ref': result.get('ref', ''),
                            'email': result.get('email', ''),
                            'phone': result.get('phone', ''),
                            'match_method': 'odoo_fuzzy'
                        }
                        odoo_matches['match_summary']['customer_matched'] = True
                        logger.info(f"      [OK] Customer found (ID: {result.get('id')})")
            else:
                logger.warning(f"   [1/2] No company name extracted")
                odoo_matches['customer'] = {'found': False}

            # Match products in Odoo using JSON matches + Odoo ID verification
            # Strategy: Use JSON fuzzy match, then verify the Odoo ID still exists
            json_data = context.get('json_data', {})
            json_products = json_data.get('products', [])

            if json_products:
                logger.info(f"   [2/2] Matching {len(json_products)} products in Odoo...")
                odoo_matches['match_summary']['products_total'] = len(json_products)

                # DEBUG: Log first product structure
                if json_products:
                    logger.info(f"   [DEBUG] First product keys: {list(json_products[0].keys())}")
                    logger.info(f"   [DEBUG] First product sample: id={json_products[0].get('id')}, code={json_products[0].get('default_code')}")

                for idx, json_product in enumerate(json_products, 1):
                    # Get the Odoo ID from JSON match
                    json_odoo_id = json_product.get('id')
                    json_product_name = json_product.get('name', 'Unknown')[:50]
                    json_product_code = json_product.get('default_code', 'N/A')

                    if json_odoo_id:
                        # Strategy 1: Verify JSON's Odoo ID still exists in current Odoo
                        logger.info(f"      [{idx}] Verifying JSON Odoo ID {json_odoo_id} (code: {json_product_code})...")
                        results = self.odoo.query_products(product_id=json_odoo_id)

                        if results:
                            # ID still exists in Odoo - use it!
                            odoo_matches['products'].append({
                                'json_product': json_product,
                                'odoo_product': results[0],
                                'match_method': 'json_id_verified',
                                'extracted_name': json_product.get('extracted_product_name', json_product_name)
                            })
                            odoo_matches['match_summary']['products_matched'] += 1
                            logger.info(f"         [OK] ID verified in Odoo! (ID: {results[0].get('id')})")
                        else:
                            # ID doesn't exist, fallback to code search
                            logger.info(f"         ID not found, trying by code: {json_product_code}...")
                            results = self.odoo.query_products(product_code=json_product_code)

                            if results:
                                odoo_matches['products'].append({
                                    'json_product': json_product,
                                    'odoo_product': results[0],
                                    'match_method': 'code_fallback',
                                    'extracted_name': json_product.get('extracted_product_name', json_product_name)
                                })
                                odoo_matches['match_summary']['products_matched'] += 1
                                logger.info(f"         [OK] Found by code (ID: {results[0].get('id')})")
                            else:
                                # Final fallback: try by name
                                logger.info(f"         Code not found, trying by name: {json_product_name}...")
                                results = self.odoo.query_products(product_name=json_product_name)

                                if results:
                                    odoo_matches['products'].append({
                                        'json_product': json_product,
                                        'odoo_product': results[0],
                                        'match_method': 'name_fallback',
                                        'extracted_name': json_product.get('extracted_product_name', json_product_name)
                                    })
                                    odoo_matches['match_summary']['products_matched'] += 1
                                    logger.info(f"         [OK] Found by name (ID: {results[0].get('id')})")
                                else:
                                    logger.warning(f"         [!] Product not found in Odoo")
                                    odoo_matches['products'].append({
                                        'json_product': json_product,
                                        'odoo_product': None,
                                        'match_method': 'not_found',
                                        'extracted_name': json_product.get('extracted_product_name', json_product_name)
                                    })
                    else:
                        # No JSON ID, try by code or name
                        logger.info(f"      [{idx}] No JSON ID, searching by code/name...")

                        # Try code first
                        results = []
                        if json_product_code and json_product_code != 'N/A':
                            results = self.odoo.query_products(product_code=json_product_code)

                        if results:
                            odoo_matches['products'].append({
                                'json_product': json_product,
                                'odoo_product': results[0],
                                'match_method': 'code_no_json_id',
                                'extracted_name': json_product.get('extracted_product_name', json_product_name)
                            })
                            odoo_matches['match_summary']['products_matched'] += 1
                            logger.info(f"         [OK] Found by code (ID: {results[0].get('id')})")
                        else:
                            # Try by name
                            results = self.odoo.query_products(product_name=json_product_name)
                            if results:
                                odoo_matches['products'].append({
                                    'json_product': json_product,
                                    'odoo_product': results[0],
                                    'match_method': 'name_no_json_id',
                                    'extracted_name': json_product.get('extracted_product_name', json_product_name)
                                })
                                odoo_matches['match_summary']['products_matched'] += 1
                                logger.info(f"         [OK] Found by name (ID: {results[0].get('id')})")
                            else:
                                logger.warning(f"         [!] Product '{json_product_name}' not found in Odoo")
                                odoo_matches['products'].append({
                                    'json_product': json_product,
                                    'odoo_product': None,
                                    'match_method': 'not_found',
                                    'extracted_name': json_product.get('extracted_product_name', json_product_name)
                                })

                # Log summary
                matched = odoo_matches['match_summary']['products_matched']
                total = odoo_matches['match_summary']['products_total']
                match_rate = (matched / total * 100) if total > 0 else 0
                logger.info(f"   [OK] Odoo matching complete: {matched}/{total} products ({match_rate:.0f}%)")

        except Exception as e:
            logger.error(f"   [ERROR] Error matching in Odoo: {e}")

        return odoo_matches
