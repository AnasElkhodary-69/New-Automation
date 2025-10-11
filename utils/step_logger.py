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
                'quantities': entities.get('quantities', []),
                'prices': entities.get('prices', [])
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

    def log_step_5_odoo_matching(self, odoo_matches: Dict):
        """
        Log Step 5: Odoo Database Matching

        Args:
            odoo_matches: Odoo matching results
        """
        if not self.current_email_dir:
            logger.warning("No email log directory initialized")
            return

        log_file = self.current_email_dir / "5_odoo_matching.json"

        # Extract customer match
        odoo_customer = odoo_matches.get('customer')
        customer_summary = None
        if odoo_customer:
            customer_summary = {
                'odoo_id': odoo_customer.get('id'),
                'name': odoo_customer.get('name'),
                'email': odoo_customer.get('email'),
                'phone': odoo_customer.get('phone'),
                'city': odoo_customer.get('city'),
                'country_id': odoo_customer.get('country_id')
            }

        # Extract product matches
        products_summary = []
        for match in odoo_matches.get('products', []):
            odoo_product = match.get('odoo_product')
            if odoo_product:
                products_summary.append({
                    'odoo_id': odoo_product.get('id'),
                    'product_code': odoo_product.get('default_code'),
                    'product_name': odoo_product.get('name'),
                    'extracted_as': match.get('extracted_name'),
                    'match_method': match.get('match_method'),
                    'list_price': odoo_product.get('list_price'),
                    'standard_price': odoo_product.get('standard_price')
                })
            else:
                # Product not found in Odoo
                json_product = match.get('json_product', {})
                products_summary.append({
                    'odoo_id': None,
                    'product_code': json_product.get('default_code'),
                    'product_name': json_product.get('name'),
                    'extracted_as': match.get('extracted_name'),
                    'match_method': None,
                    'status': 'NOT_FOUND_IN_ODOO'
                })

        # Create summary
        odoo_summary = {
            'step': 'Odoo Database Matching',
            'customer_match': {
                'found': customer_summary is not None,
                'odoo_data': customer_summary
            },
            'product_matches': {
                'total_searched': odoo_matches.get('match_summary', {}).get('products_total', 0),
                'matched': odoo_matches.get('match_summary', {}).get('products_matched', 0),
                'failed': odoo_matches.get('match_summary', {}).get('products_failed', 0),
                'products': products_summary
            },
            'summary': odoo_matches.get('match_summary', {})
        }

        self._write_json(log_file, odoo_summary)
        logger.info(f"   Logged Step 5: Odoo Matching -> {log_file.name}")

    def log_step_6_order_creation(self, order_result: Dict):
        """
        Log Step 6: Order Creation in Odoo

        Args:
            order_result: Order creation results
        """
        if not self.current_email_dir:
            logger.warning("No email log directory initialized")
            return

        log_file = self.current_email_dir / "6_order_creation.json"

        # Create summary
        order_summary = {
            'step': 'Order Creation in Odoo',
            'created': order_result.get('created', False),
            'timestamp': datetime.now().isoformat()
        }

        if order_result.get('created'):
            order_summary['order_details'] = {
                'order_id': order_result.get('order_id'),
                'order_name': order_result.get('order_name'),
                'amount_total': order_result.get('amount_total'),
                'state': order_result.get('state'),
                'line_count': order_result.get('line_count'),
                'customer_id': order_result.get('customer_id'),
                'customer_name': order_result.get('customer_name')
            }
        else:
            order_summary['failure_reason'] = order_result.get('reason', 'unknown')
            order_summary['message'] = order_result.get('message', 'Order creation failed')

        self._write_json(log_file, order_summary)
        logger.info(f"   Logged Step 6: Order Creation -> {log_file.name}")

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

    def create_summary_file(self, email_data: Dict, processing_result: Dict):
        """
        Create a comprehensive summary file with all processing steps

        Args:
            email_data: Original email data
            processing_result: Complete processing result
        """
        if not self.current_email_dir:
            logger.warning("No email log directory initialized")
            return

        summary_file = self.current_email_dir / "SUMMARY.json"
        txt_summary = self.current_email_dir / "SUMMARY.txt"

        intent = processing_result.get('intent', {})
        entities = processing_result.get('entities', {})
        context = processing_result.get('context', {})
        odoo_matches = processing_result.get('odoo_matches', {})
        order_created = processing_result.get('order_created', {})
        success = processing_result.get('success', False)

        # Customer info
        customer_info = context.get('customer_info')
        odoo_customer = odoo_matches.get('customer')

        # Products
        json_products = context.get('json_data', {}).get('products', [])
        odoo_product_list = odoo_matches.get('products', [])

        # Build comprehensive summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'original_email': {
                'from': email_data.get('from'),
                'to': email_data.get('to'),
                'subject': email_data.get('subject'),
                'date': email_data.get('date'),
                'message_id': email_data.get('message_id')
            },
            'intent_classification': {
                'type': intent.get('type'),
                'confidence': f"{intent.get('confidence', 0):.0%}",
                'sub_type': intent.get('sub_type')
            },
            'extracted_entities': {
                'company_name': entities.get('company_name'),
                'contact_person': entities.get('customer_name'),
                'emails': entities.get('customer_emails', []),
                'phones': entities.get('phone_numbers', []),
                'addresses': entities.get('addresses', []),
                'product_count': len(entities.get('product_names', [])),
                'products_extracted': [
                    {
                        'name': entities.get('product_names', [])[i] if i < len(entities.get('product_names', [])) else None,
                        'code': entities.get('product_codes', [])[i] if i < len(entities.get('product_codes', [])) else None,
                        'quantity': entities.get('quantities', [])[i] if i < len(entities.get('quantities', [])) else None,
                        'price': entities.get('prices', [])[i] if i < len(entities.get('prices', [])) else None
                    }
                    for i in range(len(entities.get('product_names', [])))
                ]
            },
            'company_matching': {
                'json_match': {
                    'found': customer_info is not None,
                    'name': customer_info.get('name') if customer_info else None,
                    'ref': customer_info.get('ref') if customer_info else None,
                    'match_score': f"{customer_info.get('match_score', 0):.0%}" if customer_info else None,
                    'email': customer_info.get('email') if customer_info else None,
                    'phone': customer_info.get('phone') if customer_info else None
                },
                'odoo_match': {
                    'found': odoo_customer is not None,
                    'odoo_id': odoo_customer.get('id') if odoo_customer else None,
                    'name': odoo_customer.get('name') if odoo_customer else None,
                    'email': odoo_customer.get('email') if odoo_customer else None
                }
            },
            'product_matching': {
                'total_extracted': len(entities.get('product_names', [])),
                'json_matched': len(json_products),
                'odoo_matched': odoo_matches.get('match_summary', {}).get('products_matched', 0),
                'match_rate': f"{len(json_products) / len(entities.get('product_names', [])) * 100 if len(entities.get('product_names', [])) > 0 else 0:.0f}%",
                'products': [
                    {
                        'extracted_as': entities.get('product_names', [])[i] if i < len(entities.get('product_names', [])) else None,
                        'matched_code': json_products[i].get('default_code') if i < len(json_products) else None,
                        'matched_name': json_products[i].get('name') if i < len(json_products) else None,
                        'match_score': f"{json_products[i].get('match_score', 0):.0%}" if i < len(json_products) else None,
                        'in_odoo': any(m.get('odoo_product', {}).get('default_code') == json_products[i].get('default_code') for m in odoo_product_list) if i < len(json_products) else False
                    }
                    for i in range(len(entities.get('product_names', [])))
                ]
            },
            'order_creation': {
                'created': order_created.get('created', False),
                'order_id': order_created.get('order_id') if order_created.get('created') else None,
                'order_name': order_created.get('order_name') if order_created.get('created') else None,
                'amount_total': order_created.get('amount_total') if order_created.get('created') else None,
                'state': order_created.get('state') if order_created.get('created') else None
            },
            'processing_stats': {
                'token_usage': processing_result.get('token_usage', {}),
                'log_directory': str(self.current_email_dir)
            }
        }

        # Write JSON summary
        self._write_json(summary_file, summary)
        logger.info(f"   Created summary file: {summary_file.name}")

        # Write human-readable text summary
        self._write_text_summary(txt_summary, summary)
        logger.info(f"   Created text summary: {txt_summary.name}")

    def _write_text_summary(self, file_path: Path, summary: Dict):
        """
        Write human-readable text summary

        Args:
            file_path: Path to write text file
            summary: Summary data
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("EMAIL PROCESSING SUMMARY\n")
                f.write("="*80 + "\n\n")

                # Original Email
                f.write("ORIGINAL EMAIL\n")
                f.write("-" * 80 + "\n")
                orig = summary['original_email']
                f.write(f"From:    {orig['from']}\n")
                f.write(f"Subject: {orig['subject']}\n")
                f.write(f"Date:    {orig['date']}\n\n")

                # Intent
                f.write("INTENT CLASSIFICATION\n")
                f.write("-" * 80 + "\n")
                intent = summary['intent_classification']
                f.write(f"Type:       {intent['type']}\n")
                f.write(f"Confidence: {intent['confidence']}\n")
                f.write(f"Sub-Type:   {intent.get('sub_type', 'N/A')}\n\n")

                # Extracted Entities
                f.write("EXTRACTED INFORMATION\n")
                f.write("-" * 80 + "\n")
                entities = summary['extracted_entities']
                f.write(f"Company:       {entities.get('company_name', 'N/A')}\n")
                f.write(f"Contact:       {entities.get('contact_person', 'N/A')}\n")
                f.write(f"Email:         {', '.join(entities.get('emails', [])) or 'N/A'}\n")
                f.write(f"Phone:         {', '.join(entities.get('phones', [])) or 'N/A'}\n")
                f.write(f"Products:      {entities['product_count']}\n\n")

                # Company Matching
                f.write("COMPANY MATCHING\n")
                f.write("-" * 80 + "\n")
                company = summary['company_matching']
                json_match = company['json_match']
                odoo_match = company['odoo_match']

                if json_match['found']:
                    f.write(f"JSON Database:  [OK] FOUND\n")
                    f.write(f"  Name:         {json_match['name']}\n")
                    f.write(f"  Match Score:  {json_match['match_score']}\n")
                    f.write(f"  Ref:          {json_match['ref']}\n")
                else:
                    f.write(f"JSON Database:  [NOT FOUND]\n")

                if odoo_match['found']:
                    f.write(f"Odoo Database:  [OK] FOUND\n")
                    f.write(f"  Odoo ID:      {odoo_match['odoo_id']}\n")
                    f.write(f"  Name:         {odoo_match['name']}\n")
                else:
                    f.write(f"Odoo Database:  [NOT FOUND]\n")
                f.write("\n")

                # Product Matching
                f.write("PRODUCT MATCHING\n")
                f.write("-" * 80 + "\n")
                products = summary['product_matching']
                f.write(f"Extracted:     {products['total_extracted']}\n")
                f.write(f"JSON Matched:  {products['json_matched']}\n")
                f.write(f"Odoo Matched:  {products['odoo_matched']}\n")
                f.write(f"Match Rate:    {products['match_rate']}\n\n")

                if products['products']:
                    f.write("Product Details:\n")
                    for idx, prod in enumerate(products['products'], 1):
                        f.write(f"  {idx}. {prod['extracted_as']}\n")
                        if prod['matched_code']:
                            f.write(f"     -> Matched: {prod['matched_code']} - {prod['matched_name']}\n")
                            f.write(f"     -> Score: {prod['match_score']}\n")
                            f.write(f"     -> In Odoo: {'[OK] Yes' if prod['in_odoo'] else '[NO]'}\n")
                        else:
                            f.write(f"     -> [NOT MATCHED]\n")
                    f.write("\n")

                # Order Creation
                order = summary['order_creation']
                if order['created']:
                    f.write("ORDER CREATED IN ODOO\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"Order Number:  {order['order_name']}\n")
                    f.write(f"Order ID:      {order['order_id']}\n")
                    f.write(f"Total Amount:  EUR {order['amount_total']:.2f}\n")
                    f.write(f"State:         {order['state']}\n\n")

                # Processing Status
                f.write("PROCESSING STATUS\n")
                f.write("-" * 80 + "\n")
                f.write(f"Success:       {'[OK] YES' if summary['success'] else '[FAILED] NO'}\n")
                f.write(f"Timestamp:     {summary['timestamp']}\n")
                f.write(f"Log Directory: {summary['processing_stats']['log_directory']}\n")

                f.write("\n" + "="*80 + "\n")

        except Exception as e:
            logger.error(f"Error writing text summary to {file_path}: {e}")
