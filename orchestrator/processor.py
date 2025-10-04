"""
Email Processor Module

Orchestrates the email processing workflow:
1. Parse email intent
2. Extract relevant information
3. Retrieve context from Odoo and vector store
4. Coordinate with Claude agent for response generation
"""

import logging
from typing import Dict, List, Optional, Any
from utils.step_logger import StepLogger

logger = logging.getLogger(__name__)


class EmailProcessor:
    """Main processor for coordinating email handling workflow"""

    def __init__(self, odoo_connector, vector_store, ai_agent):
        """
        Initialize Email Processor

        Args:
            odoo_connector: Instance of OdooConnector
            vector_store: Instance of VectorStore
            ai_agent: Instance of AI Agent (MistralAgent or ClaudeAgent)
        """
        self.odoo = odoo_connector
        self.vector_store = vector_store
        self.ai_agent = ai_agent
        self.step_logger = StepLogger()

        logger.info("Email Processor initialized")

    def process_email(self, email: Dict) -> Dict:
        """
        Main processing method for incoming email (NEW JSON-BASED WORKFLOW)

        Args:
            email: Email dictionary with subject, body, from, etc.

        Returns:
            Processing result dictionary
        """
        try:
            # Initialize step logging for this email
            email_id = email.get('message_id', email.get('id', 'unknown'))
            self.step_logger.start_email_log(email_id)

            # LOG STEP 1: Email Parsing
            logger.info("[LOG] [1/9] Logging email parsing...")
            self.step_logger.log_step_1_email_parsing(email)

            # Step 2: Classify intent
            logger.info("[AI] [2/9] Classifying intent...")
            intent = self._classify_intent(email)
            logger.info(f"   [OK] Intent: {intent.get('type')} ({intent.get('confidence', 0):.0%} confidence)")

            # Step 3: Extract entities and key information
            logger.info("[AI] [3/9] Extracting entities...")
            entities = self._extract_entities(email)
            entity_count = sum(1 for k, v in entities.items() if v and k not in ['urgency_level', 'sentiment'])
            logger.info(f"   [OK] Extracted {entity_count} entity types")

            # Log detailed extraction counts
            product_count = len(entities.get('product_names', []))
            code_count = len(entities.get('references', []))
            amount_count = len(entities.get('amounts', []))
            logger.info(f"   [ITEMS] Products: {product_count}, Codes: {code_count}, Amounts: {amount_count}")

            # LOG STEP 2: Entity Extraction
            logger.info("[LOG] [4/9] Logging entity extraction...")
            self.step_logger.log_step_2_entity_extraction(intent, entities)

            # Step 4: Retrieve relevant context from JSON files
            logger.info("[SEARCH] [5/9] Retrieving context from JSON database...")
            context, search_criteria, match_stats = self._retrieve_context_with_logging(intent, entities, email)
            logger.info(f"   [OK] Context retrieved from JSON")

            # Step 5: Match JSON results in Odoo database
            logger.info("[MATCH] [6/9] Matching results in Odoo database...")
            odoo_matches = self._match_in_odoo(context, entities)
            logger.info(f"   [OK] Odoo matching complete")

            # Step 6: Log Odoo matching results
            logger.info("[LOG] [7/9] Logging Odoo matching results...")
            self.step_logger.log_step_5_odoo_matching(odoo_matches)

            # Step 7: NEW - Create sales order in Odoo
            logger.info("[ORDER] [8/9] Creating sales order in Odoo...")
            order_result = self._create_order_in_odoo(odoo_matches, entities, email)
            logger.info(f"   [OK] Order creation {'complete' if order_result else 'skipped'}")

            # Step 8: Log order creation results
            if order_result:
                logger.info("[LOG] [9/9] Logging order creation results...")
                self.step_logger.log_step_6_order_creation(order_result)

            # Get token usage stats
            token_stats = self.ai_agent.get_token_stats()

            # Log the directory where step logs were saved
            log_dir = self.step_logger.get_current_log_dir()
            if log_dir:
                logger.info(f"[SAVE] Step logs saved to: {log_dir}")

            return {
                'success': True,
                'intent': intent,
                'entities': entities,
                'context': context,
                'odoo_matches': odoo_matches,
                'order_created': order_result,  # NEW: Created order info
                'response': '',  # No response generated
                'token_usage': token_stats,
                'step_log_dir': log_dir
            }

        except Exception as e:
            logger.error(f"[ERROR] Error processing email: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _classify_intent(self, email: Dict) -> Dict:
        """
        Classify the intent of the email

        Args:
            email: Email dictionary

        Returns:
            Intent classification result
        """
        logger.info("Classifying email intent...")

        try:
            intent = self.ai_agent.classify_intent(
                subject=email.get('subject', ''),
                body=email.get('body', '')
            )
            return intent
        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return {
                'type': 'unknown',
                'confidence': 0.0,
                'sub_type': None
            }

    def _extract_entities(self, email: Dict) -> Dict:
        """
        Extract key entities from email

        Args:
            email: Email dictionary

        Returns:
            Extracted entities
        """
        logger.info("Extracting entities from email...")

        try:
            # Add customer email to entities
            entities = self.ai_agent.extract_entities(
                text=email.get('body', '')
            )
            entities['customer_email'] = email.get('from')
            return entities
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {
                'customer_email': email.get('from'),
                'order_numbers': [],
                'product_names': [],
                'dates': [],
                'amounts': [],
                'references': []
            }

    def _retrieve_context_with_logging(self, intent: Dict, entities: Dict, email: Dict) -> tuple:
        """
        Retrieve context and log RAG input/output steps

        Args:
            intent: Classified intent
            entities: Extracted entities
            email: Original email

        Returns:
            Tuple of (context, search_criteria, match_statistics)
        """
        # Prepare search criteria for logging
        search_criteria = {
            'customer_search': {
                'company_name': entities.get('company_name', ''),
                'customer_name': entities.get('customer_name', ''),
                'email': entities.get('customer_email', '')
            },
            'product_search': {
                'product_names': entities.get('product_names', []),
                'product_codes': entities.get('product_codes', [])
            },
            'intent_type': intent.get('type')
        }

        # LOG STEP 3: RAG Input
        self.step_logger.log_step_3_rag_input(intent, entities, search_criteria)

        # Perform actual context retrieval
        context = self._retrieve_context(intent, entities, email)

        # Gather match statistics
        match_stats = {
            'customer_matched': context.get('customer_info') is not None,
            'products_found': len(context.get('json_data', {}).get('products', [])),
            'invoices_found': len(context.get('json_data', {}).get('invoices', [])),
            'payment_status_found': len(context.get('json_data', {}).get('payment_status', []))
        }

        # LOG STEP 4: RAG Output
        self.step_logger.log_step_4_rag_output(context, match_stats)

        return context, search_criteria, match_stats

    def _retrieve_context(self, intent: Dict, entities: Dict, email: Dict) -> Dict:
        """
        Retrieve relevant context from JSON files (new RAG workflow)

        Args:
            intent: Classified intent
            entities: Extracted entities
            email: Original email

        Returns:
            Retrieved context dictionary
        """

        context = {
            'json_data': {},
            'customer_info': None
        }

        try:
            # Retrieve customer information using data from email body/signature
            # Priority: company_name > customer_name > email (for reply-to only)
            customer_email = entities.get('customer_email')  # For reply-to purposes
            customer_name = entities.get('customer_name', '')
            company_name = entities.get('company_name', '')

            logger.info(f"   [CUSTOMER SEARCH] Criteria:")
            if company_name:
                logger.info(f"      Company: '{company_name}'")
            if customer_name:
                logger.info(f"      Contact: '{customer_name}'")
            if customer_email:
                logger.info(f"      Email: '{customer_email}'")
            if not company_name and not customer_name and not customer_email:
                logger.warning(f"      No customer information extracted from email")

            # Search in JSON files using vector store
            context['customer_info'] = self.vector_store.search_customer(
                company_name=company_name if company_name else None,
                customer_name=customer_name if customer_name else None,
                email=customer_email,
                threshold=0.6
            )

            # Enrich customer info with data extracted from email body if database fields are missing
            if context['customer_info']:
                customer = context['customer_info']

                # Fill in email if missing in database (from email body/signature, NOT sender field)
                customer_emails = entities.get('customer_emails', [])  # Emails extracted from body
                if (not customer.get('email') or customer.get('email') == False) and customer_emails:
                    customer['email'] = customer_emails[0]
                    logger.info(f"      [ENRICHED] Added email from body: {customer_emails[0]}")

                # Fill in phone if missing in database (extracted from email body/signature)
                phone_numbers = entities.get('phone_numbers', [])
                if (not customer.get('phone') or customer.get('phone') == False) and phone_numbers:
                    customer['phone'] = phone_numbers[0]  # Use first extracted phone
                    logger.info(f"      [ENRICHED] Added phone from body: {phone_numbers[0]}")

                # Fill in address/city if missing (extracted from email body/signature)
                addresses = entities.get('addresses', [])
                if (not customer.get('city') or customer.get('city') == False) and addresses:
                    customer['city'] = addresses[0]
                    logger.info(f"      [ENRICHED] Added address from body: {addresses[0]}")

            # Based on intent, retrieve specific data
            intent_type = intent.get('type')

            if intent_type == 'order_inquiry':
                context['json_data'] = self._retrieve_order_context_json(entities)

            elif intent_type == 'invoice_request':
                context['json_data'] = self._retrieve_invoice_context_json(entities)

            elif intent_type == 'product_inquiry':
                context['json_data'] = self._retrieve_product_context_json(entities)

            elif intent_type == 'general_inquiry':
                # Fallback: If general_inquiry but products were extracted, search them
                logger.info("   [WARNING]  Intent: general_inquiry - checking if products can be searched")
                context['json_data'] = self._retrieve_order_context_json(entities)

            else:
                # Default case: If products/codes were extracted, always try to search
                product_names = entities.get('product_names', [])
                product_codes = entities.get('product_codes', [])
                if product_names or product_codes:
                    logger.info(f"   [WARNING]  Unknown intent '{intent_type}' but {len(product_names)} products extracted - searching anyway")
                    context['json_data'] = self._retrieve_order_context_json(entities)

        except Exception as e:
            logger.error(f"[ERROR] Error retrieving context: {str(e)}")

        return context

    def _retrieve_order_context_json(self, entities: Dict) -> Dict:
        """
        Retrieve order-related context from JSON

        Args:
            entities: Extracted entities

        Returns:
            Order context
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
                logger.info(f"   [SEARCH] Searching {len(product_names)} products in JSON database...")
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

    def _retrieve_invoice_context_json(self, entities: Dict) -> Dict:
        """
        Retrieve invoice-related context from JSON

        Args:
            entities: Extracted entities

        Returns:
            Invoice context (currently empty, no invoice data in JSON)
        """
        logger.info("   Retrieving invoice context from JSON...")

        invoice_context = {
            'invoices': [],
            'payment_status': []
        }

        # Note: JSON files don't contain invoice data
        # This is placeholder for future expansion
        logger.info("   [WARNING]  Invoice data not available in JSON files")

        return invoice_context

    def _retrieve_product_context_json(self, entities: Dict) -> Dict:
        """
        Retrieve product-related context from JSON

        Args:
            entities: Extracted entities

        Returns:
            Product context
        """
        logger.info("   Retrieving product context from JSON...")

        product_context = {
            'products': [],
            'pricing': [],
            'availability': []
        }

        try:
            product_names = entities.get('product_names', [])
            product_codes = entities.get('product_codes', [])

            if product_names:
                matched_products = self.vector_store.search_products_batch(
                    product_names=product_names,
                    product_codes=product_codes,
                    threshold=0.6
                )
                product_context['products'] = matched_products

        except Exception as e:
            logger.error(f"   [ERROR] Error retrieving product context: {e}")

        return product_context

    def _retrieve_order_context(self, entities: Dict, customer_info: Optional[Dict]) -> Dict:
        """
        Retrieve order-related context

        Args:
            entities: Extracted entities
            customer_info: Customer information

        Returns:
            Order context
        """
        logger.info("Retrieving order context...")

        order_context = {
            'orders': [],
            'order_lines': [],
            'shipping_info': [],
            'products': []  # Add products to order context
        }

        try:
            if customer_info:
                customer_id = customer_info.get('id')
                order_context['orders'] = self.odoo.query_orders(customer_id)

            # If specific order numbers mentioned
            for order_num in entities.get('order_numbers', []):
                order = self.odoo.search_by_reference(order_num)
                if order:
                    order_context['orders'].append(order)

            # Also search for products mentioned in order inquiries
            # This helps validate new orders and check product availability
            product_names = entities.get('product_names', [])
            product_codes = entities.get('references', [])  # Product codes like "G-25-20-125-17"

            if product_names:
                logger.info(f"Searching for {len(product_names)} products in Odoo...")
                logger.info(f"Available product codes: {product_codes}")

                # Build a mapping to try matching product codes with product names
                for idx, product_name in enumerate(product_names):
                    products = []

                    # Try to find a matching product code for this product
                    # Product codes often appear in the same order as product names
                    product_code = product_codes[idx] if idx < len(product_codes) else None

                    # Strategy 1: Search by product code first (most reliable)
                    if product_code:
                        logger.info(f"Trying code '{product_code}' for product '{product_name}'")
                        products = self.odoo.query_products(product_code=product_code)

                    # Strategy 2: Search by product name if code search failed
                    if not products:
                        products = self.odoo.query_products(product_name=product_name)

                    if products:
                        order_context['products'].extend(products)
                        logger.info(f"Found {len(products)} match(es) for '{product_name}'")
                    else:
                        logger.warning(f"No match found for product: '{product_name}'")

        except Exception as e:
            logger.error(f"Error retrieving order context: {e}")

        return order_context

    def _retrieve_invoice_context(self, entities: Dict, customer_info: Optional[Dict]) -> Dict:
        """
        Retrieve invoice-related context

        Args:
            entities: Extracted entities
            customer_info: Customer information

        Returns:
            Invoice context
        """
        logger.info("Retrieving invoice context...")

        invoice_context = {
            'invoices': [],
            'payment_status': []
        }

        try:
            if customer_info:
                customer_id = customer_info.get('id')
                invoice_context['invoices'] = self.odoo.query_invoices(customer_id)

        except Exception as e:
            logger.error(f"Error retrieving invoice context: {e}")

        return invoice_context

    def _retrieve_product_context(self, entities: Dict) -> Dict:
        """
        Retrieve product-related context

        Args:
            entities: Extracted entities

        Returns:
            Product context
        """
        logger.info("Retrieving product context...")

        product_context = {
            'products': [],
            'pricing': [],
            'availability': []
        }

        try:
            product_names = entities.get('product_names', [])
            product_codes = entities.get('references', [])

            logger.info(f"Searching for {len(product_names)} products in Odoo...")
            logger.info(f"Available product codes: {product_codes}")

            for idx, product_name in enumerate(product_names):
                products = []

                # Try to find matching product code
                product_code = product_codes[idx] if idx < len(product_codes) else None

                # Strategy 1: Search by product code first
                if product_code:
                    logger.info(f"Trying code '{product_code}' for product '{product_name}'")
                    products = self.odoo.query_products(product_code=product_code)

                # Strategy 2: Search by product name
                if not products:
                    products = self.odoo.query_products(product_name=product_name)

                if products:
                    product_context['products'].extend(products)
                    logger.info(f"Found {len(products)} match(es) for '{product_name}'")
                else:
                    logger.warning(f"No match found for product: '{product_name}'")

        except Exception as e:
            logger.error(f"Error retrieving product context: {e}")

        return product_context

    def _match_in_odoo(self, context: Dict, entities: Dict) -> Dict:
        """
        Match JSON results in Odoo database to get real Odoo IDs

        Args:
            context: Context from JSON matching (contains customer_info and products)
            entities: Extracted entities

        Returns:
            Dictionary with Odoo matches
        """
        logger.info("   Matching JSON results in Odoo database...")

        odoo_matches = {
            'customer': None,
            'products': [],
            'match_summary': {
                'customer_matched': False,
                'products_total': 0,
                'products_matched': 0,
                'products_failed': 0
            }
        }

        try:
            # Match Customer in Odoo
            customer_info = context.get('customer_info')
            if customer_info:
                logger.info(f"   [CUSTOMER] Searching Odoo for: {customer_info.get('name')}")

                # Strategy 1: Try by customer reference (most reliable)
                customer_ref = customer_info.get('ref')
                if customer_ref:
                    logger.info(f"      Trying ref: '{customer_ref}'")
                    # Search by reference in Odoo
                    odoo_customer = self.odoo.query_customer_info(
                        customer_name=customer_ref  # Try ref as name search
                    )
                    if odoo_customer:
                        odoo_matches['customer'] = odoo_customer
                        odoo_matches['match_summary']['customer_matched'] = True
                        logger.info(f"      [OK] Found by ref: {odoo_customer.get('name')} (ID: {odoo_customer.get('id')})")

                # Strategy 2: Try by company name
                if not odoo_matches['customer']:
                    company_name = customer_info.get('name')
                    if company_name:
                        logger.info(f"      Trying company name: '{company_name}'")
                        odoo_customer = self.odoo.query_customer_info(
                            company_name=company_name
                        )
                        if odoo_customer:
                            odoo_matches['customer'] = odoo_customer
                            odoo_matches['match_summary']['customer_matched'] = True
                            logger.info(f"      [OK] Found by name: {odoo_customer.get('name')} (ID: {odoo_customer.get('id')})")

                # Strategy 3: Try by email (fallback)
                if not odoo_matches['customer']:
                    email = customer_info.get('email') or entities.get('customer_email')
                    if email:
                        logger.info(f"      Trying email: '{email}'")
                        odoo_customer = self.odoo.query_customer_info(email=email)
                        if odoo_customer:
                            odoo_matches['customer'] = odoo_customer
                            odoo_matches['match_summary']['customer_matched'] = True
                            logger.info(f"      [OK] Found by email: {odoo_customer.get('name')} (ID: {odoo_customer.get('id')})")

                if not odoo_matches['customer']:
                    logger.warning(f"      [X] Customer not found in Odoo")
            else:
                logger.warning(f"   [CUSTOMER] No customer from JSON to search in Odoo")

            # Match Products in Odoo
            json_products = context.get('json_data', {}).get('products', [])
            odoo_matches['match_summary']['products_total'] = len(json_products)

            if json_products:
                logger.info(f"   [PRODUCTS] Searching Odoo for {len(json_products)} products...")

                for idx, json_product in enumerate(json_products, 1):
                    product_code = json_product.get('default_code')
                    product_name = json_product.get('name')
                    extracted_name = json_product.get('extracted_product_name', product_name)

                    logger.info(f"      [{idx}] Searching: {extracted_name[:50]}...")

                    odoo_product = None

                    # Strategy 1: Search by product code (most reliable)
                    if product_code:
                        logger.info(f"          Trying code: '{product_code}'")
                        products = self.odoo.query_products(product_code=product_code)
                        if products:
                            odoo_product = products[0]  # Take first match
                            logger.info(f"          [OK] Found by code: {odoo_product.get('name')[:50]} (ID: {odoo_product.get('id')})")

                    # Strategy 2: Search by product name
                    if not odoo_product and product_name:
                        logger.info(f"          Trying name: '{product_name[:40]}'")
                        products = self.odoo.query_products(product_name=product_name)
                        if products:
                            odoo_product = products[0]  # Take first match
                            logger.info(f"          [OK] Found by name: {odoo_product.get('name')[:50]} (ID: {odoo_product.get('id')})")

                    if odoo_product:
                        # Store matched product with JSON context
                        odoo_matches['products'].append({
                            'json_product': json_product,
                            'odoo_product': odoo_product,
                            'extracted_name': extracted_name,
                            'match_method': 'code' if product_code and products else 'name'
                        })
                        odoo_matches['match_summary']['products_matched'] += 1
                    else:
                        logger.warning(f"          [X] Product not found in Odoo")
                        odoo_matches['match_summary']['products_failed'] += 1
                        # Still store the failed match for reference
                        odoo_matches['products'].append({
                            'json_product': json_product,
                            'odoo_product': None,
                            'extracted_name': extracted_name,
                            'match_method': None
                        })
            else:
                logger.info(f"   [PRODUCTS] No products from JSON to search in Odoo")

            # Summary
            logger.info(f"   [OK] Odoo Matching Summary:")
            logger.info(f"      Customer: {'[OK] Matched' if odoo_matches['match_summary']['customer_matched'] else '[X] Not found'}")
            logger.info(f"      Products: {odoo_matches['match_summary']['products_matched']}/{odoo_matches['match_summary']['products_total']} matched")

        except Exception as e:
            logger.error(f"   [X] Error matching in Odoo: {str(e)}", exc_info=True)

        return odoo_matches

    def _create_order_in_odoo(self, odoo_matches: Dict, entities: Dict, email: Dict) -> Optional[Dict]:
        """
        Create sales order in Odoo using matched products and customer

        Args:
            odoo_matches: Odoo matching results (customer + products with IDs)
            entities: Extracted entities from email
            email: Original email data

        Returns:
            Dictionary with created order info or None if not created
        """
        logger.info("   Preparing sales order for Odoo...")

        try:
            # Check if customer matched
            odoo_customer = odoo_matches.get('customer')
            if not odoo_customer:
                logger.warning("   [X] Cannot create order: Customer not found in Odoo")
                return {
                    'created': False,
                    'reason': 'customer_not_found',
                    'message': 'Customer not found in Odoo database'
                }

            customer_id = odoo_customer.get('id')
            logger.info(f"   Customer ID: {customer_id} ({odoo_customer.get('name')})")

            # Prepare order lines from matched products
            order_lines = []
            product_matches = odoo_matches.get('products', [])

            # Get quantities and prices from entities
            product_quantities = entities.get('product_quantities', [])
            product_prices = entities.get('product_prices', [])
            product_names_extracted = entities.get('product_names', [])

            # Build a map from extracted name to quantity/price
            qty_map = {}
            price_map = {}
            for idx, name in enumerate(product_names_extracted):
                if idx < len(product_quantities):
                    qty_map[name] = product_quantities[idx]
                if idx < len(product_prices):
                    price_map[name] = product_prices[idx]

            for match in product_matches:
                odoo_product = match.get('odoo_product')
                if not odoo_product:
                    logger.warning(f"   Skipping product: Not found in Odoo")
                    continue

                # Get the template ID (from product.template query)
                product_template_id = odoo_product.get('id')

                # Extract product.product ID from product_variant_id field if available
                # In Odoo, product_variant_id is typically [id, name] or just an int
                product_id = None
                product_variant_id = odoo_product.get('product_variant_id')
                if isinstance(product_variant_id, list) and len(product_variant_id) > 0:
                    product_id = product_variant_id[0]  # Extract ID from [id, name]
                elif isinstance(product_variant_id, int) and product_variant_id:
                    product_id = product_variant_id

                extracted_name = match.get('extracted_name', '')

                # Get quantity and price
                quantity = qty_map.get(extracted_name, 1)
                price = price_map.get(extracted_name)

                # Use extracted price if available, otherwise use Odoo price
                if price is None or price == 0:
                    price = odoo_product.get('list_price') or odoo_product.get('standard_price', 0)

                # Build order line with either product_id or product_template_id
                line_data = {
                    'quantity': quantity,
                    'price_unit': price,
                    'name': odoo_product.get('name')
                }

                # Prefer product_id if available, otherwise use product_template_id
                if product_id:
                    line_data['product_id'] = product_id
                else:
                    line_data['product_template_id'] = product_template_id

                order_lines.append(line_data)

                display_id = product_id if product_id else f"T{product_template_id}"
                logger.info(f"      + Product {display_id}: Qty {quantity} @ €{price:.2f}")

            if not order_lines:
                logger.warning("   [X] Cannot create order: No products matched")
                return {
                    'created': False,
                    'reason': 'no_products',
                    'message': 'No products found in Odoo to create order'
                }

            # Prepare additional order data
            order_data = {}

            # Add date if available
            dates = entities.get('dates', [])
            if dates:
                # Note: Odoo expects date in YYYY-MM-DD format
                # For now, we'll skip date parsing to avoid format issues
                pass

            # Add customer reference if available
            references = entities.get('references', [])
            if references:
                order_data['client_order_ref'] = references[0]

            # Add note with email subject
            order_data['note'] = f"Created from email: {email.get('subject', 'No subject')}"

            # Create the order
            logger.info(f"   Creating order with {len(order_lines)} line(s)...")
            order_info = self.odoo.create_sale_order(
                customer_id=customer_id,
                order_lines=order_lines,
                order_data=order_data
            )

            if order_info:
                return {
                    'created': True,
                    'order_id': order_info.get('id'),
                    'order_name': order_info.get('name'),
                    'amount_total': order_info.get('amount_total'),
                    'state': order_info.get('state'),
                    'line_count': order_info.get('line_count'),
                    'customer_id': customer_id,
                    'customer_name': odoo_customer.get('name')
                }
            else:
                return {
                    'created': False,
                    'reason': 'creation_failed',
                    'message': 'Failed to create order in Odoo'
                }

        except Exception as e:
            logger.error(f"   [X] Error creating order in Odoo: {str(e)}", exc_info=True)
            return {
                'created': False,
                'reason': 'exception',
                'message': str(e)
            }

    def _generate_response(
        self,
        email: Dict,
        intent: Dict,
        entities: Dict,
        context: Dict
    ) -> str:
        """
        Generate response using Claude agent

        Args:
            email: Original email
            intent: Classified intent
            entities: Extracted entities
            context: Retrieved context

        Returns:
            Generated response text
        """
        logger.info("Generating response using AI agent...")

        try:
            response = self.ai_agent.generate_response(
                email=email,
                intent=intent,
                entities=entities,
                context=context
            )
            return response
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Thank you for your email. We'll get back to you shortly."

    def validate_response(self, response: str) -> Dict:
        """
        Validate generated response before sending

        Args:
            response: Generated response text

        Returns:
            Validation result
        """
        logger.info("Validating response...")

        warnings = []
        suggestions = []

        # Check length
        if len(response) < 50:
            warnings.append("Response is very short")
        if len(response) > 2000:
            warnings.append("Response is very long")

        # Check for placeholder text
        if 'TODO' in response or 'PLACEHOLDER' in response:
            warnings.append("Response contains placeholder text")

        return {
            'valid': len(warnings) == 0,
            'warnings': warnings,
            'suggestions': suggestions
        }

    def log_interaction(self, email: Dict, result: Dict):
        """
        Log the interaction for analysis and training

        Args:
            email: Original email
            result: Processing result
        """
        logger.info("Logging interaction...")
        # TODO: Implement interaction logging to database or file
        pass
