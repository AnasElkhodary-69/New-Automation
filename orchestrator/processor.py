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
            # Step 1: Classify intent
            logger.info("🤖 [2/4] Classifying intent...")
            intent = self._classify_intent(email)
            logger.info(f"   ✓ Intent: {intent.get('type')} ({intent.get('confidence', 0):.0%} confidence)")

            # Step 2: Extract entities and key information
            logger.info("🤖 [3/4] Extracting entities...")
            entities = self._extract_entities(email)
            entity_count = sum(1 for k, v in entities.items() if v and k not in ['urgency_level', 'sentiment'])
            logger.info(f"   ✓ Extracted {entity_count} entity types")

            # Log detailed extraction counts
            product_count = len(entities.get('product_names', []))
            code_count = len(entities.get('references', []))
            amount_count = len(entities.get('amounts', []))
            logger.info(f"   📦 Products: {product_count}, Codes: {code_count}, Amounts: {amount_count}")

            # Step 3: Retrieve relevant context from JSON files
            context = self._retrieve_context(intent, entities, email)
            logger.info(f"   ✓ Context retrieved from JSON")

            # Step 4: STOP HERE - No response generation
            logger.info("🛑 [4/4] Stopping workflow (no response generation)")

            return {
                'success': True,
                'intent': intent,
                'entities': entities,
                'context': context,
                'response': ''  # No response generated
            }

        except Exception as e:
            logger.error(f"❌ Error processing email: {str(e)}", exc_info=True)
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
        logger.info("🔍 [4/5] Retrieving context from JSON database...")

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

        except Exception as e:
            logger.error(f"❌ Error retrieving context: {str(e)}")

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
            product_codes = entities.get('references', [])

            if product_names:
                logger.info(f"   🔍 Searching {len(product_names)} products in JSON database...")
                matched_products = self.vector_store.search_products_batch(
                    product_names=product_names,
                    product_codes=product_codes,
                    threshold=0.6
                )
                order_context['products'] = matched_products
                logger.info(f"   ✅ Product search complete: {len(matched_products)} matches found")

        except Exception as e:
            logger.error(f"   ❌ Error retrieving order context: {e}")

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
        logger.info("   ⚠️  Invoice data not available in JSON files")

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
            product_codes = entities.get('references', [])

            if product_names:
                matched_products = self.vector_store.search_products_batch(
                    product_names=product_names,
                    product_codes=product_codes,
                    threshold=0.6
                )
                product_context['products'] = matched_products

        except Exception as e:
            logger.error(f"   ❌ Error retrieving product context: {e}")

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
