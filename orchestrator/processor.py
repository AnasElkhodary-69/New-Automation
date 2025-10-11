"""
Email Processor Module (Refactored)

Orchestrates the email processing workflow using modular components:
1. Parse email intent
2. Extract relevant information
3. Retrieve context from databases
4. Match in Odoo
5. Create orders (optional)
6. Generate responses
"""

import logging
import os
from typing import Dict, List, Optional, Any
from utils.step_logger import StepLogger
from utils.email_cleaner import clean_email_data
from orchestrator.context_retriever import ContextRetriever
from orchestrator.odoo_matcher import OdooMatcher
from orchestrator.order_creator import OrderCreator

logger = logging.getLogger(__name__)


class EmailProcessor:
    """Main processor for coordinating email handling workflow"""

    # Feature toggles (set to True to enable)
    ENABLE_ORDER_CREATION = False  # Set to True to automatically create orders in Odoo
    # Note: Email responses are NOT sent via SMTP - we don't use automated email replies

    def __init__(self, odoo_connector, vector_store, ai_agent):
        """
        Initialize Email Processor

        Args:
            odoo_connector: Instance of OdooConnector
            vector_store: Instance of VectorStore
            ai_agent: Instance of AI Agent (MistralAgent)
        """
        self.odoo = odoo_connector
        self.vector_store = vector_store
        self.ai_agent = ai_agent
        self.step_logger = StepLogger()

        # Check if DSPy is enabled (read from environment)
        self.USE_DSPY = os.getenv('USE_DSPY', 'false').lower() == 'true'

        # Token tracking for DSPy
        self.dspy_token_usage = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0
        }

        # Initialize Token Matcher for product matching
        token_matcher = None
        try:
            from retriever_module.token_matcher import TokenMatcher
            logger.info("Initializing Token Matcher for product matching...")
            token_matcher = TokenMatcher()
            logger.info("[OK] Token Matcher ready (exact + token overlap matching)")
        except Exception as e:
            logger.warning(f"[!] Token Matcher unavailable: {e}")
            logger.warning("[!] Falling back to VectorStore fuzzy matching")

        # Initialize modular components
        self.context_retriever = ContextRetriever(vector_store, token_matcher)
        self.odoo_matcher = OdooMatcher(odoo_connector)
        self.order_creator = OrderCreator(odoo_connector)

        # Initialize DSPy components if enabled
        self.dspy_intent_classifier = None
        self.dspy_entity_extractor = None
        if self.USE_DSPY:
            try:
                from orchestrator.dspy_config import setup_dspy
                from orchestrator.dspy_intent_classifier import IntentClassifier
                from orchestrator.dspy_entity_extractor import EntityExtractor

                logger.info("Initializing DSPy components...")
                setup_dspy()  # Configure DSPy with Mistral
                self.dspy_intent_classifier = IntentClassifier(use_chain_of_thought=True)
                self.dspy_entity_extractor = EntityExtractor(use_chain_of_thought=True)
                logger.info("[OK] DSPy intent classifier ready")
                logger.info("[OK] DSPy entity extractor ready")
            except Exception as e:
                logger.error(f"[!] DSPy initialization failed: {e}")
                logger.warning("[!] Falling back to standard Mistral agent")
                self.USE_DSPY = False

        logger.info(f"Email Processor initialized (modular architecture, DSPy: {self.USE_DSPY})")

    def process_email(self, email: Dict) -> Dict:
        """
        Main processing method for incoming email

        Args:
            email: Email dictionary with subject, body, etc.

        Returns:
            Processing result with intent, entities, context, and response
        """
        logger.info("Processing email...")

        # Initialize step logging for this email
        email_id = email.get('message_id', email.get('id', 'unknown'))
        self.step_logger.start_email_log(email_id)

        # Clean email content (remove noise, detect T&C files)
        email = clean_email_data(email)

        # Log step 1: Email parsing
        self.step_logger.log_step_1_email_parsing(email)

        result = {
            'success': False,
            'intent': {},
            'entities': {},
            'context': {},
            'odoo_matches': {},
            'order_created': {},
            'response': '',
            'token_usage': {}
        }

        try:
            # STEP 1: Complete extraction (intent + entities in ONE AI call)
            extraction = self._extract_complete(email)
            result['intent'] = extraction['intent']
            result['entities'] = extraction['entities']

            product_count = len(result['entities'].get('product_names', []))
            logger.info(f"   Intent: {result['intent'].get('type')} ({result['intent'].get('confidence', 0):.0%} confidence)")
            logger.info(f"   Extracted: {product_count} products, customer info, etc.")

            # Log step 2: Complete Extraction
            self.step_logger.log_step_2_entity_extraction(
                result['intent'],
                result['entities']
            )

            # STEP 2: Get top 10 candidates per product (no AI)
            products = extraction['raw_result'].get('products', [])
            candidates_dict = self.context_retriever.retrieve_product_candidates(products, top_n=10)

            # Also get customer
            customer_search = result['entities'].get('company_name') or result['entities'].get('customer_name')
            customer_info = None
            if customer_search:
                customer_info = self.vector_store.search_customer(customer_search, threshold=0.6)

            # Log candidates
            self.step_logger.log_step_3_rag_input(result['intent'], result['entities'], {
                'customer_search': customer_search,
                'product_count': len(products),
                'candidates_per_product': {k: len(v) for k, v in candidates_dict.items()}
            })

            # STEP 3: Smart product confirmation (AI only for low confidence < 80%)
            confirmed = self._smart_confirm_products(email.get('body', ''), products, candidates_dict)

            # Build context from confirmed products
            result['context'] = {
                'customer_info': customer_info,
                'json_data': {
                    'products': self._build_products_from_confirmed(confirmed['matched_products'], candidates_dict)
                },
                'confirmed_matches': confirmed
            }

            # Log confirmed matches
            self.step_logger.log_step_4_rag_output(result['context'], {
                'customer_found': customer_info is not None,
                'products_matched': len(confirmed['matched_products']),
                'products_failed': len(confirmed['failed_products'])
            })

            # STEP 4: Match in Odoo database (verification)
            result['odoo_matches'] = self.odoo_matcher.match_in_odoo(
                result['context'],
                result['entities']
            )

            # Log step 5: Odoo matching
            self.step_logger.log_step_5_odoo_matching(result['odoo_matches'])

            # STEP 5: Create order if it's an order inquiry (OPTIONAL)
            if result['intent'].get('type') == 'order_inquiry':
                if self.ENABLE_ORDER_CREATION:
                    result['order_created'] = self.order_creator.create_order_in_odoo(
                        result['odoo_matches'],
                        result['entities'],
                        email
                    )
                else:
                    logger.info("   [INFO] Order creation disabled (set ENABLE_ORDER_CREATION=True to enable)")
                    result['order_created'] = {
                        'created': False,
                        'message': 'Order creation disabled (ENABLE_ORDER_CREATION=False)'
                    }

            # STEP 6: Generate response (placeholder - can be implemented)
            result['response'] = self._generate_response(
                email,
                result['intent'],
                result['entities'],
                result['context']
            )

            # Track token usage
            # Always use MistralAgent stats as it tracks all Mistral API calls
            # (DSPy uses same Mistral backend, tokens are counted there)
            result['token_usage'] = self.ai_agent.get_token_stats()

            if self.USE_DSPY:
                logger.debug("Token usage tracked via MistralAgent (DSPy mode)")

            result['success'] = True
            logger.info("   [OK] Email processing complete")

        except Exception as e:
            logger.error(f"   [ERROR] Email processing failed: {e}", exc_info=True)
            result['error'] = str(e)

        return result

    def _extract_complete(self, email: Dict) -> Dict:
        """
        Complete extraction: intent + entities in ONE AI call

        Args:
            email: Email dictionary

        Returns:
            {
                'intent': {...},
                'entities': {...},
                'raw_result': {'customer': {}, 'products': [], 'order': {}}
            }
        """
        subject = email.get('subject', '')
        body = email.get('body', '')

        # Use DSPy if enabled
        if self.USE_DSPY and self.dspy_entity_extractor:
            logger.debug("Using DSPy complete extraction")
            return self.dspy_entity_extractor.extract_complete(body, subject)
        else:
            # Fallback: separate calls
            logger.debug("Using standard Mistral agent (separate calls)")
            intent = self.ai_agent.classify_intent(subject, body)
            entities = self.ai_agent.extract_entities(body)
            return {
                'intent': intent,
                'entities': entities,
                'raw_result': {'customer': {}, 'products': [], 'order': {}}
            }

    def _smart_confirm_products(self, email_body: str, products: List[Dict], candidates_dict: Dict) -> Dict:
        """
        Smart product confirmation: AI only for low-confidence matches (< 80%)

        Args:
            email_body: Email text
            products: Extracted products
            candidates_dict: Top candidates per product

        Returns:
            {
                'matched_products': [...],
                'failed_products': [...],
                'stats': {'auto_matched': N, 'ai_confirmed': N, 'failed': N}
            }
        """
        matched_products = []
        failed_products = []

        # Separate high-confidence and low-confidence products
        high_confidence_products = []
        low_confidence_products = []
        low_confidence_dict = {}

        for product in products:
            product_name = product.get('name', '')
            candidates = candidates_dict.get(product_name, [])

            if not candidates:
                # No candidates at all
                failed_products.append({
                    'requested': product_name,
                    'reason': 'NO_MATCH - no candidates found in database'
                })
                continue

            # Check top candidate confidence (similarity_score)
            top_candidate = candidates[0]
            confidence = top_candidate.get('similarity_score', 0.0)

            if confidence >= 0.80:  # High confidence (>=80%)
                # Auto-match without AI
                high_confidence_products.append(product_name)
                matched_products.append({
                    'requested': product_name,
                    'matched_odoo_id': top_candidate.get('id', 0),
                    'confidence': confidence,
                    'reasoning': f'Auto-matched (high confidence: {confidence:.0%})'
                })
                logger.info(f"   [AUTO] {product_name} -> {top_candidate.get('default_code')} ({confidence:.0%})")
            else:
                # Low confidence - needs AI review
                low_confidence_products.append(product)
                low_confidence_dict[product_name] = candidates

        # Log statistics
        logger.info(f"   Product matching: {len(high_confidence_products)} auto-matched (>=80%), {len(low_confidence_products)} need AI review")

        # STEP 3b: AI confirmation ONLY for low-confidence products
        if low_confidence_products:
            logger.info(f"   Requesting AI confirmation for {len(low_confidence_products)} uncertain products...")

            if self.USE_DSPY and self.dspy_entity_extractor:
                ai_result = self.dspy_entity_extractor.confirm_products(
                    email_body,
                    low_confidence_products,
                    low_confidence_dict
                )
                matched_products.extend(ai_result['matched_products'])
                failed_products.extend(ai_result['failed_products'])

                logger.info(f"   AI confirmed: {len(ai_result['matched_products'])} matched, {len(ai_result['failed_products'])} failed")
            else:
                # Fallback: use first candidate
                for product in low_confidence_products:
                    product_name = product.get('name', '')
                    candidates = low_confidence_dict.get(product_name, [])
                    if candidates:
                        matched_products.append({
                            'requested': product_name,
                            'matched_odoo_id': candidates[0].get('id', 0),
                            'confidence': 0.6,
                            'reasoning': 'Fallback - first candidate (no DSPy)'
                        })

        return {
            'matched_products': matched_products,
            'failed_products': failed_products,
            'stats': {
                'auto_matched': len(high_confidence_products),
                'ai_confirmed': len(low_confidence_products),
                'failed': len(failed_products)
            }
        }

    def _confirm_products(self, email_body: str, products: List[Dict], candidates_dict: Dict) -> Dict:
        """
        AI confirms best product match from candidates (legacy - kept for compatibility)

        Args:
            email_body: Email text
            products: Extracted products
            candidates_dict: Top candidates per product

        Returns:
            {
                'matched_products': [...],
                'failed_products': [...]
            }
        """
        if self.USE_DSPY and self.dspy_entity_extractor:
            logger.debug("Using DSPy product confirmation")
            return self.dspy_entity_extractor.confirm_products(email_body, products, candidates_dict)
        else:
            # Fallback: no AI confirmation, just return first candidate
            logger.warning("No DSPy - returning first candidate for each product (no AI confirmation)")
            matched = []
            failed = []
            for product in products:
                product_name = product.get('name', '')
                candidates = candidates_dict.get(product_name, [])
                if candidates:
                    matched.append({
                        'requested': product_name,
                        'matched_odoo_id': candidates[0].get('id', 0),
                        'confidence': 0.8,
                        'reasoning': 'First candidate (no AI confirmation)'
                    })
                else:
                    failed.append({'requested': product_name, 'reason': 'NO_MATCH - no candidates found'})
            return {'matched_products': matched, 'failed_products': failed}

    def _build_products_from_confirmed(self, matched_products: List[Dict], candidates_dict: Dict) -> List[Dict]:
        """
        Build product list from confirmed matches

        Args:
            matched_products: AI-confirmed matches with odoo_ids
            candidates_dict: Original candidates

        Returns:
            List of full product dicts
        """
        products = []
        for match in matched_products:
            odoo_id = match.get('matched_odoo_id')
            requested = match.get('requested')

            # Find the full product info from candidates
            candidates = candidates_dict.get(requested, [])
            for candidate in candidates:
                if candidate.get('id') == odoo_id:
                    products.append(candidate)
                    break

        return products

    def _retrieve_context_with_logging(self, intent: Dict, entities: Dict, email: Dict) -> tuple:
        """
        Retrieve context and log RAG input/output steps

        Args:
            intent: Intent classification
            entities: Extracted entities
            email: Original email

        Returns:
            Tuple of (context, match_stats)
        """
        # Prepare search criteria for logging
        search_criteria = {
            'intent_type': intent.get('type'),
            'customer_search': entities.get('company_name') or entities.get('customer_name'),
            'product_count': len(entities.get('product_names', [])),
            'product_codes_count': len(entities.get('product_codes', []))
        }

        # LOG STEP 3: RAG Input
        self.step_logger.log_step_3_rag_input(intent, entities, search_criteria)

        # Retrieve context
        context = self.context_retriever.retrieve_context(intent, entities, email)

        # Prepare match stats for logging
        match_stats = {
            'customer_found': context.get('customer_info') is not None,
            'products_matched': len(context.get('json_data', {}).get('products', []))
        }

        # LOG STEP 4: RAG Output
        self.step_logger.log_step_4_rag_output(context, match_stats)

        return context, match_stats

    def _generate_response(
        self,
        email: Dict,
        intent: Dict,
        entities: Dict,
        context: Dict
    ) -> str:
        """
        Generate response (placeholder - can be implemented)

        Args:
            email: Original email
            intent: Intent classification
            entities: Extracted entities
            context: Retrieved context

        Returns:
            Generated response text
        """
        # This is a placeholder - response generation can be implemented later
        return f"Acknowledged: {intent.get('type')} email processed"

    def validate_response(self, response: str) -> Dict:
        """
        Validate generated response

        Args:
            response: Response text to validate

        Returns:
            Validation result
        """
        return {
            'valid': len(response) > 0,
            'length': len(response)
        }

    def _get_dspy_token_usage(self) -> Dict:
        """
        Get token usage from DSPy LiteLLM history

        Returns:
            Token usage statistics
        """
        try:
            import dspy

            input_tokens = 0
            output_tokens = 0

            # Try multiple ways to get token usage from DSPy
            # Method 1: Check lm.history
            if hasattr(dspy.settings, 'lm') and hasattr(dspy.settings.lm, 'history'):
                history = dspy.settings.lm.history
                for call in history:
                    if isinstance(call, dict):
                        # Try different response structures
                        if 'response' in call:
                            resp = call['response']
                            if hasattr(resp, 'usage'):
                                input_tokens += getattr(resp.usage, 'prompt_tokens', 0)
                                output_tokens += getattr(resp.usage, 'completion_tokens', 0)
                            elif isinstance(resp, dict) and 'usage' in resp:
                                input_tokens += resp['usage'].get('prompt_tokens', 0)
                                output_tokens += resp['usage'].get('completion_tokens', 0)

            # Method 2: Check if model has usage attribute
            if input_tokens == 0 and hasattr(dspy.settings, 'lm'):
                lm = dspy.settings.lm
                if hasattr(lm, 'get_usage'):
                    usage = lm.get_usage()
                    if usage:
                        input_tokens = usage.get('prompt_tokens', 0)
                        output_tokens = usage.get('completion_tokens', 0)

            total_tokens = input_tokens + output_tokens

            # Store for later retrieval
            self.dspy_token_usage = {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens
            }

            if total_tokens > 0:
                logger.info(f"DSPy token usage: {input_tokens} in + {output_tokens} out = {total_tokens} total")
            else:
                logger.warning("Could not retrieve DSPy token usage - using fallback from standard agent")
                # Fallback to standard agent token tracking
                return self.ai_agent.get_token_stats()

            return self.dspy_token_usage

        except Exception as e:
            logger.warning(f"Error retrieving DSPy token usage: {e}, using standard agent fallback")
            return self.ai_agent.get_token_stats()

    def log_interaction(self, email: Dict, result: Dict):
        """
        Log the interaction (placeholder for future implementation)

        Args:
            email: Original email
            result: Processing result
        """
        # This can be implemented to log interactions to a database
        pass
