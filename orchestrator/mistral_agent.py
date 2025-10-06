"""
Mistral Agent Module

Handles interaction with Mistral AI API for:
- Intent classification
- Entity extraction
- Response generation
- Context understanding
"""

import logging
from typing import Dict, List, Optional, Any
import json
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class MistralAgent:
    """Mistral AI agent for RAG-based email processing"""

    def __init__(self, config_path: str = "config/settings.json"):
        """
        Initialize Mistral Agent

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.api_key = self.config.get('mistral_api_key', '')

        # Hybrid model strategy
        self.use_hybrid = self.config.get('use_hybrid_models', True)
        self.small_model = self.config.get('mistral_small_model', 'mistral-small-latest')
        self.medium_model = self.config.get('mistral_medium_model', 'mistral-medium-latest')
        self.large_model = self.config.get('mistral_large_model', 'mistral-large-latest')

        # Default model (for backward compatibility)
        self.model = self.config.get('mistral_model', 'mistral-large-latest')

        self.prompts = self._load_prompts()
        self.client = None

        # Token usage tracking (per model)
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        # Model usage stats
        self.model_usage_stats = {
            'small': {'calls': 0, 'input_tokens': 0, 'output_tokens': 0},
            'medium': {'calls': 0, 'input_tokens': 0, 'output_tokens': 0},
            'large': {'calls': 0, 'input_tokens': 0, 'output_tokens': 0}
        }

        self._initialize_client()

    def _load_config(self) -> Dict:
        """
        Load configuration

        Returns:
            Configuration dictionary
        """
        logger.info(f"Loading Mistral configuration")

        try:
            from dotenv import load_dotenv
            load_dotenv()

            return {
                "mistral_api_key": os.getenv('MISTRAL_API_KEY', ''),
                "mistral_model": os.getenv('MISTRAL_MODEL', 'mistral-large-latest'),
                "use_hybrid_models": os.getenv('MISTRAL_USE_HYBRID', 'true').lower() == 'true',
                "mistral_small_model": os.getenv('MISTRAL_SMALL_MODEL', 'mistral-small-latest'),
                "mistral_medium_model": os.getenv('MISTRAL_MEDIUM_MODEL', 'mistral-medium-latest'),
                "mistral_large_model": os.getenv('MISTRAL_LARGE_MODEL', 'mistral-large-latest'),
                "max_tokens": 2000,
                "temperature": 0.7
            }
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {
                "mistral_api_key": "",
                "mistral_model": "mistral-large-latest",
                "max_tokens": 2000,
                "temperature": 0.7
            }

    def _load_prompts(self) -> Dict:
        """
        Load prompt templates from prompts directory

        Returns:
            Dictionary of prompt templates
        """
        logger.info("Loading prompt templates...")

        prompts = {}

        try:
            # Load intent classification prompt
            intent_prompt_path = Path("prompts/intent_prompt.txt")
            if intent_prompt_path.exists():
                with open(intent_prompt_path, 'r', encoding='utf-8') as f:
                    prompts['intent'] = f.read()

            # Load extraction prompt
            extraction_prompt_path = Path("prompts/extraction_prompt.txt")
            if extraction_prompt_path.exists():
                with open(extraction_prompt_path, 'r', encoding='utf-8') as f:
                    prompts['extraction'] = f.read()

        except Exception as e:
            logger.error(f"Error loading prompts: {e}")

        return prompts

    def _initialize_client(self):
        """Initialize Mistral API client"""
        # Check if API key is configured
        if not self.api_key or self.api_key == 'your_mistral_api_key_here':
            logger.warning("Mistral API key not configured. Running in DEMO mode.")
            logger.warning("Add your API key to .env file: MISTRAL_API_KEY=...")
            self.client = None
            return

        try:
            from mistralai import Mistral
            self.client = Mistral(api_key=self.api_key)
            logger.info("Mistral client initialized")
        except ImportError:
            logger.error("mistralai package not installed. Run: pip install mistralai")
            self.client = None
        except Exception as e:
            logger.error(f"Error initializing Mistral client: {e}")
            self.client = None

    def _log_token_usage(self, response, operation_name: str, model_used: str = None):
        """
        Log token usage from Mistral API response

        Args:
            response: Mistral API response object
            operation_name: Name of the operation (e.g., 'Intent Classification')
            model_used: Model name used (for tracking)
        """
        try:
            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # Update running totals
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_tokens += total_tokens

            # Track per-model usage
            if model_used:
                model_type = 'small' if 'small' in model_used.lower() else ('medium' if 'medium' in model_used.lower() else 'large')
                self.model_usage_stats[model_type]['calls'] += 1
                self.model_usage_stats[model_type]['input_tokens'] += input_tokens
                self.model_usage_stats[model_type]['output_tokens'] += output_tokens

            model_info = f" [{model_used}]" if model_used else ""
            logger.info(f"   [TOKENS] [{operation_name}]{model_info} Tokens: {input_tokens} input + {output_tokens} output = {total_tokens} total")
        except Exception as e:
            logger.warning(f"Could not log token usage: {e}")

    def get_token_stats(self) -> Dict:
        """
        Get token usage statistics

        Returns:
            Dictionary with token usage stats
        """
        return {
            'total_tokens': self.total_tokens,
            'input_tokens': self.total_input_tokens,
            'output_tokens': self.total_output_tokens
        }

    def reset_token_stats(self):
        """Reset token usage statistics"""
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def classify_intent(self, subject: str, body: str) -> Dict:
        """
        Classify email intent using Mistral

        Args:
            subject: Email subject
            body: Email body

        Returns:
            Intent classification result
        """
        logger.info("Classifying intent with Mistral...")

        # Demo mode fallback
        if not self.client:
            return self._demo_classify_intent(subject, body)

        try:
            # Prepare prompt
            prompt = self.prompts.get('intent', '')
            if not prompt:
                prompt = f"""Classify the intent of this email.

Subject: {subject}
Body: {body}

Return a JSON object with:
- type: one of [order_inquiry, invoice_request, product_inquiry, general_inquiry]
- confidence: float between 0 and 1
- sub_type: optional sub-category
- reasoning: brief explanation

JSON:"""

            prompt = prompt.format(subject=subject, body=body)

            # Use Small model for intent classification (simple task)
            model_to_use = self.small_model if self.use_hybrid else self.model

            # Call Mistral API
            response = self.client.chat.complete(
                model=model_to_use,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            # Log token usage
            self._log_token_usage(response, "Intent Classification", model_to_use)

            # Parse response
            result_text = response.choices[0].message.content
            logger.debug(f"Mistral intent response: {result_text}")
            result = self._parse_intent_response(result_text)
            return result

        except Exception as e:
            logger.error(f"Error classifying intent: {str(e)}")
            return self._demo_classify_intent(subject, body)

    def _demo_classify_intent(self, subject: str, body: str) -> Dict:
        """Demo mode intent classification"""
        logger.info("Using DEMO intent classification (no Mistral API)")

        # Simple keyword-based classification
        text = (subject + " " + body).lower()

        if any(word in text for word in ['order', 'purchase', 'tracking', 'delivery']):
            return {
                'type': 'order_inquiry',
                'confidence': 0.75,
                'sub_type': 'delivery_status',
                'reasoning': 'Demo mode: Keywords suggest order inquiry'
            }
        elif any(word in text for word in ['invoice', 'payment', 'bill', 'receipt']):
            return {
                'type': 'invoice_request',
                'confidence': 0.75,
                'sub_type': None,
                'reasoning': 'Demo mode: Keywords suggest invoice request'
            }
        elif any(word in text for word in ['product', 'price', 'available', 'stock']):
            return {
                'type': 'product_inquiry',
                'confidence': 0.75,
                'sub_type': None,
                'reasoning': 'Demo mode: Keywords suggest product inquiry'
            }
        else:
            return {
                'type': 'general_inquiry',
                'confidence': 0.60,
                'sub_type': None,
                'reasoning': 'Demo mode: Default classification'
            }

    def extract_entities(self, text: str, retry_count: int = 0) -> Dict:
        """
        Extract entities from email text with validation and retry logic

        Args:
            text: Email text
            retry_count: Current retry attempt (internal use)

        Returns:
            Extracted entities dictionary
        """
        logger.info("Extracting entities with Mistral...")

        # Demo mode fallback
        if not self.client:
            return self._demo_extract_entities(text)

        try:
            # Prepare prompt
            prompt = self.prompts.get('extraction', '')
            if not prompt:
                prompt = f"""Extract key entities from this email text:

{text}

Return a JSON object with:
- order_numbers: list of order/reference numbers
- product_names: list of product names mentioned
- dates: list of dates mentioned
- amounts: list of monetary amounts
- references: list of other reference IDs
- customer_name: customer's name if mentioned
- urgency_level: low/medium/high
- sentiment: positive/neutral/negative

JSON:"""

            prompt = prompt.format(text=text)

            # Hybrid model strategy: Small first, Medium on retry
            if self.use_hybrid:
                if retry_count == 0:
                    # First try: Use Small model (cheap)
                    model_to_use = self.small_model
                    logger.info(f"   Using Small model for entity extraction (attempt {retry_count + 1})")
                else:
                    # Retry: Use Medium model (better quality)
                    model_to_use = self.medium_model
                    logger.info(f"   Using Medium model for entity extraction (attempt {retry_count + 1})")
            else:
                # Non-hybrid mode: use configured model
                model_to_use = self.model

            # Call Mistral API
            response = self.client.chat.complete(
                model=model_to_use,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2500  # Increased from 1500 to handle large orders
            )

            # Log token usage
            self._log_token_usage(response, f"Entity Extraction (attempt {retry_count + 1})", model_to_use)

            # Parse response
            result_text = response.choices[0].message.content

            # DEBUG: Save raw response to file for inspection
            try:
                with open('mistral_raw_response_debug.txt', 'w', encoding='utf-8') as f:
                    f.write(result_text)
                logger.info("Saved raw Mistral response to mistral_raw_response_debug.txt")
            except Exception as e:
                logger.warning(f"Could not save debug file: {e}")

            # Log raw response for debugging
            logger.info("="*80)
            logger.info("RAW MISTRAL ENTITY EXTRACTION RESPONSE:")
            if result_text:
                logger.info(f"Length: {len(result_text)} chars")
                logger.info(f"First 1000 chars:\n{result_text[:1000]}")
            else:
                logger.warning("RESPONSE IS EMPTY OR NONE!")
                logger.debug(f"Response object type: {type(result_text)}")
                logger.debug(f"Full response: {response}")
            logger.info("="*80)

            entities = self._parse_entity_response(result_text)

            # Log extracted counts
            logger.info(f"Extraction Summary:")
            logger.info(f"   Product Names: {len(entities.get('product_names', []))}")
            logger.info(f"   References/Codes: {len(entities.get('references', []))}")
            logger.info(f"   Amounts: {len(entities.get('amounts', []))}")
            logger.info(f"   Dates: {len(entities.get('dates', []))}")
            logger.info(f"   Customer Emails: {len(entities.get('customer_emails', []))}")
            logger.info(f"   Phone Numbers: {len(entities.get('phone_numbers', []))}")
            logger.info(f"   Addresses: {len(entities.get('addresses', []))}")

            # Log actual extracted customer contact info for debugging
            if entities.get('customer_emails'):
                logger.info(f"   -> Emails extracted: {entities.get('customer_emails')[:2]}")
            if entities.get('phone_numbers'):
                logger.info(f"   -> Phones extracted: {entities.get('phone_numbers')[:2]}")
            if entities.get('addresses'):
                logger.info(f"   -> Addresses extracted: {entities.get('addresses')}")
            else:
                logger.warning(f"   -> NO ADDRESSES EXTRACTED (empty array)")

            # Validate entities - check if extraction seems incomplete
            if self._validate_entity_extraction(entities, text, retry_count):
                return entities
            else:
                # Retry once with higher temperature for better extraction
                if retry_count < 1:
                    logger.warning("Entity extraction seems incomplete, retrying with adjusted parameters...")
                    return self.extract_entities(text, retry_count + 1)
                else:
                    logger.warning("Entity extraction still incomplete after retry, using current results")
                    return entities

        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return self._demo_extract_entities(text)

    def _demo_extract_entities(self, text: str) -> Dict:
        """Demo mode entity extraction"""
        logger.info("Using DEMO entity extraction (no Mistral API)")

        import re

        entities = {
            'order_numbers': [],
            'product_names': [],
            'dates': [],
            'amounts': [],
            'references': [],
            'locations': [],
            'contact_info': [],
            'time_expressions': [],
            'customer_name': None,
            'urgency_level': 'medium',
            'sentiment': 'neutral'
        }

        # Extract order numbers (SO, ORD, etc.)
        order_patterns = [r'SO\d+', r'ORD[-]?\d+', r'#\d{4,}']
        for pattern in order_patterns:
            entities['order_numbers'].extend(re.findall(pattern, text, re.IGNORECASE))

        # Extract amounts ($, €, etc.)
        amount_pattern = r'[\$€£]\s?\d+[\.,]?\d*'
        entities['amounts'] = re.findall(amount_pattern, text)

        # Simple sentiment based on keywords
        if any(word in text.lower() for word in ['urgent', 'asap', 'immediately', 'emergency']):
            entities['urgency_level'] = 'high'
        if any(word in text.lower() for word in ['angry', 'disappointed', 'terrible', 'awful']):
            entities['sentiment'] = 'negative'
        elif any(word in text.lower() for word in ['thanks', 'appreciate', 'great', 'excellent']):
            entities['sentiment'] = 'positive'

        return entities

    def generate_response(
        self,
        email: Dict,
        intent: Dict,
        entities: Dict,
        context: Dict
    ) -> str:
        """
        Generate email response using RAG approach

        Args:
            email: Original email
            intent: Classified intent
            entities: Extracted entities
            context: Retrieved context from Odoo and vector store

        Returns:
            Generated response text
        """
        logger.info("Generating response with Mistral and RAG context...")

        # Demo mode fallback
        if not self.client:
            return self._demo_generate_response(email, intent, entities, context)

        try:
            # Build context-enhanced prompt
            prompt = self._build_rag_prompt(email, intent, entities, context)

            # Call Mistral API
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config['temperature'],
                max_tokens=self.config['max_tokens']
            )

            # Log token usage
            self._log_token_usage(response, "Response Generation")

            # Log raw response for debugging
            response_text = response.choices[0].message.content
            logger.info("="*80)
            logger.info("RAW MISTRAL RESPONSE GENERATION:")
            logger.info(f"Response type: {type(response_text)}, Length: {len(response_text) if response_text else 0}")
            if response_text and len(response_text.strip()) > 0:
                logger.info(f"Response generated successfully!")
                # Don't log full response here to avoid encoding issues - will be logged in main.py
            else:
                logger.warning("RESPONSE IS EMPTY OR WHITESPACE ONLY!")
                logger.warning(f"Raw value: '{response_text}'")
                logger.warning(f"Prompt length: {len(prompt)} chars")
            logger.info("="*80)

            # If response is empty, use demo mode as fallback
            if not response_text or len(response_text.strip()) == 0:
                logger.warning("Mistral returned empty response, falling back to demo mode")
                return self._demo_generate_response(email, intent, entities, context)

            return response_text

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return self._demo_generate_response(email, intent, entities, context)

    def _demo_generate_response(self, email: Dict, intent: Dict, entities: Dict, context: Dict) -> str:
        """Demo mode response generation"""
        logger.info("Using DEMO response generation (no Mistral API)")

        # Safely get customer info
        customer_info = context.get('customer_info') if context else None
        customer_name = customer_info.get('name', 'Valued Customer') if customer_info else 'Valued Customer'
        intent_type = intent.get('type', 'general_inquiry') if intent else 'general_inquiry'

        response = f"Dear {customer_name},\n\n"

        if intent_type == 'order_inquiry':
            response += "Thank you for your inquiry about your order. "
            response += "I've checked your account and found the following recent orders:\n\n"

            orders = context.get('odoo_data', {}).get('orders', [])
            if orders:
                for order in orders[:3]:
                    response += f"- Order {order.get('name')}: {order.get('state')}\n"
            else:
                response += "No recent orders found in our system.\n"

        elif intent_type == 'invoice_request':
            response += "Thank you for contacting us regarding invoices. "
            response += "I've located the following invoices for your account:\n\n"

            invoices = context.get('odoo_data', {}).get('invoices', [])
            if invoices:
                for inv in invoices[:3]:
                    response += f"- Invoice {inv.get('name')}: €{inv.get('amount_total')} - {inv.get('state')}\n"
            else:
                response += "No invoices found in our system.\n"

        elif intent_type == 'product_inquiry':
            response += "Thank you for your interest in our products. "
            response += "Let me provide you with the information you requested.\n\n"

        else:
            response += "Thank you for reaching out to us. "
            response += "I've reviewed your inquiry and I'm here to help.\n\n"

        response += "\nIf you need any additional assistance, please don't hesitate to contact us.\n\n"
        response += "Best regards,\nCustomer Service Team"
        response += "\n\n[DEMO MODE - Add MISTRAL_API_KEY to .env for AI-generated responses]"

        return response

    def _build_rag_prompt(self, email: Dict, intent: Dict, entities: Dict, context: Dict) -> str:
        """Build RAG prompt with retrieved context"""

        prompt = f"""You are a customer service agent responding to an email.

Email Details:
- From: {email.get('from')}
- Subject: {email.get('subject')}
- Body: {email.get('body')}

Intent: {intent.get('type')}

Extracted Information:
{json.dumps(entities, indent=2)}

Customer Context:
{json.dumps(context.get('customer_info', {}), indent=2)}

Relevant Odoo Data:
{json.dumps(context.get('odoo_data', {}), indent=2)}

Please generate a professional, helpful email response that:
1. Addresses the customer's inquiry
2. Uses the provided context appropriately
3. Maintains a friendly and professional tone
4. Provides accurate information based on the data
5. Offers next steps if applicable

Response:
"""
        return prompt

    def _parse_intent_response(self, response_text: str) -> Dict:
        """Parse Mistral's intent classification response"""
        try:
            import re

            # Remove markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith('```'):
                # Remove ```json or ``` at start and ``` at end
                cleaned = re.sub(r'^```(?:json)?\s*\n', '', cleaned)
                cleaned = re.sub(r'\n```\s*$', '', cleaned)

            # FIX: Add missing commas in malformed JSON (common Mistral error)
            # Pattern: "value"\n    "key" should be "value",\n    "key"
            cleaned = re.sub(r'(:\s*"[^"]*")\s*\n\s*(")', r'\1,\n    \2', cleaned)
            cleaned = re.sub(r'(:\s*[\d.]+)\s*\n\s*(")', r'\1,\n    \2', cleaned)
            cleaned = re.sub(r'(:\s*null)\s*\n\s*(")', r'\1,\n    \2', cleaned)

            # Extract just the core fields we need with regex patterns
            # This is more robust than trying to parse potentially malformed JSON
            type_match = re.search(r'"type"\s*:\s*"([^"]+)"', cleaned)
            confidence_match = re.search(r'"confidence"\s*:\s*([\d.]+)', cleaned)
            sub_type_match = re.search(r'"sub_type"\s*:\s*"([^"]+)"', cleaned)
            reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+(?:"[^"]*"[^"]*)*)"', cleaned)

            if type_match:
                result = {
                    'type': type_match.group(1),
                    'confidence': float(confidence_match.group(1)) if confidence_match else 0.8,
                    'sub_type': sub_type_match.group(1) if sub_type_match else None,
                    'reasoning': reasoning_match.group(1)[:200] if reasoning_match else 'Parsed from Mistral response'
                }
                logger.debug(f"Parsed intent: {result}")
                return result

            # Fallback: try to parse as JSON after fixing
            try:
                result = json.loads(cleaned)
                logger.debug(f"Parsed intent via JSON: {result}")
                return result
            except json.JSONDecodeError:
                # Try to extract JSON object even if nested in other text
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned)
                if json_match:
                    result = json.loads(json_match.group())
                    logger.debug(f"Parsed intent via JSON extraction: {result}")
                    return result

        except Exception as e:
            logger.error(f"Error parsing intent response: {e}")
            logger.debug(f"Full response text: {response_text[:500]}")

        return {
            'type': 'general_inquiry',
            'confidence': 0.5,
            'sub_type': None,
            'reasoning': 'Could not parse Mistral response'
        }

    def _parse_entity_response(self, response_text: str) -> Dict:
        """Parse Mistral's entity extraction response (with product_attributes support)"""
        try:
            import re

            # Remove markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith('```'):
                # Remove ```json or ``` at start and ``` at end
                cleaned = re.sub(r'^```(?:json)?\s*\n', '', cleaned)
                cleaned = re.sub(r'\n```\s*$', '', cleaned)

            # Try to extract JSON from response - be lenient with formatting
            # First attempt: clean JSON parsing
            try:
                json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    logger.debug(f"Parsed entities: {result}")
                    return result
            except json.JSONDecodeError as e:
                # Log the specific JSON error for debugging
                logger.warning(f"JSON parsing failed: {str(e)}")
                logger.debug(f"Problematic JSON snippet: {cleaned[:500]}...")

                # Second attempt: extract arrays for each field individually
                logger.warning("Trying field-by-field extraction")

                result = {
                    'order_numbers': [],
                    'product_names': [],
                    'product_codes': [],
                    'product_quantities': [],
                    'product_prices': [],
                    'dates': [],
                    'amounts': [],
                    'references': [],
                    'urgency_level': 'medium',
                    'sentiment': 'neutral'
                }

                # Extract arrays (PHASE 1: now includes product_codes, quantities, prices)
                for field in ['order_numbers', 'product_names', 'product_codes', 'product_quantities',
                              'product_prices', 'dates', 'amounts', 'references']:
                    array_match = re.search(rf'"{field}"\s*:\s*\[(.*?)\]', cleaned, re.DOTALL)
                    if array_match:
                        items = re.findall(r'"([^"]+)"', array_match.group(1))
                        result[field] = items

                # Extract single values
                urgency_match = re.search(r'"urgency_level"\s*:\s*"([^"]+)"', cleaned)
                if urgency_match:
                    result['urgency_level'] = urgency_match.group(1)

                sentiment_match = re.search(r'"sentiment"\s*:\s*"([^"]+)"', cleaned)
                if sentiment_match:
                    result['sentiment'] = sentiment_match.group(1)

                logger.debug(f"Parsed entities via field extraction: {result}")
                return result

        except Exception as e:
            logger.error(f"Error parsing entity response: {e}")
            logger.debug(f"Full response text: {response_text[:500]}...")

        return {
            'order_numbers': [],
            'product_names': [],
            'product_codes': [],
            'product_quantities': [],
            'product_prices': [],
            'dates': [],
            'amounts': [],
            'references': []
        }

    def _validate_entity_extraction(self, entities: Dict, original_text: str, retry_count: int) -> bool:
        """
        Validate if entity extraction is complete and reasonable

        Args:
            entities: Extracted entities
            original_text: Original email text
            retry_count: Current retry attempt

        Returns:
            True if extraction seems valid, False if retry needed
        """
        # Don't retry if already retried
        if retry_count > 0:
            return True

        # Check if text contains obvious product indicators but no products extracted
        text_lower = original_text.lower()
        has_product_indicators = any(indicator in text_lower for indicator in [
            'doctor blade', 'seal', 'tape', 'product', 'item', 'art.', 'art -', 'quantity'
        ])

        product_names = entities.get('product_names', [])
        product_codes = entities.get('product_codes', [])
        product_prices = entities.get('product_prices', [])
        amounts = entities.get('amounts', [])

        # If text seems to contain products but none extracted, retry
        if has_product_indicators and len(product_names) == 0:
            logger.warning(f"Text contains product indicators but no products extracted. Text length: {len(original_text)}")
            return False

        # FIX: Check product_prices (new format) OR amounts (old format)
        # If text contains price/amount indicators but no prices extracted
        has_price_indicators = any(indicator in text_lower for indicator in ['eur', 'price', 'cost', '$', '€'])
        prices_extracted = len(product_prices) > 0 or len(amounts) > 0

        if has_price_indicators and not prices_extracted and len(product_names) > 0:
            logger.warning("Text contains pricing information but no product_prices extracted")
            return False

        # Extraction seems reasonable
        logger.info(f"Validation passed: {len(product_names)} products, {len(product_codes)} codes, {len(product_prices)} prices")
        return True

    def extract_product_attributes(self, product_name: str) -> Dict:
        """
        Extract structured attributes from product name for matching without codes

        Args:
            product_name: Full product name/description

        Returns:
            Dictionary of extracted attributes
        """
        import re

        attributes = {
            'brand': None,
            'product_line': None,
            'machine_type': None,
            'dimensions': {
                'width': None,
                'height': None,
                'thickness': None
            },
            'color': None,
            'length': None
        }

        text_upper = product_name.upper()

        # Brand detection
        brands = ['3M', 'DUROSEAL', 'HEAT SEAL', 'BOBST', 'W&H']
        for brand in brands:
            if brand in text_upper:
                attributes['brand'] = brand
                break

        # Product line
        if 'CUSHION MOUNT' in text_upper:
            attributes['product_line'] = 'Cushion Mount'
        elif 'DUROSEAL' in text_upper or 'DURO SEAL' in text_upper:
            attributes['product_line'] = 'DuroSeal'
        elif 'HEAT SEAL' in text_upper:
            attributes['product_line'] = 'Heat Seal'

        # Machine type (16S, 26S, 20SIX)
        machine_match = re.search(r'\b(16S|26S|20SIX)\b', text_upper)
        if machine_match:
            attributes['machine_type'] = machine_match.group(1)

        # Dimensions - Width (only with explicit context to avoid confusion with product codes)
        # FIXED: Removed standalone number pattern that was matching product codes like "928" or "234"
        width_patterns = [
            r'(\d{2,4})\s*mm\s*x',          # "12mm x" or "685 mm x"
            r'(\d{2,4})\s*x\s*[\d\.,]',     # "685 x 0.55" or "12 x 44"
            r'[Bb]reite:?\s*(\d{2,4})',     # "Breite: 50" or "breite 685" (German: width)
            r'[Ww]idth:?\s*(\d{2,4})',      # "Width: 50" or "width 685"
            r',\s*(\d{2,4})\s*mm',          # ", 685 mm" (in specification lists)
        ]

        for pattern in width_patterns:
            width_match = re.search(pattern, product_name)
            if width_match:
                try:
                    width = int(width_match.group(1))
                    # Reasonable width range (10-3000mm)
                    if 10 <= width <= 3000:
                        attributes['dimensions']['width'] = width
                        break
                except ValueError:
                    pass

        # Height (look for H suffix or second dimension)
        height_match = re.search(r'(\d{2,4})\s*H\b', text_upper)
        if height_match:
            try:
                attributes['dimensions']['height'] = int(height_match.group(1))
            except ValueError:
                pass

        # Thickness (look for small decimal numbers)
        thickness_match = re.search(r'(\d+[,\.]\d+)\s*mm', product_name)
        if thickness_match:
            try:
                thickness_str = thickness_match.group(1).replace(',', '.')
                thickness = float(thickness_str)
                if 0.1 <= thickness <= 10:  # Reasonable thickness range
                    attributes['dimensions']['thickness'] = thickness
            except ValueError:
                pass

        # Length (23m, 33m) - look for "Rolle à 33m" or similar patterns
        # Need to find the LAST occurrence since "mm" will match first
        length_patterns = [
            r'[^\d](\d{2,3})\s*m\b',  # Preceded by non-digit, 2-3 digit number + m
            r'x\s*(\d+)\s*m',         # x 33m
        ]

        for pattern in length_patterns:
            matches = list(re.finditer(pattern, product_name.lower()))
            if matches:
                # Take last match (to avoid catching "mm" which appears earlier)
                last_match = matches[-1]
                length_val = int(last_match.group(1))
                # Reasonable roll length (10m - 200m)
                if 10 <= length_val <= 200:
                    attributes['length'] = f"{length_val}m"
                    break

        # Color
        colors = {
            'GREY': 'Grey', 'GRAY': 'Grey',
            'BLUE': 'Blue', 'BLAU': 'Blue',
            'BLACK': 'Black', 'SCHWARZ': 'Black',
            'ORANGE': 'Orange',
            'RED': 'Red', 'ROT': 'Red',
            'GREEN': 'Green', 'GRÜN': 'Green'
        }

        for color_key, color_value in colors.items():
            if color_key in text_upper:
                attributes['color'] = color_value
                break

        return attributes

    def normalize_product_codes(self, extracted_data: Dict) -> Dict:
        """
        Normalize and prioritize product codes from extracted data

        Args:
            extracted_data: Dictionary with 'product_codes' and 'product_names'

        Returns:
            Dictionary with normalized codes per product
        """
        import re

        product_codes = extracted_data.get('product_codes', [])
        product_names = extracted_data.get('product_names', [])

        normalized_products = []

        # Process each product
        for idx, product_name in enumerate(product_names):
            # Get code for this product (if available)
            product_code = product_codes[idx] if idx < len(product_codes) else ''

            code_candidates = []

            # 1. Clean the explicit product_code field
            if product_code and product_code not in ['', 'NO_CODE_FOUND', 'unknown']:
                # Remove common prefixes
                clean_code = product_code.replace("3M ", "").replace("Supplier: ", "").strip()

                # Extract base code (before dash/space)
                base_code = re.split(r'[-\s]', clean_code)[0]

                # Check if it looks like a customer code (5-7 digits, no letters)
                # If so, give it lower priority
                is_customer_code = bool(re.match(r'^\d{5,7}$', clean_code))

                code_candidates.append({
                    'code': clean_code,
                    'base_code': base_code,
                    'source': 'explicit_field',
                    'priority': 3 if is_customer_code else 1,  # Customer codes get lower priority
                    'is_customer_code': is_customer_code
                })

            # 2. Extract codes from product name
            # Patterns: SDS###, L####, E####, etc.
            name_patterns = [
                (r'\b(SDS\d+[A-Z]?)\b', 'SDS'),                # SDS025, SDS025A
                (r'\b(L\d{4})\b', 'L'),                        # L1520, L1320
                (r'\b(E\d{4})\b', 'E'),                        # E1015, E1820
                (r'\b(HEAT\s*SEAL\s*\d+)\b', 'HEAT_SEAL'),     # HEAT SEAL 1282
                (r'\b(\d{3,4}-\d{3})\b', 'MANUFACTURER')       # 178-177 format
            ]

            for pattern, code_type in name_patterns:
                matches = re.finditer(pattern, product_name, re.IGNORECASE)
                for match in matches:
                    extracted_code = match.group(1)
                    # Clean up HEAT SEAL spacing
                    if code_type == 'HEAT_SEAL':
                        extracted_code = re.sub(r'\s+', ' ', extracted_code)

                    code_candidates.append({
                        'code': extracted_code,
                        'base_code': extracted_code.split('-')[0],
                        'source': 'product_name',
                        'code_type': code_type,
                        'priority': 2
                    })

            # 3. Determine final code
            if code_candidates:
                # Sort by priority and return best
                code_candidates.sort(key=lambda x: x['priority'])
                best_code = code_candidates[0]

                normalized_products.append({
                    'product_name': product_name,
                    'primary_code': best_code['code'],
                    'base_code': best_code['base_code'],
                    'all_codes': code_candidates,
                    'use_name_matching': False
                })
            else:
                # No codes found - must use name matching
                normalized_products.append({
                    'product_name': product_name,
                    'primary_code': 'NO_CODE_FOUND',
                    'base_code': None,
                    'all_codes': [],
                    'use_name_matching': True
                })

        return {
            'products': normalized_products,
            'total_with_codes': sum(1 for p in normalized_products if not p['use_name_matching']),
            'total_without_codes': sum(1 for p in normalized_products if p['use_name_matching'])
        }
