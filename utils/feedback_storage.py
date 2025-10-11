"""
Feedback Storage System
Stores user corrections and generates DSPy training data
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class FeedbackStorage:
    """Store and manage user feedback for DSPy training"""

    def __init__(self, storage_dir: str = "feedback"):
        """
        Initialize feedback storage

        Args:
            storage_dir: Directory to store feedback data
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

        # Storage files
        self.feedback_file = self.storage_dir / "corrections.json"
        self.order_results_file = self.storage_dir / "order_results.json"
        self.training_data_file = self.storage_dir / "training_examples.json"
        self.stats_file = self.storage_dir / "feedback_stats.json"

        # Initialize storage files if they don't exist
        self._initialize_storage()

        logger.info(f"Feedback storage initialized at {self.storage_dir}")

    def _initialize_storage(self):
        """Initialize storage files if they don't exist"""
        for file_path in [self.feedback_file, self.order_results_file,
                          self.training_data_file, self.stats_file]:
            if not file_path.exists():
                self._write_json(file_path, [])
                logger.debug(f"Initialized {file_path.name}")

    def store_order_result(
        self,
        order_id: str,
        email: Dict,
        result: Dict,
        telegram_message_id: Optional[int] = None
    ) -> bool:
        """
        Store order processing result for feedback tracking

        Args:
            order_id: Order identifier
            email: Original email data
            result: Processing result
            telegram_message_id: Telegram message ID if sent

        Returns:
            True if stored successfully
        """
        try:
            # Load existing results
            order_results = self._read_json(self.order_results_file)

            # Create order result entry
            order_entry = {
                'order_id': order_id,
                'timestamp': datetime.now().isoformat(),
                'email': {
                    'subject': email.get('subject', ''),
                    'from': email.get('from', ''),
                    'body': email.get('body', ''),
                    'message_id': email.get('message_id', '')
                },
                'result': {
                    'intent': result.get('intent', {}),
                    'entities': result.get('entities', {}),
                    'context': result.get('context', {}),
                    'odoo_matches': result.get('odoo_matches', {}),
                    'order_created': result.get('order_created', {})
                },
                'telegram_message_id': telegram_message_id,
                'feedback_received': False,
                'feedback_count': 0
            }

            # Append and save
            order_results.append(order_entry)
            self._write_json(self.order_results_file, order_results)

            logger.info(f"Stored order result for {order_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing order result: {e}", exc_info=True)
            return False

    def store_feedback(
        self,
        order_id: str,
        user_message: str,
        mistral_parsing: Dict,
        telegram_user_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Store user feedback with Mistral parsing

        Args:
            order_id: Order identifier
            user_message: Raw user message
            mistral_parsing: Parsed corrections from Mistral
            telegram_user_id: Telegram user ID

        Returns:
            Feedback ID if stored successfully, None otherwise
        """
        try:
            # Generate feedback ID
            feedback_id = f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{order_id}"

            # Get original order result
            original_result = self.get_order_result(order_id)
            if not original_result:
                logger.warning(f"No order result found for {order_id}")
                original_result = {}

            # Load existing feedback
            feedback_list = self._read_json(self.feedback_file)

            # Create feedback entry
            feedback_entry = {
                'feedback_id': feedback_id,
                'order_id': order_id,
                'timestamp': datetime.now().isoformat(),
                'user_message': user_message,
                'telegram_user_id': telegram_user_id,
                'mistral_parsing': mistral_parsing,
                'original_extraction': {
                    'intent': original_result.get('result', {}).get('intent', {}),
                    'entities': original_result.get('result', {}).get('entities', {}),
                    'context': original_result.get('result', {}).get('context', {})
                },
                'status': 'pending_review',
                'dspy_training_ready': False,
                'applied_to_model': False
            }

            # Append and save
            feedback_list.append(feedback_entry)
            self._write_json(self.feedback_file, feedback_list)

            # Update order result feedback count
            self._update_order_feedback_count(order_id)

            # Update stats
            self._update_stats('feedback_received')

            logger.info(f"Stored feedback {feedback_id} for order {order_id}")
            return feedback_id

        except Exception as e:
            logger.error(f"Error storing feedback: {e}", exc_info=True)
            return None

    def store_training_example(
        self,
        feedback_id: str,
        training_example: Dict
    ) -> bool:
        """
        Store DSPy training example generated from feedback

        Args:
            feedback_id: Feedback identifier
            training_example: Training data in DSPy format

        Returns:
            True if stored successfully
        """
        try:
            # Load existing training data
            training_data = self._read_json(self.training_data_file)

            # Create training entry
            training_entry = {
                'training_id': f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'feedback_id': feedback_id,
                'timestamp': datetime.now().isoformat(),
                'signature_type': training_example.get('signature_type'),
                'training_data': training_example.get('training_data', {}),
                'error_analysis': training_example.get('error_analysis', ''),
                'training_weight': training_example.get('training_weight', 1.0),
                'used_in_training': False
            }

            # Append and save
            training_data.append(training_entry)
            self._write_json(self.training_data_file, training_data)

            # Mark feedback as training ready
            self._mark_feedback_training_ready(feedback_id)

            # Update stats
            self._update_stats('training_examples_generated')

            logger.info(f"Stored training example for feedback {feedback_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing training example: {e}", exc_info=True)
            return False

    def get_order_result(self, order_id: str) -> Optional[Dict]:
        """
        Get order processing result by order ID

        Args:
            order_id: Order identifier

        Returns:
            Order result or None if not found
        """
        try:
            order_results = self._read_json(self.order_results_file)
            for result in reversed(order_results):  # Latest first
                if result.get('order_id') == order_id:
                    return result
            return None

        except Exception as e:
            logger.error(f"Error getting order result: {e}")
            return None

    def get_feedback(self, feedback_id: str) -> Optional[Dict]:
        """
        Get feedback by ID

        Args:
            feedback_id: Feedback identifier

        Returns:
            Feedback entry or None if not found
        """
        try:
            feedback_list = self._read_json(self.feedback_file)
            for feedback in feedback_list:
                if feedback.get('feedback_id') == feedback_id:
                    return feedback
            return None

        except Exception as e:
            logger.error(f"Error getting feedback: {e}")
            return None

    def get_training_examples(
        self,
        signature_type: Optional[str] = None,
        unused_only: bool = False
    ) -> List[Dict]:
        """
        Get training examples for DSPy

        Args:
            signature_type: Filter by signature type (EntityExtractor, ProductConfirmer, etc.)
            unused_only: Only return examples not yet used in training

        Returns:
            List of training examples
        """
        try:
            training_data = self._read_json(self.training_data_file)

            # Filter by signature type
            if signature_type:
                training_data = [
                    ex for ex in training_data
                    if ex.get('signature_type') == signature_type
                ]

            # Filter by usage
            if unused_only:
                training_data = [
                    ex for ex in training_data
                    if not ex.get('used_in_training', False)
                ]

            return training_data

        except Exception as e:
            logger.error(f"Error getting training examples: {e}")
            return []

    def mark_training_examples_used(self, training_ids: List[str]) -> bool:
        """
        Mark training examples as used

        Args:
            training_ids: List of training IDs

        Returns:
            True if marked successfully
        """
        try:
            training_data = self._read_json(self.training_data_file)

            # Mark examples as used
            for example in training_data:
                if example.get('training_id') in training_ids:
                    example['used_in_training'] = True
                    example['used_timestamp'] = datetime.now().isoformat()

            self._write_json(self.training_data_file, training_data)

            # Update stats
            self._update_stats('training_examples_used', len(training_ids))

            logger.info(f"Marked {len(training_ids)} training examples as used")
            return True

        except Exception as e:
            logger.error(f"Error marking training examples as used: {e}")
            return False

    def get_feedback_stats(self) -> Dict:
        """
        Get feedback statistics

        Returns:
            Statistics dictionary
        """
        try:
            stats = self._read_json(self.stats_file)
            if not stats:
                stats = self._initialize_stats()
            return stats

        except Exception as e:
            logger.error(f"Error getting feedback stats: {e}")
            return {}

    def _update_order_feedback_count(self, order_id: str):
        """Update feedback count for an order"""
        try:
            order_results = self._read_json(self.order_results_file)

            for result in order_results:
                if result.get('order_id') == order_id:
                    result['feedback_received'] = True
                    result['feedback_count'] = result.get('feedback_count', 0) + 1
                    break

            self._write_json(self.order_results_file, order_results)

        except Exception as e:
            logger.error(f"Error updating order feedback count: {e}")

    def _mark_feedback_training_ready(self, feedback_id: str):
        """Mark feedback as ready for training"""
        try:
            feedback_list = self._read_json(self.feedback_file)

            for feedback in feedback_list:
                if feedback.get('feedback_id') == feedback_id:
                    feedback['dspy_training_ready'] = True
                    break

            self._write_json(self.feedback_file, feedback_list)

        except Exception as e:
            logger.error(f"Error marking feedback as training ready: {e}")

    def _update_stats(self, stat_name: str, increment: int = 1):
        """Update statistics"""
        try:
            stats = self._read_json(self.stats_file)
            if not stats:
                stats = self._initialize_stats()

            stats[stat_name] = stats.get(stat_name, 0) + increment
            stats['last_updated'] = datetime.now().isoformat()

            self._write_json(self.stats_file, stats)

        except Exception as e:
            logger.error(f"Error updating stats: {e}")

    def _initialize_stats(self) -> Dict:
        """Initialize statistics"""
        return {
            'feedback_received': 0,
            'training_examples_generated': 0,
            'training_examples_used': 0,
            'last_updated': datetime.now().isoformat()
        }

    def _read_json(self, file_path: Path) -> List[Dict]:
        """Read JSON file"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []

    def _write_json(self, file_path: Path, data: List[Dict]):
        """Write JSON file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error writing {file_path}: {e}")
            raise
