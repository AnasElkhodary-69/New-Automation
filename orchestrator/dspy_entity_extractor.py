"""
DSPy Entity Extractor

Replaces manual prompt engineering for entity extraction with
DSPy's declarative approach using structured signatures.
"""

import logging
import json
from typing import Dict, List, Optional
import dspy
from orchestrator.dspy_signatures import ExtractOrderEntities

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
            logger.info("Entity extractor initialized with ChainOfThought")
        else:
            self.extractor = dspy.Predict(ExtractOrderEntities)
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

            # Call DSPy module
            result = self.extractor(email_text=email_text)

            # Parse JSON outputs
            customer_info = self._parse_json(result.customer_json, {})
            products = self._parse_json(result.products_json, [])
            order_info = self._parse_json(result.order_info_json, {})

            # Convert to legacy format for backward compatibility
            entities = self._convert_to_legacy_format(
                customer_info,
                products,
                order_info
            )

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
