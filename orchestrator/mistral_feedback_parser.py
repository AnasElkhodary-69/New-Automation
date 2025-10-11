"""
Mistral Feedback Parser
Uses DSPy and Mistral to parse natural language feedback from Telegram users
"""

import json
import logging
import dspy
from typing import Dict, Optional
from orchestrator.dspy_feedback_signatures import FeedbackParser

logger = logging.getLogger(__name__)


class MistralFeedbackParser:
    """Parse user feedback using Mistral AI via DSPy"""

    def __init__(self, use_chain_of_thought: bool = True):
        """
        Initialize feedback parser

        Args:
            use_chain_of_thought: Use CoT for better reasoning
        """
        self.use_chain_of_thought = use_chain_of_thought

        # Initialize DSPy predictor
        if use_chain_of_thought:
            self.parser = dspy.ChainOfThought(FeedbackParser)
            logger.info("Feedback parser initialized with Chain-of-Thought")
        else:
            self.parser = dspy.Predict(FeedbackParser)
            logger.info("Feedback parser initialized (basic mode)")

    def parse_feedback(
        self,
        order_id: str,
        user_message: str,
        original_result: Dict
    ) -> Dict:
        """
        Parse user feedback into structured corrections

        Args:
            order_id: Order identifier
            user_message: Raw user message from Telegram
            original_result: Original processing result

        Returns:
            Parsed feedback with corrections
        """
        try:
            logger.info(f"Parsing feedback for order {order_id}: '{user_message[:50]}...'")

            # Convert original result to JSON string for DSPy
            original_result_str = json.dumps(original_result, ensure_ascii=False)

            # Run DSPy prediction
            prediction = self.parser(
                original_result=original_result_str,
                user_message=user_message,
                order_id=order_id
            )

            # Parse outputs
            correction_type = prediction.correction_type.strip()
            affected_items = self._parse_list_output(prediction.affected_items)
            confidence = self._parse_float_output(prediction.confidence)
            needs_clarification = self._parse_bool_output(prediction.needs_clarification)

            # Parse corrections JSON
            try:
                corrections = json.loads(prediction.corrections)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse corrections JSON, using raw: {prediction.corrections}")
                corrections = {'raw': prediction.corrections}

            # Build result
            result = {
                'correction_type': correction_type,
                'corrections': corrections,
                'affected_items': affected_items,
                'user_reasoning': prediction.user_reasoning,
                'confidence': confidence,
                'needs_clarification': needs_clarification,
                'clarification_question': prediction.clarification_question if needs_clarification else None
            }

            # Log result
            logger.info(f"Feedback parsed: type={correction_type}, confidence={confidence:.2f}, "
                       f"needs_clarification={needs_clarification}")

            if needs_clarification:
                logger.info(f"Clarification needed: {prediction.clarification_question}")

            return result

        except Exception as e:
            logger.error(f"Error parsing feedback: {e}", exc_info=True)
            # Return fallback result
            return {
                'correction_type': 'clarify',
                'corrections': {},
                'affected_items': [],
                'user_reasoning': 'Error parsing feedback',
                'confidence': 0.0,
                'needs_clarification': True,
                'clarification_question': 'I had trouble understanding your message. Could you please rephrase?'
            }

    def parse_batch_feedback(
        self,
        feedback_items: list[Dict]
    ) -> list[Dict]:
        """
        Parse multiple feedback items in batch

        Args:
            feedback_items: List of {order_id, user_message, original_result}

        Returns:
            List of parsed feedback
        """
        results = []
        for item in feedback_items:
            try:
                result = self.parse_feedback(
                    order_id=item['order_id'],
                    user_message=item['user_message'],
                    original_result=item['original_result']
                )
                results.append({
                    'order_id': item['order_id'],
                    'parsed': result
                })
            except Exception as e:
                logger.error(f"Error parsing feedback for {item['order_id']}: {e}")
                results.append({
                    'order_id': item['order_id'],
                    'error': str(e)
                })

        return results

    def validate_correction(self, parsed_feedback: Dict) -> Dict:
        """
        Validate parsed feedback before applying

        Args:
            parsed_feedback: Parsed feedback from parse_feedback()

        Returns:
            Validation result with warnings/errors
        """
        validation = {
            'valid': True,
            'warnings': [],
            'errors': []
        }

        correction_type = parsed_feedback.get('correction_type')
        corrections = parsed_feedback.get('corrections', {})
        confidence = parsed_feedback.get('confidence', 0)

        # Check confidence threshold
        if confidence < 0.5:
            validation['warnings'].append(f"Low confidence ({confidence:.0%}), suggest clarification")

        # Validate correction structure based on type
        if correction_type == 'product_match':
            if 'product_index' not in corrections:
                validation['errors'].append("Missing product_index in product correction")
                validation['valid'] = False

            if not corrections.get('correct_product_code') and not corrections.get('correct_product_name'):
                validation['errors'].append("Must specify product code or name")
                validation['valid'] = False

        elif correction_type == 'company_match':
            if not corrections.get('correct_company_name'):
                validation['errors'].append("Missing company name in company correction")
                validation['valid'] = False

        elif correction_type == 'quantity':
            if 'product_index' not in corrections:
                validation['errors'].append("Missing product_index in quantity correction")
                validation['valid'] = False

            if 'correct_quantity' not in corrections:
                validation['errors'].append("Missing correct_quantity value")
                validation['valid'] = False

        elif correction_type == 'clarify':
            if not parsed_feedback.get('needs_clarification'):
                validation['warnings'].append("Correction type is 'clarify' but needs_clarification is False")

        return validation

    def _parse_list_output(self, output: str) -> list:
        """Parse list output from DSPy"""
        try:
            # Try JSON parse first
            if output.startswith('['):
                return json.loads(output)

            # Try comma-separated
            if ',' in output:
                return [item.strip() for item in output.split(',')]

            # Single item
            if output.strip():
                return [output.strip()]

            return []

        except Exception as e:
            logger.debug(f"Error parsing list output: {e}")
            return []

    def _parse_float_output(self, output: str) -> float:
        """Parse float output from DSPy"""
        try:
            # Remove any non-numeric characters except . and -
            cleaned = ''.join(c for c in str(output) if c.isdigit() or c in '.-')
            value = float(cleaned)

            # Clamp to 0.0-1.0
            return max(0.0, min(1.0, value))

        except Exception as e:
            logger.debug(f"Error parsing float output: {e}")
            return 0.5  # Default medium confidence

    def _parse_bool_output(self, output: str) -> bool:
        """Parse boolean output from DSPy"""
        try:
            output_lower = str(output).lower().strip()
            return output_lower in ['true', 'yes', '1', 'True']
        except Exception as e:
            logger.debug(f"Error parsing bool output: {e}")
            return False
