"""
DSPy Intent Classifier

Replaces manual prompt engineering for intent classification with
DSPy's declarative approach using ChainOfThought module.
"""

import logging
from typing import Dict, Optional
import dspy
from orchestrator.dspy_signatures import ClassifyEmailIntent, dspy_result_to_legacy_format

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    DSPy-based email intent classifier.

    This replaces the manual prompt-based classification in mistral_agent.py
    with a structured, optimizable DSPy module.
    """

    def __init__(self, use_chain_of_thought: bool = True):
        """
        Initialize intent classifier

        Args:
            use_chain_of_thought: If True, use ChainOfThought module for reasoning
                                 If False, use simple Predict module
        """
        # ChainOfThought generates reasoning steps before output
        # This typically improves accuracy for classification tasks
        if use_chain_of_thought:
            self.classifier = dspy.ChainOfThought(ClassifyEmailIntent)
            logger.info("Intent classifier initialized with ChainOfThought")
        else:
            self.classifier = dspy.Predict(ClassifyEmailIntent)
            logger.info("Intent classifier initialized with Predict")

    def classify(self, subject: str, body: str) -> Dict:
        """
        Classify email intent using DSPy

        Args:
            subject: Email subject line
            body: Email body text (including extracted attachments)

        Returns:
            Dictionary with intent classification results in legacy format:
            {
                'type': str,        # Primary intent type
                'sub_type': str,    # Sub-category
                'confidence': float, # 0.0 to 1.0
                'urgency': str,     # high, medium, low
                'reasoning': str    # Explanation
                'tokens_used': int  # Token count
            }
        """
        try:
            logger.debug(f"Classifying intent for email with subject: '{subject[:50]}...'")

            # Estimate tokens (rough approximation: 1 token ≈ 4 chars)
            input_text = f"{subject} {body}"
            estimated_input_tokens = len(input_text) // 4

            # Call DSPy module
            result = self.classifier(
                subject=subject,
                body=body
            )

            # Convert to legacy format for backward compatibility
            intent = dspy_result_to_legacy_format(result, 'intent')

            # Add estimated token usage (rough estimate)
            estimated_output_tokens = len(str(result)) // 4
            intent['tokens_used'] = estimated_input_tokens + estimated_output_tokens

            logger.info(f"Intent classified: {intent['type']} "
                       f"(confidence: {intent['confidence']:.2f}, urgency: {intent['urgency']})")
            logger.debug(f"Reasoning: {intent['reasoning']}")
            logger.debug(f"Estimated tokens: ~{intent['tokens_used']}")

            return intent

        except Exception as e:
            logger.error(f"Error in intent classification: {e}", exc_info=True)
            # Return fallback result
            return {
                'type': 'general',
                'sub_type': 'unknown',
                'confidence': 0.0,
                'urgency': 'medium',
                'reasoning': f'Classification failed: {str(e)}'
            }

    def classify_batch(self, emails: list[Dict[str, str]]) -> list[Dict]:
        """
        Classify multiple emails in batch

        Args:
            emails: List of dicts with 'subject' and 'body' keys

        Returns:
            List of intent dictionaries
        """
        results = []
        for email in emails:
            result = self.classify(
                subject=email.get('subject', ''),
                body=email.get('body', '')
            )
            results.append(result)

        return results


class OptimizedIntentClassifier(IntentClassifier):
    """
    Optimized intent classifier using DSPy's optimization capabilities.

    This version can be optimized using labeled training data to
    automatically generate better prompts and few-shot examples.
    """

    def __init__(self):
        super().__init__(use_chain_of_thought=True)
        self.is_optimized = False

    def optimize(
        self,
        training_examples: list[dspy.Example],
        validation_examples: Optional[list[dspy.Example]] = None,
        metric_threshold: float = 0.8
    ):
        """
        Optimize the classifier using labeled examples.

        This uses DSPy's BootstrapFewShot optimizer to automatically:
        1. Select good few-shot examples
        2. Optimize the prompt structure
        3. Improve classification accuracy

        Args:
            training_examples: List of dspy.Example with labeled intents
            validation_examples: Optional validation set
            metric_threshold: Minimum accuracy threshold

        Example:
            >>> examples = [
            ...     dspy.Example(
            ...         subject="Order #123",
            ...         body="I want to order 10 units",
            ...         intent_type="order_inquiry"
            ...     ).with_inputs("subject", "body")
            ... ]
            >>> classifier.optimize(examples)
        """
        try:
            logger.info(f"Optimizing intent classifier with {len(training_examples)} examples...")

            # Define accuracy metric
            def intent_accuracy(example, pred, trace=None):
                """Check if predicted intent matches expected intent"""
                return example.intent_type.lower() == pred.intent_type.lower()

            # Use BootstrapFewShot optimizer
            optimizer = dspy.BootstrapFewShot(
                metric=intent_accuracy,
                max_bootstrapped_demos=4,  # Number of few-shot examples
                max_labeled_demos=8  # Max examples to try
            )

            # Compile (optimize) the module
            self.classifier = optimizer.compile(
                self.classifier,
                trainset=training_examples
            )

            self.is_optimized = True
            logger.info("Intent classifier optimization complete")

            # Evaluate on validation set if provided
            if validation_examples:
                accuracy = self._evaluate(validation_examples, intent_accuracy)
                logger.info(f"Validation accuracy: {accuracy:.2%}")

        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)
            raise

    def _evaluate(self, examples: list[dspy.Example], metric) -> float:
        """
        Evaluate classifier on a set of examples

        Args:
            examples: List of labeled examples
            metric: Metric function to use

        Returns:
            Accuracy score (0.0 to 1.0)
        """
        correct = 0
        total = len(examples)

        for example in examples:
            pred = self.classifier(
                subject=example.subject,
                body=example.body
            )
            if metric(example, pred):
                correct += 1

        return correct / total if total > 0 else 0.0

    def save_optimized(self, path: str = "dspy_data/optimized_prompts/intent_classifier.json"):
        """
        Save the optimized classifier configuration

        Args:
            path: Path to save the optimized module
        """
        if not self.is_optimized:
            logger.warning("Classifier has not been optimized yet")
            return

        try:
            import os
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.classifier.save(path)
            logger.info(f"Optimized classifier saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save classifier: {e}")

    def load_optimized(self, path: str = "dspy_data/optimized_prompts/intent_classifier.json"):
        """
        Load a previously optimized classifier

        Args:
            path: Path to the saved optimized module
        """
        try:
            self.classifier.load(path)
            self.is_optimized = True
            logger.info(f"Loaded optimized classifier from {path}")
        except Exception as e:
            logger.error(f"Failed to load classifier: {e}")
            raise
