"""
DSPy Training Data Generator
Converts user corrections into DSPy training examples
"""

import json
import logging
import dspy
from typing import Dict, Optional
from orchestrator.dspy_feedback_signatures import TrainingExampleGenerator

logger = logging.getLogger(__name__)


class DSPyTrainingGenerator:
    """Generate DSPy training examples from user corrections"""

    def __init__(self, use_chain_of_thought: bool = True):
        """
        Initialize training generator

        Args:
            use_chain_of_thought: Use CoT for better reasoning
        """
        self.use_chain_of_thought = use_chain_of_thought

        # Initialize DSPy predictor
        if use_chain_of_thought:
            self.generator = dspy.ChainOfThought(TrainingExampleGenerator)
            logger.info("Training generator initialized with Chain-of-Thought")
        else:
            self.generator = dspy.Predict(TrainingExampleGenerator)
            logger.info("Training generator initialized (basic mode)")

    def generate_training_example(
        self,
        email_text: str,
        system_output: Dict,
        user_correction: Dict
    ) -> Optional[Dict]:
        """
        Generate DSPy training example from user correction

        Args:
            email_text: Original email content
            system_output: What the system originally extracted
            user_correction: User's correction (parsed by MistralFeedbackParser)

        Returns:
            Training example or None if generation failed
        """
        try:
            logger.info(f"Generating training example for correction type: {user_correction.get('correction_type')}")

            # Convert dicts to JSON strings for DSPy
            system_output_str = json.dumps(system_output, ensure_ascii=False)
            user_correction_str = json.dumps(user_correction, ensure_ascii=False)

            # Run DSPy prediction
            prediction = self.generator(
                email_text=email_text,
                system_output=system_output_str,
                user_correction=user_correction_str
            )

            # Parse outputs
            dspy_signature = prediction.dspy_signature.strip()
            training_weight = self._parse_float_output(prediction.training_weight)
            training_priority = prediction.training_priority.strip()

            # Parse JSON outputs
            try:
                training_input = json.loads(prediction.training_input)
            except json.JSONDecodeError:
                logger.warning("Failed to parse training_input JSON")
                training_input = {'raw': prediction.training_input}

            try:
                correct_output = json.loads(prediction.correct_output)
            except json.JSONDecodeError:
                logger.warning("Failed to parse correct_output JSON")
                correct_output = {'raw': prediction.correct_output}

            try:
                incorrect_output = json.loads(prediction.incorrect_output)
            except json.JSONDecodeError:
                logger.warning("Failed to parse incorrect_output JSON")
                incorrect_output = {'raw': prediction.incorrect_output}

            # Build training example
            training_example = {
                'signature_type': dspy_signature,
                'training_data': {
                    'input': training_input,
                    'correct_output': correct_output,
                    'incorrect_output': incorrect_output
                },
                'error_analysis': prediction.error_analysis,
                'training_weight': training_weight,
                'training_priority': training_priority
            }

            logger.info(f"Training example generated: signature={dspy_signature}, "
                       f"weight={training_weight:.1f}, priority={training_priority}")

            return training_example

        except Exception as e:
            logger.error(f"Error generating training example: {e}", exc_info=True)
            return None

    def generate_batch_examples(
        self,
        feedback_items: list[Dict]
    ) -> list[Dict]:
        """
        Generate training examples for multiple feedback items

        Args:
            feedback_items: List of {email_text, system_output, user_correction}

        Returns:
            List of training examples
        """
        results = []

        for idx, item in enumerate(feedback_items, 1):
            try:
                logger.info(f"Processing feedback {idx}/{len(feedback_items)}")

                example = self.generate_training_example(
                    email_text=item['email_text'],
                    system_output=item['system_output'],
                    user_correction=item['user_correction']
                )

                if example:
                    results.append({
                        'success': True,
                        'feedback_id': item.get('feedback_id'),
                        'training_example': example
                    })
                else:
                    results.append({
                        'success': False,
                        'feedback_id': item.get('feedback_id'),
                        'error': 'Generation failed'
                    })

            except Exception as e:
                logger.error(f"Error processing feedback {idx}: {e}")
                results.append({
                    'success': False,
                    'feedback_id': item.get('feedback_id'),
                    'error': str(e)
                })

        success_count = sum(1 for r in results if r['success'])
        logger.info(f"Generated {success_count}/{len(feedback_items)} training examples")

        return results

    def create_dspy_training_set(
        self,
        training_examples: list[Dict],
        signature_type: Optional[str] = None
    ) -> list[dspy.Example]:
        """
        Convert training examples to DSPy Example format

        Args:
            training_examples: List of training examples from generate_training_example()
            signature_type: Filter by signature type (EntityExtractor, ProductConfirmer, etc.)

        Returns:
            List of dspy.Example objects ready for training
        """
        dspy_examples = []

        for example in training_examples:
            try:
                # Filter by signature type if specified
                if signature_type and example.get('signature_type') != signature_type:
                    continue

                training_data = example.get('training_data', {})
                input_data = training_data.get('input', {})
                correct_output = training_data.get('correct_output', {})

                # Create DSPy example
                # The exact format depends on the signature, but we'll create a generic one
                dspy_example = dspy.Example(
                    **input_data,
                    **correct_output
                ).with_inputs(*input_data.keys())

                dspy_examples.append(dspy_example)

            except Exception as e:
                logger.error(f"Error creating DSPy example: {e}")
                continue

        logger.info(f"Created {len(dspy_examples)} DSPy Example objects")
        return dspy_examples

    def export_training_data(
        self,
        training_examples: list[Dict],
        output_file: str
    ) -> bool:
        """
        Export training examples to JSON file

        Args:
            training_examples: List of training examples
            output_file: Output file path

        Returns:
            True if export successful
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(training_examples, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported {len(training_examples)} training examples to {output_file}")
            return True

        except Exception as e:
            logger.error(f"Error exporting training data: {e}")
            return False

    def get_training_statistics(self, training_examples: list[Dict]) -> Dict:
        """
        Get statistics about training examples

        Args:
            training_examples: List of training examples

        Returns:
            Statistics dictionary
        """
        stats = {
            'total_examples': len(training_examples),
            'by_signature': {},
            'by_priority': {},
            'average_weight': 0.0,
            'high_priority': 0,
            'error_types': {}
        }

        if not training_examples:
            return stats

        weights = []

        for example in training_examples:
            # Count by signature
            sig_type = example.get('signature_type', 'unknown')
            stats['by_signature'][sig_type] = stats['by_signature'].get(sig_type, 0) + 1

            # Count by priority
            priority = example.get('training_priority', 'unknown')
            stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1

            if priority == 'immediate':
                stats['high_priority'] += 1

            # Collect weights
            weight = example.get('training_weight', 1.0)
            weights.append(weight)

            # Extract error type from error analysis
            error_analysis = example.get('error_analysis', '')
            if 'company' in error_analysis.lower():
                stats['error_types']['company'] = stats['error_types'].get('company', 0) + 1
            if 'product' in error_analysis.lower():
                stats['error_types']['product'] = stats['error_types'].get('product', 0) + 1
            if 'quantity' in error_analysis.lower():
                stats['error_types']['quantity'] = stats['error_types'].get('quantity', 0) + 1

        # Calculate average weight
        if weights:
            stats['average_weight'] = sum(weights) / len(weights)

        return stats

    def _parse_float_output(self, output: str) -> float:
        """Parse float output from DSPy"""
        try:
            # Remove any non-numeric characters except . and -
            cleaned = ''.join(c for c in str(output) if c.isdigit() or c in '.-')
            value = float(cleaned)

            # Clamp to 1.0-10.0
            return max(1.0, min(10.0, value))

        except Exception as e:
            logger.debug(f"Error parsing float output: {e}")
            return 5.0  # Default medium weight
