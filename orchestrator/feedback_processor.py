"""
Feedback Processor
Orchestrates the feedback processing workflow:
1. Parse user feedback with Mistral
2. Store feedback
3. Generate training data
4. Send confirmations
"""

import logging
from typing import Dict, Optional
from utils.feedback_storage import FeedbackStorage
from utils.telegram_notifier import TelegramNotifier
from orchestrator.mistral_feedback_parser import MistralFeedbackParser
from orchestrator.dspy_training_generator import DSPyTrainingGenerator

logger = logging.getLogger(__name__)


class FeedbackProcessor:
    """Orchestrate feedback processing workflow"""

    def __init__(
        self,
        feedback_parser: MistralFeedbackParser,
        training_generator: DSPyTrainingGenerator,
        feedback_storage: FeedbackStorage,
        telegram_notifier: TelegramNotifier
    ):
        """
        Initialize feedback processor

        Args:
            feedback_parser: Mistral feedback parser
            training_generator: DSPy training generator
            feedback_storage: Feedback storage
            telegram_notifier: Telegram notifier
        """
        self.parser = feedback_parser
        self.generator = training_generator
        self.storage = feedback_storage
        self.notifier = telegram_notifier

        logger.info("Feedback processor initialized")

    def process_feedback(
        self,
        order_id: str,
        user_message: str,
        telegram_user_id: Optional[int] = None
    ) -> bool:
        """
        Main entry point for processing user feedback

        Args:
            order_id: Order identifier
            user_message: Raw user message from Telegram
            telegram_user_id: Telegram user ID

        Returns:
            True if processed successfully
        """
        try:
            logger.info(f"Processing feedback for order {order_id}")

            # Step 1: Get original order result
            original_result = self.storage.get_order_result(order_id)

            if not original_result:
                logger.error(f"Order {order_id} not found in storage")
                self.notifier.send_error(
                    order_id,
                    f"Order {order_id} not found. Please check the order ID."
                )
                return False

            # Step 2: Parse feedback with Mistral
            logger.info("Parsing feedback with Mistral...")
            parsed_feedback = self.parser.parse_feedback(
                order_id=order_id,
                user_message=user_message,
                original_result=original_result.get('result', {})
            )

            # Step 3: Check if clarification is needed
            if parsed_feedback.get('needs_clarification'):
                logger.info("Clarification needed, asking user...")
                question = parsed_feedback.get('clarification_question')
                self.notifier.send_clarification(order_id, question)
                return True  # Waiting for user response

            # Step 4: Validate parsed feedback
            validation = self.parser.validate_correction(parsed_feedback)

            if not validation['valid']:
                logger.error(f"Invalid feedback: {validation['errors']}")
                error_msg = "I couldn't understand your correction:\n" + "\n".join(validation['errors'])
                self.notifier.send_error(order_id, error_msg)
                return False

            # Show warnings if any
            if validation['warnings']:
                logger.warning(f"Feedback warnings: {validation['warnings']}")

            # Step 5: Store feedback
            logger.info("Storing feedback...")
            feedback_id = self.storage.store_feedback(
                order_id=order_id,
                user_message=user_message,
                mistral_parsing=parsed_feedback,
                telegram_user_id=telegram_user_id
            )

            if not feedback_id:
                logger.error("Failed to store feedback")
                return False

            # Step 6: Send confirmation to user
            logger.info("Sending confirmation to user...")
            self.notifier.send_confirmation(order_id, parsed_feedback)

            # Step 7: Generate training data
            correction_type = parsed_feedback.get('correction_type')

            if correction_type not in ['confirm', 'reject']:
                # Only generate training data for actual corrections
                logger.info("Generating DSPy training data...")
                training_example = self.generator.generate_training_example(
                    email_text=original_result.get('email', {}).get('body', ''),
                    system_output=original_result.get('result', {}),
                    user_correction=parsed_feedback
                )

                if training_example:
                    # Store training example
                    self.storage.store_training_example(feedback_id, training_example)
                    logger.info(f"Training example stored for feedback {feedback_id}")
                else:
                    logger.warning("Failed to generate training example")

            # Step 8: Log success
            logger.info(f"Successfully processed feedback for order {order_id}")

            # Step 9: Check if we should trigger retraining
            if self._should_retrain():
                logger.info("Retraining threshold reached - consider running training")
                # TODO: Implement auto-retraining or send notification

            return True

        except Exception as e:
            logger.error(f"Error processing feedback: {e}", exc_info=True)
            try:
                self.notifier.send_error(
                    order_id,
                    f"An error occurred while processing your feedback: {str(e)}"
                )
            except:
                pass
            return False

    def process_batch_feedback(self, feedback_items: list[Dict]) -> Dict:
        """
        Process multiple feedback items in batch

        Args:
            feedback_items: List of {order_id, user_message, telegram_user_id}

        Returns:
            Processing statistics
        """
        stats = {
            'total': len(feedback_items),
            'success': 0,
            'failed': 0,
            'clarification_needed': 0
        }

        for item in feedback_items:
            try:
                success = self.process_feedback(
                    order_id=item['order_id'],
                    user_message=item['user_message'],
                    telegram_user_id=item.get('telegram_user_id')
                )

                if success:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1

            except Exception as e:
                logger.error(f"Error processing feedback item: {e}")
                stats['failed'] += 1

        logger.info(f"Batch processing complete: {stats}")
        return stats

    def get_feedback_summary(self, order_id: str) -> Optional[Dict]:
        """
        Get summary of all feedback for an order

        Args:
            order_id: Order identifier

        Returns:
            Feedback summary or None
        """
        try:
            # Get all feedback for this order
            all_feedback = self.storage._read_json(self.storage.feedback_file)
            order_feedback = [
                fb for fb in all_feedback
                if fb.get('order_id') == order_id
            ]

            if not order_feedback:
                return None

            summary = {
                'order_id': order_id,
                'feedback_count': len(order_feedback),
                'correction_types': {},
                'training_examples_generated': 0,
                'latest_feedback': None
            }

            for fb in order_feedback:
                # Count by correction type
                corr_type = fb.get('mistral_parsing', {}).get('correction_type', 'unknown')
                summary['correction_types'][corr_type] = summary['correction_types'].get(corr_type, 0) + 1

                # Count training examples
                if fb.get('dspy_training_ready'):
                    summary['training_examples_generated'] += 1

            # Get latest feedback
            if order_feedback:
                summary['latest_feedback'] = order_feedback[-1]

            return summary

        except Exception as e:
            logger.error(f"Error getting feedback summary: {e}")
            return None

    def _should_retrain(self) -> bool:
        """
        Check if we should trigger DSPy retraining

        Returns:
            True if retraining threshold reached
        """
        try:
            import os

            # Check if auto-retraining is enabled
            auto_retrain = os.getenv('FEEDBACK_ENABLE_AUTO_TRAINING', 'false').lower() == 'true'
            if not auto_retrain:
                return False

            # Get threshold from env
            threshold = int(os.getenv('DSPY_AUTO_RETRAIN_THRESHOLD', '10'))

            # Count unused training examples
            training_examples = self.storage.get_training_examples(unused_only=True)

            return len(training_examples) >= threshold

        except Exception as e:
            logger.error(f"Error checking retrain threshold: {e}")
            return False

    def export_training_data(self, output_file: str, signature_type: Optional[str] = None) -> bool:
        """
        Export training data to file

        Args:
            output_file: Output file path
            signature_type: Filter by signature type

        Returns:
            True if export successful
        """
        try:
            training_examples = self.storage.get_training_examples(
                signature_type=signature_type,
                unused_only=False
            )

            return self.generator.export_training_data(training_examples, output_file)

        except Exception as e:
            logger.error(f"Error exporting training data: {e}")
            return False

    def get_training_statistics(self) -> Dict:
        """
        Get statistics about training data

        Returns:
            Statistics dictionary
        """
        try:
            # Get all training examples
            training_examples = self.storage.get_training_examples()

            # Get statistics from generator
            stats = self.generator.get_training_statistics(training_examples)

            # Add storage statistics
            feedback_stats = self.storage.get_feedback_stats()
            stats['feedback_stats'] = feedback_stats

            return stats

        except Exception as e:
            logger.error(f"Error getting training statistics: {e}")
            return {}
