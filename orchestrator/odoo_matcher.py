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

    def __init__(self, odoo_connector):
        """
        Initialize Odoo Matcher

        Args:
            odoo_connector: OdooConnector instance
        """
        self.odoo = odoo_connector

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
            # Use EXTRACTED company name from entities, not JSON match
            extracted_company = entities.get('company_name')
            extracted_email = entities.get('email')
            extracted_phones = entities.get('phone_numbers', [])
            extracted_addresses = entities.get('addresses', [])

            # Extract phone (first one if available)
            extracted_phone = extracted_phones[0] if extracted_phones else None

            # Extract address (first one if available)
            extracted_address = extracted_addresses[0] if extracted_addresses else None

            # Try to extract zip code from address if available
            extracted_zip = None
            if extracted_address:
                import re
                # Look for zip code patterns (5 digits or 5+4 format)
                zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', extracted_address)
                if zip_match:
                    extracted_zip = zip_match.group(1)

            # Filter out SDS (our own company) from customer matching
            excluded_companies = ['SDS', 'SDS GmbH', 'SDS Print Services', 'SDS Print Services GmbH']
            is_sds_company = any(excl.upper() in extracted_company.upper() for excl in excluded_companies) if extracted_company else False

            if extracted_company and not is_sds_company:
                logger.info(f"   [1/2] Searching customer in Odoo...")
                logger.info(f"      Searching in Odoo (company={extracted_company}, email={extracted_email}, phone={extracted_phone}, zip={extracted_zip})...")

                result = self.odoo.query_customer_info(
                    company_name=extracted_company,
                    email=extracted_email,
                    phone=extracted_phone,
                    address=extracted_address,
                    zip_code=extracted_zip
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
                    logger.info(f"      [OK] Customer found in Odoo (ID: {result.get('id')})")
                else:
                    logger.warning(f"      [!] Customer '{extracted_company}' not found in Odoo")
                    odoo_matches['customer'] = {'found': False}
            elif is_sds_company:
                logger.info(f"   [1/2] Skipping SDS company (our own company): {extracted_company}")
                odoo_matches['customer'] = {'found': False, 'reason': 'SDS company excluded'}
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
                                'found': True,
                                'id': results[0].get('id'),
                                'name': results[0].get('name'),
                                'code': results[0].get('default_code'),
                                'match_method': 'json_id_verified',
                                'json_match_score': json_product.get('match_score', 'N/A')
                            })
                            odoo_matches['match_summary']['products_matched'] += 1
                            logger.info(f"         [OK] ID verified in Odoo! (ID: {results[0].get('id')})")
                        else:
                            # ID doesn't exist, fallback to code search
                            logger.info(f"         ID not found, trying by code: {json_product_code}...")
                            results = self.odoo.query_products(product_code=json_product_code)

                            if results:
                                odoo_matches['products'].append({
                                    'found': True,
                                    'id': results[0].get('id'),
                                    'name': results[0].get('name'),
                                    'code': results[0].get('default_code'),
                                    'match_method': 'code_fallback',
                                    'json_match_score': json_product.get('match_score', 'N/A')
                                })
                                odoo_matches['match_summary']['products_matched'] += 1
                                logger.info(f"         [OK] Found by code (ID: {results[0].get('id')})")
                            else:
                                # Final fallback: try by name
                                logger.info(f"         Code not found, trying by name: {json_product_name}...")
                                results = self.odoo.query_products(product_name=json_product_name)

                                if results:
                                    odoo_matches['products'].append({
                                        'found': True,
                                        'id': results[0].get('id'),
                                        'name': results[0].get('name'),
                                        'code': results[0].get('default_code'),
                                        'match_method': 'name_fallback',
                                        'json_match_score': json_product.get('match_score', 'N/A')
                                    })
                                    odoo_matches['match_summary']['products_matched'] += 1
                                    logger.info(f"         [OK] Found by name (ID: {results[0].get('id')})")
                                else:
                                    logger.warning(f"         [!] Product not found in Odoo")
                                    odoo_matches['products'].append({
                                        'found': False,
                                        'id': None,
                                        'name': json_product_name,
                                        'code': json_product_code,
                                        'match_method': 'not_found',
                                        'json_match_score': json_product.get('match_score', 'N/A')
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
                                'found': True,
                                'id': results[0].get('id'),
                                'name': results[0].get('name'),
                                'code': results[0].get('default_code'),
                                'match_method': 'code_no_json_id',
                                'json_match_score': json_product.get('match_score', 'N/A')
                            })
                            odoo_matches['match_summary']['products_matched'] += 1
                            logger.info(f"         [OK] Found by code (ID: {results[0].get('id')})")
                        else:
                            # Try by name
                            results = self.odoo.query_products(product_name=json_product_name)
                            if results:
                                odoo_matches['products'].append({
                                    'found': True,
                                    'id': results[0].get('id'),
                                    'name': results[0].get('name'),
                                    'code': results[0].get('default_code'),
                                    'match_method': 'name_no_json_id',
                                    'json_match_score': json_product.get('match_score', 'N/A')
                                })
                                odoo_matches['match_summary']['products_matched'] += 1
                                logger.info(f"         [OK] Found by name (ID: {results[0].get('id')})")
                            else:
                                logger.warning(f"         [!] Product '{json_product_name}' not found in Odoo")
                                odoo_matches['products'].append({
                                    'found': False,
                                    'id': None,
                                    'name': json_product_name,
                                    'code': json_product_code,
                                    'match_method': 'not_found',
                                    'json_match_score': json_product.get('match_score', 'N/A')
                                })

                # Log summary
                matched = odoo_matches['match_summary']['products_matched']
                total = odoo_matches['match_summary']['products_total']
                match_rate = (matched / total * 100) if total > 0 else 0
                logger.info(f"   [OK] Odoo matching complete: {matched}/{total} products ({match_rate:.0f}%)")

        except Exception as e:
            logger.error(f"   [ERROR] Error matching in Odoo: {e}")

        return odoo_matches
