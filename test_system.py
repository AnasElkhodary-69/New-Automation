"""
Test the complete RAG Email System
"""

import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_email_connection():
    """Test email IMAP/SMTP connection"""
    print("\n" + "="*60)
    print("TEST 1: Email Connection")
    print("="*60)

    try:
        from email_module.email_reader import EmailReader
        from email_module.email_sender import EmailSender

        # Test email reader
        print("\n[1/2] Testing Email Reader (IMAP)...")
        reader = EmailReader()
        print("[OK] Email Reader initialized")

        # Test fetching emails
        emails = reader.fetch_unread_emails()
        print(f"[OK] Found {len(emails)} unread email(s)")

        if emails:
            print(f"\nSample email:")
            print(f"  From: {emails[0].get('from')}")
            print(f"  Subject: {emails[0].get('subject')}")
            print(f"  Body preview: {emails[0].get('body', '')[:100]}...")

        reader.close()

        # Test email sender
        print("\n[2/2] Testing Email Sender (SMTP)...")
        sender = EmailSender()
        print("[OK] Email Sender initialized")

        print("\n[PASS] Email connection test PASSED")
        return True, emails

    except Exception as e:
        print(f"\n[FAIL] Email connection test FAILED: {e}")
        return False, []


def test_odoo_connection():
    """Test Odoo API connection"""
    print("\n" + "="*60)
    print("TEST 2: Odoo Connection")
    print("="*60)

    try:
        from retriever_module.odoo_connector import OdooConnector

        print("\nConnecting to Odoo...")
        odoo = OdooConnector()
        print(f"[OK] Connected to Odoo (UID: {odoo.uid})")

        # Test query
        print("\nTesting customer query...")
        customer = odoo.query_customer_info(customer_id=1)
        if customer:
            print(f"[OK] Found customer: {customer.get('name')}")
        else:
            print("[INFO] No customer with ID 1 found (this is okay)")

        odoo.close()

        print("\n[PASS] Odoo connection test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] Odoo connection test FAILED: {e}")
        return False


def test_mistral_agent():
    """Test Mistral agent"""
    print("\n" + "="*60)
    print("TEST 3: Mistral Agent")
    print("="*60)

    try:
        from orchestrator.mistral_agent import MistralAgent

        print("\nInitializing Mistral agent...")
        mistral = MistralAgent()
        print("[OK] Mistral agent initialized")

        if not mistral.client:
            print("[INFO] Running in DEMO mode (no API key)")
        else:
            print("[OK] Mistral API client ready")

        # Test intent classification
        print("\nTesting intent classification...")
        intent = mistral.classify_intent(
            subject="Order Status",
            body="Hi, I want to know the status of my recent order."
        )
        print(f"[OK] Intent classified: {intent.get('type')}")

        # Test entity extraction
        print("\nTesting entity extraction...")
        entities = mistral.extract_entities(
            text="I need invoice for order SO12345 amounting to $299.99"
        )
        print(f"[OK] Entities extracted: {len(entities)} types")

        print("\n[PASS] Mistral agent test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] Mistral agent test FAILED: {e}")
        return False


def test_complete_workflow(test_emails):
    """Test the complete email processing workflow"""
    print("\n" + "="*60)
    print("TEST 4: Complete Workflow")
    print("="*60)

    try:
        from email_module.email_reader import EmailReader
        from email_module.email_sender import EmailSender
        from retriever_module.odoo_connector import OdooConnector
        from retriever_module.vector_store import VectorStore
        from orchestrator.processor import EmailProcessor
        from orchestrator.mistral_agent import MistralAgent

        print("\nInitializing all components...")

        # Initialize components
        email_reader = EmailReader()
        email_sender = EmailSender()
        odoo = OdooConnector()
        vector_store = VectorStore()
        mistral = MistralAgent()

        # Initialize processor
        processor = EmailProcessor(
            odoo_connector=odoo,
            vector_store=vector_store,
            ai_agent=mistral
        )

        print("[OK] All components initialized")

        # Test with a sample email
        if test_emails:
            print("\nProcessing real email...")
            email = test_emails[0]
        else:
            print("\nProcessing mock email...")
            email = {
                'id': 'test',
                'from': 'test@example.com',
                'subject': 'Order Status Inquiry',
                'body': 'Hi, I would like to know the status of my order SO12345. Thank you!'
            }

        # Process email
        result = processor.process_email(email)

        if result.get('success'):
            print("\n[OK] Email processed successfully")
            print(f"\nIntent: {result['intent'].get('type')}")
            customer_info = result.get('context', {}).get('customer_info')
            customer_name = customer_info.get('name', 'Unknown') if customer_info else 'Unknown'
            print(f"Customer: {customer_name}")
            print(f"\nGenerated Response Preview:")
            print("-" * 60)
            print(result['response'][:300] + "...")
            print("-" * 60)
        else:
            print(f"\n[FAIL] Processing failed: {result.get('error')}")
            return False

        # Cleanup
        email_reader.close()
        odoo.close()
        vector_store.close()

        print("\n[PASS] Complete workflow test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] Complete workflow test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n")
    print("=" * 60)
    print(" " * 15 + "RAG EMAIL SYSTEM - TESTS")
    print("=" * 60)

    results = []

    # Test 1: Email connection
    email_success, test_emails = test_email_connection()
    results.append(("Email Connection", email_success))

    # Test 2: Odoo connection
    odoo_success = test_odoo_connection()
    results.append(("Odoo Connection", odoo_success))

    # Test 3: Mistral agent
    mistral_success = test_mistral_agent()
    results.append(("Mistral Agent", mistral_success))

    # Test 4: Complete workflow
    if email_success and odoo_success and mistral_success:
        workflow_success = test_complete_workflow(test_emails)
        results.append(("Complete Workflow", workflow_success))
    else:
        print("\n" + "="*60)
        print("SKIPPING Complete Workflow test (prerequisites failed)")
        print("="*60)
        results.append(("Complete Workflow", False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = 0
    for test_name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status:10} {test_name}")
        if success:
            passed += 1

    print(f"\nTotal: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n[SUCCESS] All tests passed! System is ready to use.")
        print("\nTo run the system:")
        print("  python main.py")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
