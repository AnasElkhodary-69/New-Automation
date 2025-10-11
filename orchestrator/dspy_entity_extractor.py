"""
DSPy Entity Extractor

Replaces manual prompt engineering for entity extraction with
DSPy's declarative approach using structured signatures.
"""

import logging
import json
from typing import Dict, List, Optional
import dspy
from orchestrator.dspy_signatures import ExtractOrderEntities, ConfirmAllProducts, ClassifyEmailIntent

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    DSPy-based entity extractor for order emails.

    This replaces the manual 108-line extraction prompt with a structured,
    optimizable DSPy module that extracts:
    - Customer information (name, company, email, phone, address)
    - Product list (name, code, quantity, price, specifications)
    - Order details (order_number, dates, urgency, terms, notes)
    """

    def __init__(self, use_chain_of_thought: bool = True):
        """
        Initialize entity extractor

        Args:
            use_chain_of_thought: If True, use ChainOfThought for better reasoning
        """
        if use_chain_of_thought:
            self.extractor = dspy.ChainOfThought(ExtractOrderEntities)
            self.intent_classifier = dspy.ChainOfThought(ClassifyEmailIntent)
            self.product_matcher = dspy.ChainOfThought(ConfirmAllProducts)
            logger.info("Entity extractor initialized with ChainOfThought")
        else:
            self.extractor = dspy.Predict(ExtractOrderEntities)
            self.intent_classifier = dspy.Predict(ClassifyEmailIntent)
            self.product_matcher = dspy.Predict(ConfirmAllProducts)
            logger.info("Entity extractor initialized with Predict")

    def extract(self, email_text: str) -> Dict:
        """
        Extract entities from email text using DSPy

        Args:
            email_text: Complete email body including attachments

        Returns:
            Dictionary with extracted entities in legacy format:
            {
                'customer_name': str,
                'company_name': str,
                'email': str,
                'phone': str,
                'address': str,
                'product_names': List[str],
                'product_codes': List[str],
                'quantities': List[int],
                'prices': List[float],
                'order_number': str,
                'order_date': str,
                'delivery_date': str,
                'urgency': str,
                'notes': str
            }
        """
        try:
            logger.debug(f"Extracting entities from email ({len(email_text)} chars)")

            # DEBUG: Log first 3000 chars to check for dimensions
            logger.debug(f"Email text preview (first 3000 chars):\n{email_text[:3000]}")

            # Call DSPy module
            result = self.extractor(email_text=email_text)

            # Parse JSON outputs
            customer_info = self._parse_json(result.customer_json, {})
            products = self._parse_json(result.products_json, [])
            order_info = self._parse_json(result.order_info_json, {})

            # DEBUG: Log what DSPy returned
            logger.debug(f"[DEBUG] DSPy returned {len(products)} products")
            logger.debug(f"[DEBUG] Raw products_json: {result.products_json[:500]}")
            if products:
                logger.debug(f"[DEBUG] First product keys: {list(products[0].keys())}")
                logger.debug(f"[DEBUG] First product: {products[0]}")

            # Convert to legacy format for backward compatibility
            entities = self._convert_to_legacy_format(
                customer_info,
                products,
                order_info
            )

            # POST-PROCESSING: Extract dimensions from email text and add to product names
            entities = self._post_process_add_dimensions(entities, email_text)

            # Log summary
            product_count = len(entities.get('product_names', []))
            logger.info(f"Entities extracted: {product_count} products, customer info, order details")
            logger.debug(f"Customer: {entities.get('company_name', 'N/A')}")
            logger.debug(f"Products: {entities.get('product_names', [])[:3]}...")  # First 3

            return entities

        except Exception as e:
            logger.error(f"Error in entity extraction: {e}", exc_info=True)
            # Return empty structure on failure
            return self._get_empty_entities()

    def _parse_json(self, json_str: str, default):
        """
        Safely parse JSON string

        Args:
            json_str: JSON string to parse
            default: Default value if parsing fails

        Returns:
            Parsed JSON or default value
        """
        try:
            # Clean markdown code blocks if present
            if '```json' in json_str:
                json_str = json_str.split('```json')[1].split('```')[0].strip()
            elif '```' in json_str:
                json_str = json_str.split('```')[1].split('```')[0].strip()

            return json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return default

    def _convert_to_legacy_format(
        self,
        customer_info: Dict,
        products: List[Dict],
        order_info: Dict
    ) -> Dict:
        """
        Convert DSPy output to legacy format for backward compatibility

        Args:
            customer_info: Customer information dict
            products: List of product dicts
            order_info: Order information dict

        Returns:
            Dictionary in legacy format
        """
        # Extract product lists
        product_names = [p.get('name', '') for p in products]
        product_codes = [p.get('code', '') for p in products]
        quantities = [p.get('quantity', 0) for p in products]
        prices = [p.get('unit_price', 0.0) for p in products]

        # DEBUG
        logger.debug(f"[CONVERT] Extracted {len(quantities)} quantities: {quantities}")
        logger.debug(f"[CONVERT] Extracted {len(prices)} prices: {prices}")

        # Build legacy format
        return {
            # Customer info
            'customer_name': customer_info.get('name', ''),
            'company_name': customer_info.get('company', ''),
            'email': customer_info.get('email', ''),
            'phone': customer_info.get('phone', ''),
            'address': customer_info.get('address', ''),

            # Products
            'product_names': product_names,
            'product_codes': product_codes,
            'quantities': quantities,
            'prices': prices,

            # Order info
            'order_number': order_info.get('order_number', ''),
            'order_date': order_info.get('date', ''),
            'delivery_date': order_info.get('delivery_date', ''),
            'urgency': order_info.get('urgency', 'medium'),
            'payment_terms': order_info.get('payment_terms', ''),
            'shipping_terms': order_info.get('shipping_terms', ''),
            'notes': order_info.get('notes', ''),

            # Store structured data for advanced processing
            'structured': {
                'customer': customer_info,
                'products': products,
                'order': order_info
            }
        }

    def _post_process_add_dimensions(self, entities: Dict, email_text: str) -> Dict:
        """
        Post-process extracted entities to add dimensions from email text.

        Handles multi-line PDF format where dimensions appear on line after product:
        RPR-123965 Cushion Mount Plus E1320 gelb ...
        457x23 mm

        Args:
            entities: Extracted entities dict
            email_text: Full email text including attachments

        Returns:
            Updated entities with dimensions added to product names
        """
        import re

        product_codes = entities.get('product_codes', [])
        product_names = entities.get('product_names', [])

        if not product_codes or not product_names:
            return entities

        logger.debug(f"Post-processing: Looking for dimensions for {len(product_codes)} products")

        # Pattern to find dimensions in various formats
        dimension_patterns = [
            # Format with technical specs (RPE, etc.) - HIGHEST PRIORITY
            r'(\d{2,4}\s*[xX*]\s*\d{1,3}(?:[.,]\d{1,2})?\s*(?:mm)?\s*(?:RPE|RPS|mm))',  # 25 * 0,20 RPE, 25x0,20 mm RPE

            # Format: NNNxNN mm or NNN x NN mm
            r'(\d{2,4}\s*[xX]\s*\d{1,3}(?:[.,]\d{1,2})?\s*mm)',  # 457x23 mm, 25x0.20 mm
            r'(\d{2,4}\s*[xX]\s*\d{1,3}(?:[.,]\d{1,2})?)',       # 457x23, 25x0.20

            # Format: NN * N,NN (asterisk with comma/dot)
            r'(\d{2,4}\s*\*\s*\d{1,3}(?:[.,]\d{1,2})?\s*mm)',    # 25 * 0,20 mm
            r'(\d{2,4}\s*\*\s*\d{1,3}(?:[.,]\d{1,2})?)',         # 25 * 0,20, 25*0.20

            # Format: NNNmm (single dimension)
            r'(\d{3,4}\s*mm)',                                    # 457mm, 685mm
        ]

        updated_count = 0

        for i, code in enumerate(product_codes):
            if i >= len(product_names):
                break

            # Search for this product code in email text
            # Look for code followed by product info, then capture next 200 chars
            code_pattern = rf'{re.escape(code)}[^\n]*(?:\n([^\n]{{0,200}}))?'
            code_match = re.search(code_pattern, email_text, re.IGNORECASE)

            if code_match:
                # Get the text after the product line (next line)
                next_line_text = code_match.group(1) if code_match.lastindex >= 1 else ""

                # Also check the same line
                same_line_text = code_match.group(0)
                search_text = same_line_text + " " + (next_line_text or "")

                # Try to find dimension in this text
                dimension_found = None
                for dim_pattern in dimension_patterns:
                    dim_match = re.search(dim_pattern, search_text, re.IGNORECASE)
                    if dim_match:
                        dimension_found = dim_match.group(1).strip()
                        break

                if dimension_found:
                    # Check if dimension is already in product name
                    current_name = product_names[i]
                    if dimension_found.lower() not in current_name.lower():
                        # Add dimension to product name
                        product_names[i] = f"{current_name} {dimension_found}"
                        logger.info(f"   [POST] Added dimension to '{code}': {dimension_found}")
                        updated_count += 1
                    else:
                        logger.debug(f"   [POST] Dimension already present for '{code}'")

        if updated_count > 0:
            logger.info(f"Post-processing complete: Updated {updated_count}/{len(product_codes)} products with dimensions")
        else:
            logger.debug(f"Post-processing complete: No dimensions added")

        entities['product_names'] = product_names
        return entities

    def _get_empty_entities(self) -> Dict:
        """
        Return empty entities structure as fallback

        Returns:
            Empty entities dictionary
        """
        return {
            'customer_name': '',
            'company_name': '',
            'email': '',
            'phone': '',
            'address': '',
            'product_names': [],
            'product_codes': [],
            'quantities': [],
            'prices': [],
            'order_number': '',
            'order_date': '',
            'delivery_date': '',
            'urgency': 'medium',
            'payment_terms': '',
            'shipping_terms': '',
            'notes': '',
            'structured': {
                'customer': {},
                'products': [],
                'order': {}
            }
        }

    def extract_complete(self, email_text: str, subject: str = "") -> Dict:
        """
        Complete extraction: intent + entities in ONE AI call

        Args:
            email_text: Full email body
            subject: Email subject line

        Returns:
            {
                'intent': {'type': '...', 'confidence': 0.95, ...},
                'entities': {...},  # Same as extract() method
                'raw_result': {...}  # Raw DSPy outputs
            }
        """
        try:
            logger.info("Complete extraction started (intent + entities in 1 call)")

            # Call 1: Extract everything (already includes intent info via urgency)
            result = self.extractor(email_text=email_text)

            # Parse outputs
            customer_info = self._parse_json(result.customer_json, {})
            products = self._parse_json(result.products_json, [])
            order_info = self._parse_json(result.order_info_json, {})

            # Convert to legacy format
            entities = self._convert_to_legacy_format(customer_info, products, order_info)
            entities = self._post_process_add_dimensions(entities, email_text)

            # Derive intent from extraction (order_inquiry is default)
            intent = {
                'type': 'order_inquiry',  # Most emails are orders
                'sub_type': 'new_order',
                'confidence': 0.95,
                'urgency': order_info.get('urgency', 'medium'),
                'reasoning': 'Extracted from order email'
            }

            # If we want explicit intent classification, use the classifier
            if subject:
                intent_result = self.intent_classifier(subject=subject, body=email_text[:1000])
                intent = {
                    'type': intent_result.intent_type,
                    'sub_type': intent_result.sub_type,
                    'confidence': float(intent_result.confidence),
                    'urgency': intent_result.urgency,
                    'reasoning': intent_result.reasoning
                }

            logger.info(f"Complete extraction: intent={intent['type']}, {len(entities.get('product_names', []))} products")

            return {
                'intent': intent,
                'entities': entities,
                'raw_result': {
                    'customer': customer_info,
                    'products': products,
                    'order': order_info
                }
            }

        except Exception as e:
            logger.error(f"Error in complete extraction: {e}", exc_info=True)
            return {
                'intent': {'type': 'unknown', 'confidence': 0.0, 'urgency': 'medium', 'reasoning': 'Error'},
                'entities': self._get_empty_entities(),
                'raw_result': {}
            }

    def confirm_products(self, email_excerpt: str, products: List[Dict], candidates_dict: Dict[str, List[Dict]]) -> Dict:
        """
        AI confirms best match for each product from top 10 candidates

        Args:
            email_excerpt: Relevant email text
            products: Extracted products [{"name": "...", "code": "..."}, ...]
            candidates_dict: {"product_name": [{"odoo_id": 123, "code": "...", "name": "..."}, ...], ...}

        Returns:
            {
                'matched_products': [
                    {'requested': '...', 'matched_odoo_id': 123, 'confidence': 0.95, 'reasoning': '...'},
                    ...
                ],
                'failed_products': [
                    {'requested': '...', 'reason': 'NO_MATCH'},
                    ...
                ]
            }
        """
        try:
            logger.info(f"Confirming {len(products)} products with AI...")

            # Build input for AI (without scores)
            products_with_candidates = []
            for product in products:
                product_name = product.get('name', '')
                product_code = product.get('code', '')

                if not product_name:
                    continue

                # Get candidates for this product
                candidates = candidates_dict.get(product_name, [])

                # Clean candidates (remove scores, only keep odoo_id, code, name)
                clean_candidates = []
                for c in candidates:
                    clean_candidates.append({
                        'odoo_id': c.get('id', 0),  # From JSON DB
                        'code': c.get('default_code', ''),
                        'name': c.get('name', '')
                    })

                products_with_candidates.append({
                    'requested': {
                        'name': product_name,
                        'code': product_code
                    },
                    'candidates': clean_candidates[:10]  # Top 10 only
                })

            # Call AI to confirm matches
            result = self.product_matcher(
                email_excerpt=email_excerpt[:2000],  # Limit to 2000 chars
                products_with_candidates=json.dumps(products_with_candidates, ensure_ascii=False)
            )

            # Parse AI response
            matches = self._parse_json(result.matches, [])

            # Separate matched and failed
            matched_products = []
            failed_products = []

            for match in matches:
                selected_id = match.get('selected_odoo_id', 0)

                if selected_id and selected_id != 0:
                    matched_products.append({
                        'requested': match.get('requested', ''),
                        'matched_odoo_id': selected_id,
                        'confidence': match.get('confidence', 0.0),
                        'reasoning': match.get('reason', '')
                    })
                else:
                    failed_products.append({
                        'requested': match.get('requested', ''),
                        'reason': match.get('reason', 'NO_MATCH')
                    })

            logger.info(f"AI confirmed: {len(matched_products)} matched, {len(failed_products)} failed")

            return {
                'matched_products': matched_products,
                'failed_products': failed_products
            }

        except Exception as e:
            logger.error(f"Error in product confirmation: {e}", exc_info=True)
            # Return all as failed if error
            return {
                'matched_products': [],
                'failed_products': [{'requested': p.get('name', ''), 'reason': f'Error: {e}'} for p in products]
            }

    def extract_batch(self, emails: List[str]) -> List[Dict]:
        """
        Extract entities from multiple emails in batch

        Args:
            emails: List of email texts

        Returns:
            List of entity dictionaries
        """
        results = []
        for i, email_text in enumerate(emails, 1):
            logger.info(f"Extracting entities from email {i}/{len(emails)}")
            result = self.extract(email_text)
            results.append(result)

        return results


class OptimizedEntityExtractor(EntityExtractor):
    """
    Optimized entity extractor using DSPy's optimization capabilities.

    This version can be optimized using labeled training data to
    automatically generate better prompts and few-shot examples.
    """

    def __init__(self):
        super().__init__(use_chain_of_thought=True)
        self.is_optimized = False

    def optimize(
        self,
        training_examples: List[dspy.Example],
        validation_examples: Optional[List[dspy.Example]] = None,
        metric_threshold: float = 0.8
    ):
        """
        Optimize the extractor using labeled examples.

        Args:
            training_examples: List of dspy.Example with labeled entities
            validation_examples: Optional validation set
            metric_threshold: Minimum accuracy threshold

        Example:
            >>> examples = [
            ...     dspy.Example(
            ...         email_text="Order from ACME Corp...",
            ...         customer_json='{"company": "ACME Corp", ...}',
            ...         products_json='[{"name": "Product A", ...}]',
            ...         order_info_json='{"order_number": "12345", ...}'
            ...     ).with_inputs("email_text")
            ... ]
            >>> extractor.optimize(examples)
        """
        try:
            logger.info(f"Optimizing entity extractor with {len(training_examples)} examples...")

            # Define accuracy metric
            def extraction_accuracy(example, pred, trace=None):
                """Check if extracted entities match expected entities"""
                # Compare customer info
                expected_customer = self._parse_json(example.customer_json, {})
                actual_customer = self._parse_json(pred.customer_json, {})
                customer_match = expected_customer.get('company') == actual_customer.get('company')

                # Compare products count
                expected_products = self._parse_json(example.products_json, [])
                actual_products = self._parse_json(pred.products_json, [])
                products_match = len(expected_products) == len(actual_products)

                return customer_match and products_match

            # Use BootstrapFewShot optimizer
            optimizer = dspy.BootstrapFewShot(
                metric=extraction_accuracy,
                max_bootstrapped_demos=4,
                max_labeled_demos=8
            )

            # Compile (optimize) the module
            self.extractor = optimizer.compile(
                self.extractor,
                trainset=training_examples
            )

            self.is_optimized = True
            logger.info("Entity extractor optimization complete")

            # Evaluate on validation set if provided
            if validation_examples:
                accuracy = self._evaluate(validation_examples, extraction_accuracy)
                logger.info(f"Validation accuracy: {accuracy:.2%}")

        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)
            raise

    def _evaluate(self, examples: List[dspy.Example], metric) -> float:
        """
        Evaluate extractor on examples

        Args:
            examples: List of labeled examples
            metric: Metric function to use

        Returns:
            Accuracy score (0.0 to 1.0)
        """
        correct = 0
        total = len(examples)

        for example in examples:
            pred = self.extractor(email_text=example.email_text)
            if metric(example, pred):
                correct += 1

        return correct / total if total > 0 else 0.0

    def save_optimized(self, path: str = "dspy_data/optimized_prompts/entity_extractor.json"):
        """Save optimized extractor configuration"""
        if not self.is_optimized:
            logger.warning("Extractor has not been optimized yet")
            return

        try:
            import os
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.extractor.save(path)
            logger.info(f"Optimized extractor saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save extractor: {e}")

    def load_optimized(self, path: str = "dspy_data/optimized_prompts/entity_extractor.json"):
        """Load previously optimized extractor"""
        try:
            self.extractor.load(path)
            self.is_optimized = True
            logger.info(f"Loaded optimized extractor from {path}")
        except Exception as e:
            logger.error(f"Failed to load extractor: {e}")
            raise
