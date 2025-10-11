"""
Claude Agent Module

Handles interaction with Claude API for:
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


class ClaudeAgent:
    """Claude AI agent for RAG-based email processing"""

    def __init__(self, config_path: str = "config/settings.json"):
        """
        Initialize Claude Agent

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.api_key = self.config.get('claude_api_key', '')
        self.model = self.config.get('claude_model', 'claude-3-opus-20240229')
        self.prompts = self._load_prompts()
        self.client = None

        self._initialize_client()

    def _load_config(self) -> Dict:
        """
        Load configuration

        Returns:
            Configuration dictionary
        """
        logger.info(f"Loading Claude configuration")

        try:
            from dotenv import load_dotenv
            load_dotenv()

            return {
                "claude_api_key": os.getenv('CLAUDE_API_KEY', ''),
                "claude_model": "claude-3-opus-20240229",
                "max_tokens": 2000,
                "temperature": 0.7
            }
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {
                "claude_api_key": "",
                "claude_model": "claude-3-opus-20240229",
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
        """Initialize Claude API client"""
        # Check if API key is configured
        if not self.api_key or self.api_key == 'your_claude_api_key_here':
            logger.warning("Claude API key not configured. Running in DEMO mode.")
            logger.warning("Add your API key to .env file: CLAUDE_API_KEY=sk-ant-...")
            self.client = None
            return

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("Claude client initialized")
        except ImportError:
            logger.error("anthropic package not installed. Run: pip install anthropic")
            self.client = None
        except Exception as e:
            logger.error(f"Error initializing Claude client: {e}")
            self.client = None

    def classify_intent(self, subject: str, body: str) -> Dict:
        """
        Classify email intent using Claude

        Args:
            subject: Email subject
            body: Email body

        Returns:
            Intent classification result
        """
        logger.info("Classifying intent with Claude...")

        # Demo mode fallback
        if not self.client:
            return self._demo_classify_intent(subject, body)

        try:
            # Prepare prompt
            prompt = self.prompts.get('intent', '')
            prompt = prompt.format(subject=subject, body=body)

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse response
            result_text = response.content[0].text
            result = self._parse_intent_response(result_text)
            return result

        except Exception as e:
            logger.error(f"Error classifying intent: {str(e)}")
            return self._demo_classify_intent(subject, body)

    def _demo_classify_intent(self, subject: str, body: str) -> Dict:
        """Demo mode intent classification"""
        logger.info("Using DEMO intent classification (no Claude API)")

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

    def extract_entities(self, text: str) -> Dict:
        """
        Extract entities from email text

        Args:
            text: Email text

        Returns:
            Extracted entities dictionary
        """
        logger.info("Extracting entities with Claude...")

        # Demo mode fallback
        if not self.client:
            return self._demo_extract_entities(text)

        try:
            # Prepare prompt
            prompt = self.prompts.get('extraction', '')
            prompt = prompt.format(text=text)

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse response
            result_text = response.content[0].text
            entities = self._parse_entity_response(result_text)
            return entities

        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            return self._demo_extract_entities(text)

    def _demo_extract_entities(self, text: str) -> Dict:
        """Demo mode entity extraction"""
        logger.info("Using DEMO entity extraction (no Claude API)")

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
        logger.info("Generating response with Claude and RAG context...")

        # Demo mode fallback
        if not self.client:
            return self._demo_generate_response(email, intent, entities, context)

        try:
            # Build context-enhanced prompt
            prompt = self._build_rag_prompt(email, intent, entities, context)

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.config['max_tokens'],
                temperature=self.config['temperature'],
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return self._demo_generate_response(email, intent, entities, context)

    def _demo_generate_response(self, email: Dict, intent: Dict, entities: Dict, context: Dict) -> str:
        """Demo mode response generation"""
        logger.info("Using DEMO response generation (no Claude API)")

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
        response += "\n\n[DEMO MODE - Add CLAUDE_API_KEY to .env for AI-generated responses]"

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
        """Parse Claude's intent classification response"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return {
            'type': 'general_inquiry',
            'confidence': 0.5,
            'sub_type': None,
            'reasoning': 'Could not parse Claude response'
        }

    def _parse_entity_response(self, response_text: str) -> Dict:
        """Parse Claude's entity extraction response"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return {
            'order_numbers': [],
            'product_names': [],
            'dates': [],
            'amounts': [],
            'references': []
        }
