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
        self.model = self.config.get('mistral_model', 'mistral-large-latest')
        self.prompts = self._load_prompts()
        self.client = None

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

            # Call Mistral API
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

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

            # Call Mistral API
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2500  # Increased from 1500 to handle large orders
            )

            # Parse response
            result_text = response.choices[0].message.content

            # Log raw response for debugging
            logger.info("="*80)
            logger.info("RAW MISTRAL ENTITY EXTRACTION RESPONSE:")
            if result_text:
                logger.info(f"Length: {len(result_text)} chars")
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

            # Fallback: try to parse as JSON
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned)
            if json_match:
                result = json.loads(json_match.group())
                logger.debug(f"Parsed intent via JSON: {result}")
                return result

        except Exception as e:
            logger.error(f"Error parsing intent response: {e}")
            logger.debug(f"Full response text: {response_text}")

        return {
            'type': 'general_inquiry',
            'confidence': 0.5,
            'sub_type': None,
            'reasoning': 'Could not parse Mistral response'
        }

    def _parse_entity_response(self, response_text: str) -> Dict:
        """Parse Mistral's entity extraction response"""
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
            except json.JSONDecodeError:
                # Second attempt: extract arrays for each field individually
                logger.warning("JSON parsing failed, trying field-by-field extraction")

                result = {
                    'order_numbers': [],
                    'product_names': [],
                    'dates': [],
                    'amounts': [],
                    'references': [],
                    'urgency_level': 'medium',
                    'sentiment': 'neutral'
                }

                # Extract arrays
                for field in ['order_numbers', 'product_names', 'dates', 'amounts', 'references']:
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
            logger.debug(f"Full response text: {response_text}")

        return {
            'order_numbers': [],
            'product_names': [],
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
        amounts = entities.get('amounts', [])

        # If text seems to contain products but none extracted, retry
        if has_product_indicators and len(product_names) == 0:
            logger.warning(f"Text contains product indicators but no products extracted. Text length: {len(original_text)}")
            return False

        # If text contains price/amount indicators but no amounts extracted
        has_price_indicators = any(indicator in text_lower for indicator in ['eur', 'price', 'cost', '$', '€'])
        if has_price_indicators and len(amounts) == 0 and len(product_names) > 0:
            logger.warning("Text contains pricing information but no amounts extracted")
            return False

        # Extraction seems reasonable
        return True
