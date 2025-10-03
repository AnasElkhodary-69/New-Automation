"""
Step Logger Module

Creates separate log files for each processing step of an email
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class StepLogger:
    """Logs each processing step to separate files"""

    def __init__(self, base_dir: str = "logs/email_steps"):
        """
        Initialize Step Logger

        Args:
            base_dir: Base directory for step logs
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.current_email_dir = None

    def start_email_log(self, email_id: str):
        """
        Create a new directory for this email's step logs

        Args:
            email_id: Unique identifier for the email
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_email_id = email_id.replace('<', '').replace('>', '').replace('/', '_')[:50]
        dir_name = f"{timestamp}_{safe_email_id}"

        self.current_email_dir = self.base_dir / dir_name
        self.current_email_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created step log directory: {self.current_email_dir}")

    def log_step_1_email_parsing(self, email_data: Dict):
        """
        Log Step 1: Email Parsing

        Args:
            email_data: Original parsed email data
        """
        if not self.current_email_dir:
            logger.warning("No email log directory initialized")
            return

        log_file = self.current_email_dir / "1_email_parsing.json"

        # Create readable summary instead of full data dump
        body_preview = email_data.get('body', '')[:300] + '...' if len(email_data.get('body', '')) > 300 else email_data.get('body', '')

        summary_data = {
            'step': 'Email Parsing',
            'email_info': {
                'from': email_data.get('from'),
                'to': email_data.get('to'),
                'subject': email_data.get('subject'),
                'date': email_data.get('date')
            },
            'content_summary': {
                'body_length': len(email_data.get('body', '')),
                'body_preview': body_preview,
                'has_html': bool(email_data.get('body_html')),
                'attachments_count': len(email_data.get('attachments', [])),
                'attachment_names': [att.get('filename') for att in email_data.get('attachments', [])]
            }
        }

        self._write_json(log_file, summary_data)
        logger.info(f"   Logged Step 1: Email Parsing -> {log_file.name}")

    def log_step_2_entity_extraction(self, intent: Dict, entities: Dict):
        """
        Log Step 2: Entity Extraction (Mistral AI output)

        Args:
            intent: Classified intent from Mistral
            entities: Extracted entities from Mistral
        """
        if not self.current_email_dir:
            logger.warning("No email log directory initialized")
            return

        log_file = self.current_email_dir / "2_entity_extraction.json"

        # Create readable summary
        extraction_summary = {
            'step': 'Entity Extraction (Mistral AI)',
            'intent': {
                'type': intent.get('type'),
                'confidence': f"{intent.get('confidence', 0):.0%}",
                'sub_type': intent.get('sub_type'),
                'reasoning': intent.get('reasoning', '')[:200]
            },
            'customer_info': {
                'company': entities.get('company_name'),
                'contact': entities.get('customer_name'),
                'emails': entities.get('customer_emails', []),
                'phones': entities.get('phone_numbers', []),
                'addresses': entities.get('addresses', [])
            },
            'extracted_products': {
                'count': len(entities.get('product_names', [])),
                'product_names': entities.get('product_names', []),
                'product_codes': entities.get('product_codes', []),
                'quantities': entities.get('product_quantities', []),
                'prices': entities.get('product_prices', [])
            },
            'other_data': {
                'dates': entities.get('dates', []),
                'references': entities.get('references', []),
                'urgency': entities.get('urgency_level'),
                'sentiment': entities.get('sentiment')
            }
        }

        self._write_json(log_file, extraction_summary)
        logger.info(f"   Logged Step 2: Entity Extraction -> {log_file.name}")

    def log_step_3_rag_input(self, intent: Dict, entities: Dict, search_criteria: Dict):
        """
        Log Step 3: Data given to RAG for filtration

        Args:
            intent: Intent classification
            entities: Extracted entities
            search_criteria: Specific search criteria sent to vector store
        """
        if not self.current_email_dir:
            logger.warning("No email log directory initialized")
            return

        log_file = self.current_email_dir / "3_rag_input.json"

        # Create readable summary
        rag_input_summary = {
            'step': 'RAG Input (Search Criteria)',
            'intent': intent.get('type'),
            'confidence': f"{intent.get('confidence', 0):.0%}",
            'customer_search_criteria': search_criteria.get('customer_search', {}),
            'product_search_criteria': {
                'products_to_search': len(search_criteria.get('product_search', {}).get('product_names', [])),
                'product_names': search_criteria.get('product_search', {}).get('product_names', []),
                'product_codes': search_criteria.get('product_search', {}).get('product_codes', [])
            }
        }

        self._write_json(log_file, rag_input_summary)
        logger.info(f"   Logged Step 3: RAG Input -> {log_file.name}")

    def log_step_4_rag_output(self, context: Dict, match_statistics: Dict = None):
        """
        Log Step 4: Data outcome from RAG filtration

        Args:
            context: Retrieved context from vector store
            match_statistics: Optional statistics about matches
        """
        if not self.current_email_dir:
            logger.warning("No email log directory initialized")
            return

        log_file = self.current_email_dir / "4_rag_output.json"

        # Create readable summary
        customer_info = context.get('customer_info')
        products = context.get('json_data', {}).get('products', [])

        # Helper to safely get string values (handle False/None)
        def safe_str(value):
            return value if value and value is not False else None

        # Helper to safely get country from country_id field
        def safe_country(customer):
            if not customer:
                return None
            country_id = customer.get('country_id')
            if isinstance(country_id, list) and len(country_id) > 1:
                return country_id[1]
            return None

        rag_output_summary = {
            'step': 'RAG Output (Search Results)',
            'customer_match': {
                'found': customer_info is not None,
                'company_name': safe_str(customer_info.get('name')) if customer_info else None,
                'match_score': f"{customer_info.get('match_score', 0):.0%}" if customer_info else None,
                'customer_ref': safe_str(customer_info.get('ref')) if customer_info else None,
                'contact_info': {
                    'email': safe_str(customer_info.get('email')) if customer_info else None,
                    'phone': safe_str(customer_info.get('phone')) if customer_info else None,
                    'city': safe_str(customer_info.get('city')) if customer_info else None,
                    'country': safe_country(customer_info)
                } if customer_info else None
            },
            'product_matches': {
                'total_matched': len(products),
                'products': [
                    {
                        'product_code': p.get('default_code'),
                        'product_name': p.get('name'),
                        'match_score': f"{p.get('match_score', 0):.0%}",
                        'extracted_as': p.get('extracted_product_name'),
                        'standard_price': p.get('standard_price')
                    }
                    for p in products
                ]
            },
            'statistics': match_statistics or {}
        }

        self._write_json(log_file, rag_output_summary)
        logger.info(f"   Logged Step 4: RAG Output -> {log_file.name}")

    def _write_json(self, file_path: Path, data: Dict):
        """
        Write data to JSON file with pretty formatting

        Args:
            file_path: Path to write JSON file
            data: Data to write
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"Error writing step log to {file_path}: {e}")

    def get_current_log_dir(self) -> str:
        """Get the current email's log directory path"""
        return str(self.current_email_dir) if self.current_email_dir else None
