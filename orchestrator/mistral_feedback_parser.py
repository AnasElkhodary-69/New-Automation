"""
Mistral Feedback Parser
Uses DSPy and Mistral to parse natural language feedback from Telegram users
"""

import json
import logging
import dspy
from typing import Dict, Optional, List
from orchestrator.dspy_feedback_signatures import MultiFeedbackParser

logger = logging.getLogger(__name__)


class MistralFeedbackParser:
    """Parse user feedback using Mistral AI via DSPy - supports MULTIPLE corrections per message"""

    def __init__(self, use_chain_of_thought: bool = True):
        """
        Initialize feedback parser

        Args:
            use_chain_of_thought: Use CoT for better reasoning
        """
        self.use_chain_of_thought = use_chain_of_thought

        # Initialize DSPy predictor with MultiFeedbackParser
        if use_chain_of_thought:
            self.parser = dspy.ChainOfThought(MultiFeedbackParser)
            logger.info("Multi-correction feedback parser initialized with Chain-of-Thought")
        else:
            self.parser = dspy.Predict(MultiFeedbackParser)
            logger.info("Multi-correction feedback parser initialized (basic mode)")

    def parse_feedback(
        self,
        order_id: str,
        user_message: str,
        original_result: Dict
    ) -> Dict:
        """
        Parse user feedback into structured corrections (supports MULTIPLE corrections)

        Args:
            order_id: Order identifier
            user_message: Raw user message from Telegram
            original_result: Original processing result

        Returns:
            Parsed feedback with list of corrections:
            {
                'corrections_list': [
                    {'correction_type': '...', 'corrections': {...}, 'confidence': 0.9, ...},
                    ...
                ],
                'overall_confidence': 0.92,
                'needs_clarification': False,
                'clarification_question': None
            }
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

            # Parse corrections_list (array of corrections)
            try:
                corrections_list = json.loads(prediction.corrections_list)
                if not isinstance(corrections_list, list):
                    corrections_list = [corrections_list]  # Wrap if single object
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse corrections_list JSON: {prediction.corrections_list}")
                corrections_list = []

            # Parse other outputs
            overall_confidence = self._parse_float_output(prediction.overall_confidence)
            needs_clarification = self._parse_bool_output(prediction.needs_clarification)

            # Build result
            result = {
                'corrections_list': corrections_list,
                'overall_confidence': overall_confidence,
                'needs_clarification': needs_clarification,
                'clarification_question': prediction.clarification_question if needs_clarification else None,
                'total_corrections': len(corrections_list)
            }

            # Log result
            logger.info(f"Feedback parsed: {len(corrections_list)} correction(s), "
                       f"confidence={overall_confidence:.2f}, needs_clarification={needs_clarification}")

            for idx, correction in enumerate(corrections_list, 1):
                logger.info(f"  [{idx}] type={correction.get('correction_type')}, "
                           f"confidence={correction.get('confidence', 0):.2f}")

            if needs_clarification:
                logger.info(f"Clarification needed: {prediction.clarification_question}")

            return result

        except Exception as e:
            logger.error(f"Error parsing feedback: {e}", exc_info=True)
            # Return fallback result
            return {
                'corrections_list': [],
                'overall_confidence': 0.0,
                'needs_clarification': True,
                'clarification_question': 'I had trouble understanding your message. Could you please rephrase?',
                'total_corrections': 0
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
        Validate parsed feedback before applying (supports multiple corrections)

        Args:
            parsed_feedback: Parsed feedback from parse_feedback() with corrections_list

        Returns:
            Validation result with warnings/errors
        """
        validation = {
            'valid': True,
            'warnings': [],
            'errors': []
        }

        corrections_list = parsed_feedback.get('corrections_list', [])
        overall_confidence = parsed_feedback.get('overall_confidence', 0)

        # Check overall confidence threshold
        if overall_confidence < 0.5:
            validation['warnings'].append(f"Low overall confidence ({overall_confidence:.0%}), suggest clarification")

        # Validate each correction
        for idx, correction in enumerate(corrections_list, 1):
            correction_type = correction.get('correction_type')
            corrections_data = correction.get('corrections', {})
            confidence = correction.get('confidence', 0)

            # Check individual confidence
            if confidence < 0.5:
                validation['warnings'].append(f"Correction {idx} has low confidence ({confidence:.0%})")

            # Validate correction structure based on type
            if correction_type == 'product_match':
                if 'product_index' not in corrections_data:
                    validation['errors'].append(f"Correction {idx}: Missing product_index in product correction")
                    validation['valid'] = False

                if not corrections_data.get('correct_product_code') and not corrections_data.get('correct_product_name'):
                    validation['errors'].append(f"Correction {idx}: Must specify product code or name")
                    validation['valid'] = False

            elif correction_type == 'company_match':
                if not corrections_data.get('correct_company_name'):
                    validation['errors'].append(f"Correction {idx}: Missing company name in company correction")
                    validation['valid'] = False

            elif correction_type == 'quantity':
                if 'product_index' not in corrections_data:
                    validation['errors'].append(f"Correction {idx}: Missing product_index in quantity correction")
                    validation['valid'] = False

                if 'correct_quantity' not in corrections_data:
                    validation['errors'].append(f"Correction {idx}: Missing correct_quantity value")
                    validation['valid'] = False

        # Check if no corrections found
        if not corrections_list:
            validation['warnings'].append("No corrections found in message")

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
