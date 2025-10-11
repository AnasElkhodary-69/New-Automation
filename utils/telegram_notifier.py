"""
Telegram Notifier
Sends order processing notifications to Telegram
"""

import os
import logging
import requests
from typing import Dict, Optional
from dotenv import load_dotenv
from utils.telegram_message_formatter import TelegramMessageFormatter

load_dotenv()

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send notifications to Telegram bot"""

    def __init__(self):
        """Initialize Telegram notifier"""
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = os.getenv('TELEGRAM_ENABLE_NOTIFICATIONS', 'false').lower() == 'true'

        # Initialize formatter
        self.formatter = TelegramMessageFormatter()

        # Telegram API URL
        if self.bot_token:
            self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        else:
            self.api_url = None

        # Validate configuration
        if self.enabled and not all([self.bot_token, self.chat_id]):
            logger.warning("Telegram notifications enabled but credentials missing - disabling")
            self.enabled = False

        if self.enabled:
            logger.info(f"Telegram notifier initialized (chat_id: {self.chat_id})")
        else:
            logger.info("Telegram notifier disabled")

    def send_order_notification(
        self,
        email: Dict,
        result: Dict,
        order_id: str
    ) -> Optional[Dict]:
        """
        Send order processing notification to Telegram

        Args:
            email: Original email data
            result: Processing result from EmailProcessor
            order_id: Order identifier

        Returns:
            Response from Telegram API or None if disabled/failed
        """
        if not self.enabled:
            logger.debug("Telegram notifications disabled, skipping")
            return None

        try:
            # Format message
            message = self.formatter.format_order_notification(email, result, order_id)

            # Send to Telegram
            response = self._send_message(message)

            if response and response.get('ok'):
                message_id = response['result']['message_id']
                logger.info(f"Telegram notification sent for order {order_id} (msg_id: {message_id})")
                return {
                    'success': True,
                    'order_id': order_id,
                    'message_id': message_id,
                    'chat_id': self.chat_id
                }
            else:
                logger.error(f"Failed to send Telegram notification: {response}")
                return None

        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}", exc_info=True)
            return None

    def send_confirmation(
        self,
        order_id: str,
        correction_summary: Dict
    ) -> bool:
        """
        Send confirmation message after parsing user feedback

        Args:
            order_id: Order identifier
            correction_summary: Parsed corrections from Mistral

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            message = self.formatter.format_confirmation_message(order_id, correction_summary)
            response = self._send_message(message)
            return response and response.get('ok', False)

        except Exception as e:
            logger.error(f"Error sending confirmation: {e}", exc_info=True)
            return False

    def send_clarification(
        self,
        order_id: str,
        question: str
    ) -> bool:
        """
        Send clarification request to user

        Args:
            order_id: Order identifier
            question: Clarification question from Mistral

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            message = self.formatter.format_clarification_message(order_id, question)
            response = self._send_message(message)
            return response and response.get('ok', False)

        except Exception as e:
            logger.error(f"Error sending clarification: {e}", exc_info=True)
            return False

    def send_error(
        self,
        order_id: str,
        error: str
    ) -> bool:
        """
        Send error message to user

        Args:
            order_id: Order identifier
            error: Error description

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            message = self.formatter.format_error_message(order_id, error)
            response = self._send_message(message)
            return response and response.get('ok', False)

        except Exception as e:
            logger.error(f"Error sending error message: {e}", exc_info=True)
            return False

    def send_message(self, message: str) -> Optional[Dict]:
        """
        Send raw message to Telegram (for custom messages)

        Args:
            message: Message text

        Returns:
            Response from Telegram API or None
        """
        if not self.enabled:
            return None

        return self._send_message(message)

    def _send_message(self, message: str) -> Optional[Dict]:
        """
        Internal method to send message via Telegram API

        Args:
            message: Message text

        Returns:
            Response from Telegram API or None
        """
        if not self.api_url or not self.chat_id:
            logger.error("Telegram API not configured")
            return None

        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                # 'parse_mode': 'Markdown',  # Disabled - using plain text to avoid parsing errors
                'disable_web_page_preview': True  # Don't show link previews
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Telegram API error detail: {error_detail}")
                except:
                    logger.error(f"Telegram API response text: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}", exc_info=True)
            return None

    def test_connection(self) -> bool:
        """
        Test Telegram bot connection

        Returns:
            True if connection successful, False otherwise
        """
        if not self.enabled:
            logger.warning("Telegram notifications are disabled")
            return False

        try:
            # Test with a simple message
            message = "✅ Telegram connection test successful!"
            response = self._send_message(message)

            if response and response.get('ok'):
                logger.info("Telegram connection test passed")
                return True
            else:
                logger.error(f"Telegram connection test failed: {response}")
                return False

        except Exception as e:
            logger.error(f"Telegram connection test error: {e}", exc_info=True)
            return False

    def get_bot_info(self) -> Optional[Dict]:
        """
        Get information about the bot

        Returns:
            Bot info or None
        """
        if not self.api_url:
            return None

        try:
            url = f"{self.api_url}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data.get('ok'):
                return data['result']
            return None

        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            return None
