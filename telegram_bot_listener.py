"""
Telegram Bot Listener
Background service that listens for user feedback on Telegram
"""

import os
import sys
import logging
import time
import requests
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.feedback_processor import FeedbackProcessor
from utils.feedback_storage import FeedbackStorage
from utils.telegram_notifier import TelegramNotifier
from orchestrator.mistral_feedback_parser import MistralFeedbackParser
from orchestrator.dspy_training_generator import DSPyTrainingGenerator
from orchestrator.dspy_config import setup_dspy

load_dotenv()

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/telegram_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TelegramBotListener:
    """Listen for Telegram messages and process feedback"""

    def __init__(self):
        """Initialize bot listener"""
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = os.getenv('TELEGRAM_ENABLE_NOTIFICATIONS', 'false').lower() == 'true'

        if not all([self.bot_token, self.chat_id, self.enabled]):
            logger.error("Telegram bot not configured properly")
            sys.exit(1)

        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.last_update_id = 0

        # Initialize components
        logger.info("Initializing DSPy...")
        setup_dspy()

        logger.info("Initializing feedback components...")
        self.storage = FeedbackStorage()
        self.notifier = TelegramNotifier()
        self.feedback_parser = MistralFeedbackParser(use_chain_of_thought=True)
        self.training_generator = DSPyTrainingGenerator(use_chain_of_thought=True)

        # Initialize feedback processor
        self.feedback_processor = FeedbackProcessor(
            feedback_parser=self.feedback_parser,
            training_generator=self.training_generator,
            feedback_storage=self.storage,
            telegram_notifier=self.notifier
        )

        logger.info("Telegram bot listener initialized")

    def start(self, poll_interval: int = 2):
        """
        Start listening for messages

        Args:
            poll_interval: Seconds between polling
        """
        logger.info(f"Starting Telegram bot listener (polling every {poll_interval}s)")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                try:
                    # Get new messages
                    updates = self._get_updates()

                    if updates:
                        for update in updates:
                            self._process_update(update)

                    time.sleep(poll_interval)

                except KeyboardInterrupt:
                    logger.info("Received stop signal")
                    break
                except Exception as e:
                    logger.error(f"Error in polling loop: {e}", exc_info=True)
                    time.sleep(poll_interval * 2)  # Wait longer on error

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.shutdown()

    def _get_updates(self) -> list:
        """
        Get new updates from Telegram

        Returns:
            List of updates
        """
        try:
            url = f"{self.api_url}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': 30,
                'allowed_updates': ['message']
            }

            response = requests.get(url, params=params, timeout=35)
            response.raise_for_status()

            data = response.json()

            if data.get('ok'):
                updates = data.get('result', [])

                if updates:
                    # Update last_update_id
                    self.last_update_id = max(update['update_id'] for update in updates)

                return updates

            return []

        except requests.exceptions.Timeout:
            # Timeout is normal with long polling
            return []
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []

    def _process_update(self, update: Dict):
        """
        Process a single update

        Args:
            update: Update from Telegram
        """
        try:
            # Extract message
            message = update.get('message')
            if not message:
                return

            # Get message details
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')
            user_id = message.get('from', {}).get('id')
            message_id = message.get('message_id')

            # Verify chat_id matches (security check)
            if str(chat_id) != str(self.chat_id):
                logger.warning(f"Received message from unauthorized chat: {chat_id}")
                return

            # Ignore empty messages
            if not text.strip():
                return

            # Ignore bot commands (for now)
            if text.startswith('/'):
                logger.info(f"Ignoring command: {text}")
                return

            logger.info(f"Received message: '{text[:50]}...' from user {user_id}")

            # Try to extract order_id from recent messages
            order_id = self._extract_order_id(text, message)

            if not order_id:
                # Send help message
                self.notifier.send_message(
                    "⚠️ Could not identify which order you're referring to.\n\n"
                    "Please reply to the original order notification, or include the order ID in your message."
                )
                return

            # Process feedback
            success = self.feedback_processor.process_feedback(
                order_id=order_id,
                user_message=text,
                telegram_user_id=user_id
            )

            if success:
                logger.info(f"Successfully processed feedback for order {order_id}")
            else:
                logger.error(f"Failed to process feedback for order {order_id}")

        except Exception as e:
            logger.error(f"Error processing update: {e}", exc_info=True)

    def _extract_order_id(self, text: str, message: Dict) -> Optional[str]:
        """
        Extract order ID from message

        Args:
            text: Message text
            message: Full message dict

        Returns:
            Order ID or None
        """
        try:
            # Method 1: Check if replying to a message
            reply_to = message.get('reply_to_message')
            if reply_to:
                reply_text = reply_to.get('text', '')
                # Look for "Order ID: XXX" pattern
                if 'Order ID:' in reply_text:
                    order_id = reply_text.split('Order ID:')[-1].strip().split('\n')[0].strip()
                    return order_id

            # Method 2: Look for order ID in current message
            if 'Order ID:' in text or 'order' in text.lower():
                # Try to extract order ID pattern (e.g., SO12345, ORDER_1, etc.)
                import re
                patterns = [
                    r'Order ID:\s*([A-Z0-9_]+)',
                    r'order\s+([A-Z0-9_]+)',
                    r'(SO\d+)',
                    r'(ORDER_\d+)'
                ]

                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        return match.group(1)

            # Method 3: Check recent orders (last 10 minutes)
            # This is a fallback - we'll get the most recent order
            orders = self.storage._read_json(self.storage.order_results_file)
            if orders:
                # Get most recent order
                recent_order = orders[-1]
                timestamp = recent_order.get('timestamp')

                # Check if it's recent (within 10 minutes)
                if timestamp:
                    from datetime import datetime, timedelta
                    order_time = datetime.fromisoformat(timestamp)
                    if datetime.now() - order_time < timedelta(minutes=10):
                        return recent_order.get('order_id')

            return None

        except Exception as e:
            logger.error(f"Error extracting order ID: {e}")
            return None

    def shutdown(self):
        """Cleanup and shutdown"""
        logger.info("Telegram bot listener stopped")


def main():
    """Main entry point"""
    logger.info("="*60)
    logger.info("Telegram Bot Listener Starting...")
    logger.info("="*60)

    try:
        # Initialize listener
        listener = TelegramBotListener()

        # Start listening
        listener.start(poll_interval=2)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
