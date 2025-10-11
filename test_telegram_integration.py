"""
Test Telegram Integration
Complete end-to-end test of the Telegram feedback system
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*80)
print("TELEGRAM INTEGRATION TEST")
print("="*80)
print()

# Test 1: Environment Configuration
print("[1/7] Testing environment configuration...")
try:
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    telegram_enabled = os.getenv('TELEGRAM_ENABLE_NOTIFICATIONS', 'false').lower() == 'true'

    if not telegram_token or telegram_token == 'your_telegram_bot_token_here':
        print("  [SKIP] Telegram bot token not configured")
        print("  To enable: Set TELEGRAM_BOT_TOKEN in .env")
        print("  Get token from @BotFather on Telegram")
        sys.exit(0)

    if not telegram_chat_id or telegram_chat_id == 'your_telegram_chat_id_here':
        print("  [SKIP] Telegram chat ID not configured")
        print("  To enable: Set TELEGRAM_CHAT_ID in .env")
        print("  Get chat ID from @userinfobot on Telegram")
        sys.exit(0)

    if not telegram_enabled:
        print("  [SKIP] Telegram notifications disabled")
        print("  To enable: Set TELEGRAM_ENABLE_NOTIFICATIONS=true in .env")
        sys.exit(0)

    print(f"  [OK] Token: {telegram_token[:20]}...")
    print(f"  [OK] Chat ID: {telegram_chat_id}")
    print(f"  [OK] Enabled: {telegram_enabled}")
except Exception as e:
    print(f"  [FAIL] {e}")
    sys.exit(1)

print()

# Test 2: Import Components
print("[2/7] Testing component imports...")
try:
    from utils.telegram_notifier import TelegramNotifier
    from utils.telegram_message_formatter import TelegramMessageFormatter
    from utils.feedback_storage import FeedbackStorage
    from orchestrator.mistral_feedback_parser import MistralFeedbackParser
    from orchestrator.dspy_training_generator import DSPyTrainingGenerator
    from orchestrator.feedback_processor import FeedbackProcessor
    from orchestrator.dspy_feedback_signatures import FeedbackParser, TrainingExampleGenerator

    print("  [OK] All components imported successfully")
except Exception as e:
    print(f"  [FAIL] Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 3: Initialize Components
print("[3/7] Initializing components...")
try:
    notifier = TelegramNotifier()
    formatter = TelegramMessageFormatter()
    storage = FeedbackStorage()

    print("  [OK] Telegram notifier initialized")
    print("  [OK] Message formatter initialized")
    print("  [OK] Feedback storage initialized")
except Exception as e:
    print(f"  [FAIL] Initialization error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 4: Test Telegram Connection
print("[4/7] Testing Telegram bot connection...")
try:
    bot_info = notifier.get_bot_info()
    if bot_info:
        print(f"  [OK] Bot connected: @{bot_info.get('username')}")
        print(f"  [OK] Bot name: {bot_info.get('first_name')}")
    else:
        print("  [FAIL] Could not get bot info")
        sys.exit(1)
except Exception as e:
    print(f"  [FAIL] Connection error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 5: Send Test Notification
print("[5/7] Sending test notification...")
try:
    # Create sample email and result
    test_email = {
        'subject': 'Test Order - Telegram Integration',
        'from': 'test@example.com',
        'body': 'This is a test email for Telegram integration',
        'message_id': 'test_123'
    }

    test_result = {
        'success': True,
        'intent': {
            'type': 'order_inquiry',
            'confidence': 0.95
        },
        'entities': {
            'company_name': 'Test Company GmbH',
            'customer_name': 'John Doe',
            'product_names': ['Test Product 1', 'Test Product 2'],
            'quantities': [10, 20],
            'prices': [15.50, 25.00]
        },
        'context': {
            'customer_info': {
                'name': 'Test Company GmbH',
                'email': 'test@company.com',
                'phone': '+49 123 456789',
                'match_score': 0.95
            },
            'json_data': {
                'products': [
                    {
                        'default_code': 'TEST001',
                        'name': 'Test Product 1',
                        'match_score': 0.92,
                        'standard_price': 15.50,
                        'extracted_product_name': 'Test Product 1'
                    },
                    {
                        'default_code': 'TEST002',
                        'name': 'Test Product 2',
                        'match_score': 0.88,
                        'standard_price': 25.00,
                        'extracted_product_name': 'Test Product 2'
                    }
                ]
            }
        },
        'odoo_matches': {
            'customer': {
                'id': 12345,
                'name': 'Test Company GmbH',
                'email': 'test@company.com'
            },
            'products': [
                {
                    'json_product': {'default_code': 'TEST001'},
                    'odoo_product': {'id': 67890}
                },
                {
                    'json_product': {'default_code': 'TEST002'},
                    'odoo_product': {'id': 67891}
                }
            ]
        },
        'order_created': {
            'created': False,
            'message': 'Test mode - order not created'
        }
    }

    test_order_id = f"TEST_ORDER_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Send notification
    response = notifier.send_order_notification(
        email=test_email,
        result=test_result,
        order_id=test_order_id
    )

    if response and response.get('success'):
        print(f"  [OK] Test notification sent")
        print(f"  [OK] Order ID: {test_order_id}")
        print(f"  [OK] Message ID: {response.get('message_id')}")
        print(f"  [OK] Check your Telegram for the notification!")
    else:
        print("  [FAIL] Failed to send notification")
        sys.exit(1)

except Exception as e:
    print(f"  [FAIL] Send error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 6: Store Order Result
print("[6/7] Storing order result for feedback...")
try:
    success = storage.store_order_result(
        order_id=test_order_id,
        email=test_email,
        result=test_result,
        telegram_message_id=response.get('message_id')
    )

    if success:
        print(f"  [OK] Order result stored")
        print(f"  [OK] Feedback tracking enabled for {test_order_id}")
    else:
        print("  [FAIL] Failed to store order result")
except Exception as e:
    print(f"  [FAIL] Storage error: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 7: Verify Feedback Storage
print("[7/7] Verifying feedback storage...")
try:
    # Check if order was stored
    stored_order = storage.get_order_result(test_order_id)

    if stored_order:
        print(f"  [OK] Order retrieved from storage")
        print(f"  [OK] Email subject: {stored_order['email']['subject']}")
        print(f"  [OK] Telegram message ID: {stored_order.get('telegram_message_id')}")
    else:
        print("  [WARN] Order not found in storage")

    # Check feedback stats
    stats = storage.get_feedback_stats()
    print(f"  [OK] Total feedback received: {stats.get('feedback_received', 0)}")
    print(f"  [OK] Training examples generated: {stats.get('training_examples_generated', 0)}")

except Exception as e:
    print(f"  [FAIL] Verification error: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*80)
print("INTEGRATION TEST COMPLETE")
print("="*80)
print()
print("Next Steps:")
print("1. Check your Telegram for the test notification")
print("2. Try replying to the notification with feedback, e.g.:")
print("   'Product 1 quantity should be 15'")
print("3. Start the listener: python telegram_bot_listener.py")
print("4. Process real emails: python main.py")
print()
print("Feedback will be stored in: feedback/")
print("- corrections.json - User corrections")
print("- order_results.json - Original processing results")
print("- training_examples.json - DSPy training data")
print()
print("For more info, see:")
print("- TELEGRAM_SETUP_GUIDE.md")
print("- TELEGRAM_IMPLEMENTATION_SUMMARY.md")
print()
