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
from orchestrator.context_retriever import ContextRetriever
from orchestrator.odoo_matcher import OdooMatcher
from orchestrator.order_creator import OrderCreator

logger = logging.getLogger(__name__)


class EmailProcessor:
    """Main processor for coordinating email handling workflow"""

    # Feature toggles (set to True to enable)
    ENABLE_ORDER_CREATION = True  # Set to True to automatically create orders in Odoo
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

        # Initialize Hybrid Matcher (BERT + Token) for product matching
        hybrid_matcher = None
        token_matcher = None
        try:
            from retriever_module.hybrid_matcher import HybridMatcher
            logger.info("Initializing Hybrid Matcher (BERT + Token) for product matching...")
            # Check if we should use BERT (enabled by default, can be disabled via environment variable)
            use_bert = os.getenv('USE_BERT', 'true').lower() == 'true'

            hybrid_matcher = HybridMatcher(
                products_json_path="odoo_database/odoo_products.json",
                use_bert=use_bert,
                bert_model_name="Alibaba-NLP/gte-modernbert-base"
            )

            if use_bert:
                logger.info("[INFO] BERT semantic matching enabled (set USE_BERT=false to disable)")
            else:
                logger.info("[INFO] BERT semantic matching disabled (token matching only)")
            logger.info("[OK] Hybrid Matcher ready (BERT semantic + Token dimension matching)")
        except Exception as e:
            logger.warning(f"[!] Hybrid Matcher initialization failed: {e}")
            logger.warning("[!] Falling back to Token Matcher...")

            # Fallback to Token Matcher only
            try:
                from retriever_module.token_matcher import TokenMatcher
                logger.info("Initializing Token Matcher for product matching...")
                token_matcher = TokenMatcher()
                logger.info("[OK] Token Matcher ready (exact + token overlap matching)")
            except Exception as e2:
                logger.warning(f"[!] Token Matcher unavailable: {e2}")
                logger.warning("[!] Falling back to VectorStore fuzzy matching")

        # Initialize modular components
        self.context_retriever = ContextRetriever(
            vector_store,
            token_matcher=token_matcher,
            hybrid_matcher=hybrid_matcher
        )
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
            # STEP 1: Classify intent
            result['intent'] = self._classify_intent(email)
            logger.info(f"   Intent: {result['intent'].get('type')} ({result['intent'].get('confidence', 0):.0%} confidence)")

            # STEP 2: Extract entities
            result['entities'] = self._extract_entities(email)
            product_count = len(result['entities'].get('product_names', []))
            logger.info(f"   Extracted: {product_count} products, customer info, etc.")

            # Log step 2: Entity Extraction
            self.step_logger.log_step_2_entity_extraction(
                result['intent'],
                result['entities']
            )

            # STEP 3: Retrieve context (with logging)
            result['context'], match_stats = self._retrieve_context_with_logging(
                result['intent'],
                result['entities'],
                email
            )

            # STEP 4: Match in Odoo database
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

    def _classify_intent(self, email: Dict) -> Dict:
        """
        Classify email intent using AI (DSPy or standard)

        Args:
            email: Email dictionary

        Returns:
            Intent classification result
        """
        subject = email.get('subject', '')
        body = email.get('body', '')

        # Use DSPy if enabled, otherwise use standard agent
        if self.USE_DSPY and self.dspy_intent_classifier:
            logger.debug("Using DSPy intent classifier")
            return self.dspy_intent_classifier.classify(subject, body)
        else:
            logger.debug("Using standard Mistral agent")
            return self.ai_agent.classify_intent(subject, body)

    def _extract_entities(self, email: Dict) -> Dict:
        """
        Extract entities from email using AI (DSPy or standard)

        Args:
            email: Email dictionary

        Returns:
            Extracted entities
        """
        body = email.get('body', '')

        # Use DSPy if enabled, otherwise use standard agent
        if self.USE_DSPY and self.dspy_entity_extractor:
            logger.debug("Using DSPy entity extractor")
            return self.dspy_entity_extractor.extract(body)
        else:
            logger.debug("Using standard Mistral agent for extraction")
            return self.ai_agent.extract_entities(body)

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
