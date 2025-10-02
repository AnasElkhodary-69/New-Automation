"""
RAG Email System - Main Entry Point

This module orchestrates the entire email processing workflow:
1. Read incoming emails
2. Process emails through Mistral AI agent
3. Retrieve relevant information from Odoo and vector store
4. Generate and send responses
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Import custom modules
from email_module.email_reader import EmailReader
from email_module.email_sender import EmailSender
from retriever_module.odoo_connector import OdooConnector
from retriever_module.vector_store import VectorStore
from orchestrator.processor import EmailProcessor
from orchestrator.mistral_agent import MistralAgent

# Custom logging formatter for clean console output
class CleanConsoleFormatter(logging.Formatter):
    """Custom formatter with colors and clean output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }

    def format(self, record):
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname:8}{self.COLORS['RESET']}"

        # Clean up module names
        if record.name.startswith('orchestrator'):
            record.name = f"🤖 {record.name.split('.')[-1]}"
        elif record.name.startswith('retriever'):
            record.name = f"🔍 {record.name.split('.')[-1]}"
        elif record.name.startswith('email_module'):
            record.name = f"📧 {record.name.split('.')[-1]}"
        elif record.name == '__main__':
            record.name = "🚀 main"

        return super().format(record)

# Configure logging with separate formatters for file and console
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_formatter = CleanConsoleFormatter(
    '%(levelname)s │ %(name)s │ %(message)s'
)

# File handler (detailed)
file_handler = logging.FileHandler('logs/rag_email_system.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)

# Console handler (clean) with UTF-8 encoding for emojis
import io
console_handler = logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))
console_handler.setLevel(logging.INFO)  # Only INFO and above on console
console_handler.setFormatter(console_formatter)

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler]
)

# Suppress noisy libraries
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class RAGEmailSystem:
    """Main class to orchestrate the RAG email system"""

    def __init__(self, config_path: str = "config/settings.json"):
        """
        Initialize the RAG Email System with all necessary components

        Args:
            config_path: Path to the main configuration file
        """
        logger.info("Initializing RAG Email System...")

        self.config_path = config_path
        self.config = self._load_config()

        # Initialize all modules
        self.email_reader = None
        self.email_sender = None
        self.odoo_connector = None
        self.vector_store = None
        self.processor = None
        self.ai_agent = None

        self._initialize_modules()

    def _load_config(self) -> Dict:
        """
        Load configuration from JSON file

        Returns:
            Configuration dictionary
        """
        # TODO: Implement configuration loading from JSON file
        logger.info(f"Loading configuration from {self.config_path}")
        return {}

    def _initialize_modules(self):
        """Initialize all system modules"""
        logger.info("Initializing system modules...")

        # TODO: Initialize email reader with IMAP configuration
        self.email_reader = EmailReader()

        # TODO: Initialize email sender with SMTP configuration
        self.email_sender = EmailSender()

        # TODO: Initialize Odoo connector with database configuration
        self.odoo_connector = OdooConnector()

        # TODO: Initialize vector store (FAISS/Qdrant)
        self.vector_store = VectorStore()

        # TODO: Initialize Mistral AI agent for RAG processing
        self.ai_agent = MistralAgent()

        # TODO: Initialize email processor with all dependencies
        self.processor = EmailProcessor(
            odoo_connector=self.odoo_connector,
            vector_store=self.vector_store,
            ai_agent=self.ai_agent
        )

        logger.info("All modules initialized successfully")

    def process_incoming_emails(self) -> List[Dict]:
        """
        Main workflow: Check for new emails and process them

        Returns:
            List of processed email results
        """
        print("\n" + "="*80)
        logger.info("🚀 Starting Email Processing Workflow")
        print("="*80 + "\n")

        try:
            # Step 1: Read unread emails
            logger.info("📧 [1/5] Fetching unread emails from inbox...")
            unread_emails = self.email_reader.fetch_unread_emails()

            if not unread_emails:
                logger.info("✅ No unread emails to process\n")
                return []

            logger.info(f"✅ Found {len(unread_emails)} unread email(s)\n")

            # Step 2: Process each email
            processed_results = []
            for idx, email in enumerate(unread_emails, 1):
                print(f"\n{'='*80}")
                logger.info(f"📨 Processing Email {idx}/{len(unread_emails)}")
                logger.info(f"   Subject: {email.get('subject', 'No Subject')}")
                logger.info(f"   From: {email.get('from', 'Unknown')}")
                print(f"{'='*80}\n")

                # Step 3: Extract intent and required information
                result = self.processor.process_email(email)

                # Step 4: Log the generated response (not sending)
                if result.get('success'):
                    self._log_response(email, result)

                    processed_results.append({
                        'email_id': email.get('id'),
                        'status': 'processed',
                        'result': result
                    })
                    logger.info(f"✅ Email {idx}/{len(unread_emails)} processed successfully\n")
                else:
                    logger.error(f"❌ Failed to process email: {result.get('error')}")
                    processed_results.append({
                        'email_id': email.get('id'),
                        'status': 'failed',
                        'error': result.get('error')
                    })

            print("\n" + "="*80)
            logger.info(f"✅ Workflow Complete: {len(processed_results)} email(s) processed")
            print("="*80 + "\n")

            return processed_results

        except Exception as e:
            logger.error(f"❌ Error in email processing workflow: {str(e)}", exc_info=True)
            return []

    def _log_response(self, original_email: Dict, processing_result: Dict):
        """
        Log the processing result (NEW JSON-BASED WORKFLOW)

        Args:
            original_email: Original email data
            processing_result: Result from email processor
        """
        print("\n" + "="*80)
        logger.info("📊 PROCESSING RESULTS")
        print("="*80 + "\n")

        # Log processing results
        intent = processing_result.get('intent', {})
        entities = processing_result.get('entities', {})
        context = processing_result.get('context', {})

        # Intent
        logger.info(f"🎯 Intent: {intent.get('type')} (confidence: {intent.get('confidence', 0):.0%})")

        # Entities Summary
        product_count = len(entities.get('product_names', []))
        amount_count = len(entities.get('amounts', []))
        ref_count = len(entities.get('references', []))

        logger.info(f"📦 Extracted: {product_count} products, {amount_count} amounts, {ref_count} codes")

        # Customer info
        customer_name = entities.get('customer_name', '')
        company_name = entities.get('company_name', '')
        if company_name:
            logger.info(f"🏢 Company Extracted: {company_name}")
        if customer_name:
            logger.info(f"👤 Contact Extracted: {customer_name}")

        print()

        # Customer match from JSON
        customer_info = context.get('customer_info')
        if customer_info:
            match_score = customer_info.get('match_score', 0)
            country_id = customer_info.get('country_id', False)
            country_name = country_id[1] if isinstance(country_id, list) and len(country_id) > 1 else 'N/A'

            logger.info(f"✅ Customer Found in JSON: {customer_info.get('name')}")
            logger.info(f"   📍 Location: {customer_info.get('city', 'N/A')}, {country_name}")
            logger.info(f"   📧 Email: {customer_info.get('email', 'N/A')}")
            logger.info(f"   📞 Phone: {customer_info.get('phone', 'N/A')}")
            logger.info(f"   📊 Match Score: {match_score:.0%}")
        else:
            logger.warning(f"⚠️  Customer NOT found in JSON database")

        print()

        # Product matches from JSON
        json_data = context.get('json_data', {})
        products = json_data.get('products', [])
        if products:
            # Keep ALL products - don't deduplicate (each extracted line is unique even if same DB product)
            # Use extracted_product_name to distinguish between different requests
            unique_by_extraction = list({p.get('extracted_product_name', p.get('name')): p for p in products}.values())
            match_rate = len(unique_by_extraction) / product_count * 100 if product_count > 0 else 0
            logger.info(f"✅ Products Matched in JSON: {len(unique_by_extraction)}/{product_count} ({match_rate:.0f}%)")

            # Show ALL matched products
            logger.info(f"\n   📦 ALL MATCHED PRODUCTS:")
            for idx, prod in enumerate(unique_by_extraction, 1):
                prod_name = prod.get('name', 'Unknown')
                prod_code = prod.get('default_code', 'N/A')
                prod_score = prod.get('match_score', 0)
                prod_price = prod.get('standard_price', 0)
                extracted_name = prod.get('extracted_product_name', prod_name)
                logger.info(f"   [{idx:2d}] {prod_name[:70]} | Code: {prod_code:20s} | Score: {prod_score:.0%} | Price: €{prod_price:.2f}")
                # Show extracted description if different from DB name
                if extracted_name and extracted_name != prod_name:
                    logger.info(f"        → Requested as: {extracted_name[:70]}")

            # Show which products were NOT matched
            if len(unique_by_extraction) < product_count:
                logger.warning(f"\n   ⚠️  UNMATCHED PRODUCTS: {product_count - len(unique_by_extraction)}")
                # Build set of all extracted product names that were successfully matched
                matched_extracted_names = {p.get('extracted_product_name', '') for p in products if p.get('extracted_product_name')}
                # Get all extracted product names from Mistral
                extracted_names = entities.get('product_names', [])
                # Find which extracted names are NOT in the matched set
                unmatched = []
                for name in extracted_names:
                    if name not in matched_extracted_names:
                        unmatched.append(name)
                if unmatched:
                    for idx, name in enumerate(unmatched, 1):
                        logger.warning(f"      [{idx}] {name[:70]}")
        else:
            logger.warning(f"⚠️  No products matched in JSON database")

        print("\n" + "="*80)
        logger.info("✅ PROCESSING COMPLETE - WORKFLOW STOPPED")
        print("="*80 + "\n")

        # Display organized summary
        self._display_summary(customer_info, entities, products, context)

        logger.info("Full details saved to logs/rag_email_system.log")

    def _display_summary(self, customer_info: Optional[Dict], entities: Dict, products: List[Dict], context: Dict):
        """
        Display organized summary table with customer details, order details, and shipping address

        Args:
            customer_info: Customer information from database
            entities: Extracted entities
            products: Matched products
            context: Processing context
        """
        print("\n" + "="*100)
        logger.info("ORDER SUMMARY")
        print("="*100 + "\n")

        # Customer Details Section
        logger.info("CUSTOMER DETAILS:")
        logger.info("-" * 100)

        if customer_info:
            company = customer_info.get('name', 'N/A')
            contact = entities.get('customer_name', 'N/A')
            email = customer_info.get('email', 'N/A')
            phone = customer_info.get('phone', 'N/A')
            ref = customer_info.get('ref', 'N/A')

            logger.info(f"  Company Name        : {company}")
            logger.info(f"  Contact Person      : {contact}")
            logger.info(f"  Email               : {email}")
            logger.info(f"  Phone               : {phone}")
            logger.info(f"  Customer Reference  : {ref}")
        else:
            logger.info("  No customer information available")

        print()

        # Shipping Address Section
        logger.info("SHIPPING ADDRESS:")
        logger.info("-" * 100)

        # Always prioritize extracted addresses from email body if available
        addresses = entities.get('addresses', [])

        if addresses:
            # Use address from email body (highest priority)
            # Encode safely for Windows console (replace problematic Unicode chars)
            safe_address = addresses[0].encode('ascii', errors='replace').decode('ascii')
            logger.info(f"  Address (from email): {safe_address}")
        elif customer_info:
            # Fallback to database address
            street = customer_info.get('street', 'N/A')
            zip_code = customer_info.get('zip', 'N/A')
            city = customer_info.get('city', 'N/A')
            country_id = customer_info.get('country_id', False)
            country = country_id[1] if isinstance(country_id, list) and len(country_id) > 1 else 'N/A'

            # Only show if we have real data (not False)
            if street and street != 'N/A' and street != False:
                logger.info(f"  Street              : {street}")
            if zip_code and zip_code != 'N/A' and zip_code != False:
                logger.info(f"  Postal Code         : {zip_code}")
            if city and city != 'N/A' and city != False:
                logger.info(f"  City                : {city}")
            if country and country != 'N/A':
                logger.info(f"  Country             : {country}")

            # If all fields are False/N/A, show message
            if (not street or street == False or street == 'N/A') and \
               (not city or city == False or city == 'N/A'):
                logger.info("  No shipping address in database")
        else:
            logger.info("  No shipping address available")

        print()

        # Order Details Section
        logger.info("ORDER DETAILS:")
        logger.info("-" * 100)

        # Get unique products
        unique_products = list({p.get('extracted_product_name', p.get('name')): p for p in products}.values()) if products else []
        total_items = len(unique_products)

        logger.info(f"  Total Items         : {total_items}")
        logger.info(f"  Order Date          : {entities.get('dates', ['N/A'])[0] if entities.get('dates') else 'N/A'}")

        print()

        # Products Table
        if unique_products:
            logger.info("PRODUCTS:")
            logger.info("-" * 100)
            logger.info(f"  {'No.':<5} {'Product Code':<25} {'Product Name':<45} {'Match':<8} {'Price':<12}")
            logger.info("-" * 100)

            total_price = 0
            for idx, prod in enumerate(unique_products, 1):
                code = prod.get('default_code', 'N/A')[:24]
                name = prod.get('name', 'Unknown')[:44]
                score = prod.get('match_score', 0)
                price = prod.get('standard_price', 0)
                total_price += price

                logger.info(f"  {idx:<5} {code:<25} {name:<45} {score:>6.0%}   EUR {price:>8.2f}")

            logger.info("-" * 100)
            logger.info(f"  {'ESTIMATED TOTAL (Database Prices)':<76} EUR {total_price:>8.2f}")
            logger.info("-" * 100)
        else:
            logger.info("  No products in order")

        print("\n" + "="*100 + "\n")

    # def _send_response(self, original_email: Dict, response_text: str):
    #     """
    #     Send email response (COMMENTED OUT - Currently logging only)
    #
    #     Args:
    #         original_email: Original email to reply to
    #         response_text: Generated response text
    #     """
    #     logger.info("Sending email response...")
    #
    #     try:
    #         self.email_sender.send_reply(
    #             to_address=original_email.get('from'),
    #             subject=f"Re: {original_email.get('subject')}",
    #             body=response_text,
    #             in_reply_to=original_email.get('message_id')
    #         )
    #         logger.info("Response sent successfully")
    #     except Exception as e:
    #         logger.error(f"Failed to send response: {str(e)}")

    def run_continuous(self, interval_seconds: int = 60):
        """
        Run the system continuously, checking for emails at regular intervals

        Args:
            interval_seconds: Time between email checks
        """
        import time

        logger.info(f"Starting continuous mode (checking every {interval_seconds} seconds)")

        # TODO: Implement continuous monitoring with proper error handling
        # and graceful shutdown

        try:
            while True:
                self.process_incoming_emails()
                logger.info(f"Waiting {interval_seconds} seconds before next check...")
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal, stopping...")
            self.shutdown()

    def shutdown(self):
        """Cleanup and shutdown all modules"""
        logger.info("Shutting down RAG Email System...")

        # TODO: Implement proper cleanup for all modules
        # Close database connections, email connections, etc.

        if self.email_reader:
            self.email_reader.close()

        if self.odoo_connector:
            self.odoo_connector.close()

        if self.vector_store:
            self.vector_store.close()

        logger.info("Shutdown complete")


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("RAG Email System Starting...")
    logger.info("=" * 60)

    try:
        # Initialize the system
        system = RAGEmailSystem()

        # Run single batch process (use run_continuous for daemon mode)
        system.process_incoming_emails()

        # Uncomment below to run in continuous mode
        # system.run_continuous(interval_seconds=60)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("RAG Email System stopped")


if __name__ == "__main__":
    main()
