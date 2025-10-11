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

            # Step 9: Immediate retraining and validation (if enabled)
            if correction_type not in ['confirm', 'reject'] and training_example:
                retrain_enabled = self._should_immediate_retrain()

                if retrain_enabled:
                    logger.info("🔥 Starting immediate retraining and validation...")
                    validation_result = self._retrain_and_validate(
                        order_id=order_id,
                        training_example=training_example,
                        original_result=original_result
                    )

                    if validation_result:
                        # Send validation report to user
                        self._send_validation_report(order_id, validation_result)

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

    def _should_immediate_retrain(self) -> bool:
        """
        Check if immediate retraining is enabled

        Returns:
            True if immediate retraining should happen
        """
        import os
        return os.getenv('FEEDBACK_IMMEDIATE_RETRAIN', 'false').lower() == 'true'

    def _retrain_and_validate(
        self,
        order_id: str,
        training_example: Dict,
        original_result: Dict
    ) -> Optional[Dict]:
        """
        Retrain DSPy model with feedback and validate on same email

        Args:
            order_id: Order ID
            training_example: Training example from feedback
            original_result: Original processing result

        Returns:
            Validation result dict or None
        """
        try:
            from orchestrator.dspy_entity_extractor import DSPyEntityExtractor
            from orchestrator.dspy_config import setup_dspy
            import dspy

            logger.info("  [1/3] Retraining DSPy model with feedback...")

            # Get the extractor (TODO: Make this more modular)
            setup_dspy()
            extractor = DSPyEntityExtractor()

            # Create training example in DSPy format
            # Format: (input, expected_output)
            email_text = original_result.get('email', {}).get('body', '')

            # Convert correction to expected output format
            correction_type = training_example.get('correction_type')
            expected_output = self._build_expected_output(
                original_result.get('result', {}),
                training_example
            )

            # Create DSPy training example
            trainset = [
                dspy.Example(
                    email_text=email_text,
                    **expected_output
                ).with_inputs('email_text')
            ]

            # Compile with the new example (BootstrapFewShot)
            from dspy.teleprompt import BootstrapFewShot

            optimizer = BootstrapFewShot(metric=lambda x, y: 1.0, max_bootstrapped_demos=1)
            compiled_extractor = optimizer.compile(extractor.extractor, trainset=trainset)

            # Update the extractor's model
            extractor.extractor = compiled_extractor

            logger.info("  [2/3] Re-processing original email with updated model...")

            # Re-extract with updated model
            new_result = extractor.extract_complete(email_text)

            logger.info("  [3/3] Comparing results...")

            # Compare old vs new
            validation = {
                'order_id': order_id,
                'retrained': True,
                'correction_type': correction_type,
                'old_extraction': self._get_relevant_field(
                    original_result.get('result', {}),
                    correction_type
                ),
                'new_extraction': self._get_relevant_field(new_result, correction_type),
                'expected': self._get_relevant_field(expected_output, correction_type),
                'improved': False
            }

            # Check if extraction improved
            if correction_type == 'company_match':
                validation['improved'] = (
                    validation['new_extraction'].get('company_name', '').lower()
                    == validation['expected'].get('company_name', '').lower()
                )
            elif correction_type == 'product_match':
                # Check if product code matches
                validation['improved'] = self._check_product_improvement(
                    validation['old_extraction'],
                    validation['new_extraction'],
                    validation['expected']
                )

            logger.info(f"  ✅ Validation complete: {'IMPROVED' if validation['improved'] else 'NOT IMPROVED'}")

            return validation

        except Exception as e:
            logger.error(f"Error in retrain and validate: {e}", exc_info=True)
            return None

    def _build_expected_output(self, original: Dict, training_example: Dict) -> Dict:
        """Build expected output from training example"""
        correction_type = training_example.get('correction_type')
        corrections = training_example.get('corrections', {})

        # Start with original entities
        expected = original.get('entities', {}).copy()

        if correction_type == 'company_match':
            expected['company_name'] = corrections.get('correct_company_name', '')
        elif correction_type == 'product_match':
            # Update specific product
            product_idx = corrections.get('product_index', 0) - 1
            if 'product_codes' in expected and product_idx < len(expected['product_codes']):
                if corrections.get('correct_product_code'):
                    expected['product_codes'][product_idx] = corrections['correct_product_code']
                if corrections.get('correct_product_name'):
                    expected['product_names'][product_idx] = corrections['correct_product_name']

        return expected

    def _get_relevant_field(self, result: Dict, correction_type: str) -> Dict:
        """Extract relevant field based on correction type"""
        entities = result.get('entities', {})

        if correction_type == 'company_match':
            return {
                'company_name': entities.get('company_name', ''),
                'customer_name': entities.get('customer_name', '')
            }
        elif correction_type == 'product_match':
            return {
                'product_names': entities.get('product_names', []),
                'product_codes': entities.get('product_codes', [])
            }
        return {}

    def _check_product_improvement(self, old: Dict, new: Dict, expected: Dict) -> bool:
        """Check if product extraction improved"""
        old_codes = old.get('product_codes', [])
        new_codes = new.get('product_codes', [])
        expected_codes = expected.get('product_codes', [])

        # Simple check: did new extraction get closer to expected?
        old_matches = sum(1 for o, e in zip(old_codes, expected_codes) if o == e)
        new_matches = sum(1 for n, e in zip(new_codes, expected_codes) if n == e)

        return new_matches > old_matches

    def _send_validation_report(self, order_id: str, validation: Dict):
        """Send validation report to Telegram"""
        try:
            correction_type = validation['correction_type']
            improved = validation['improved']

            icon = "✅" if improved else "⚠️"
            status = "LEARNED SUCCESSFULLY" if improved else "NEEDS MORE TRAINING"

            message = f"""🔬 **TRAINING VALIDATION** (Order #{order_id})
{icon} Status: {status}

📝 What was corrected: {correction_type.replace('_', ' ').title()}

**Before Training:**
{self._format_field(validation['old_extraction'])}

**After Training:**
{self._format_field(validation['new_extraction'])}

**Expected:**
{self._format_field(validation['expected'])}

{'✅ The model learned your correction!' if improved else '⚠️ Model needs more examples like this.'}
"""

            self.notifier.send_message(message)
            logger.info(f"Sent validation report for {order_id}")

        except Exception as e:
            logger.error(f"Error sending validation report: {e}")

    def _format_field(self, data: Dict) -> str:
        """Format field data for display"""
        if 'company_name' in data:
            return f"  Company: {data.get('company_name', 'N/A')}"
        elif 'product_codes' in data:
            codes = data.get('product_codes', [])
            return f"  Products: {', '.join(codes[:3])}..."
        return f"  {data}"
