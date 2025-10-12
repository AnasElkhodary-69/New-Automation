"""
DSPy Customer Matcher

Uses DSPy to intelligently match extracted customer names to Odoo database customers.
This allows training to improve customer matching accuracy over time.
"""

import logging
import json
from typing import Dict, List, Optional
import dspy
from pathlib import Path
from orchestrator.dspy_signatures import MatchCustomerToDatabase

logger = logging.getLogger(__name__)


class CustomerMatcher:
    """
    DSPy-based customer matcher for intelligent customer name matching.

    This replaces simple fuzzy text matching with AI-powered matching that:
    - Understands company name variations
    - Rejects false positives (e.g., similar but different companies)
    - Can be trained with user feedback to improve accuracy
    """

    def __init__(self, use_chain_of_thought: bool = True):
        """
        Initialize customer matcher

        Args:
            use_chain_of_thought: If True, use ChainOfThought for better reasoning
        """
        from pathlib import Path

        # Initialize DSPy matcher
        if use_chain_of_thought:
            self.matcher = dspy.ChainOfThought(MatchCustomerToDatabase)
        else:
            self.matcher = dspy.Predict(MatchCustomerToDatabase)

        # Try to load trained model if available
        trained_model_path = Path('trained_models/matchcustomertodatabase_trained.json')
        if trained_model_path.exists():
            try:
                self.matcher.load(str(trained_model_path))
                logger.info("✓ Loaded TRAINED customer matcher model")
            except Exception as e:
                logger.warning(f"Failed to load trained customer matcher: {e}")
                logger.info("Using default (untrained) customer matcher")
        else:
            logger.info("Using default (untrained) customer matcher")

    def match_customer(
        self,
        extracted_company: str,
        candidate_customers: List[Dict],
        min_confidence: float = 0.80
    ) -> Optional[Dict]:
        """
        Match extracted company name to candidate customers using DSPy

        Args:
            extracted_company: Company name extracted from email
            candidate_customers: List of candidate customers from Odoo (with 'name', 'id')
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            Matched customer dict with 'id', 'name', 'confidence', 'reasoning', or None
        """
        if not extracted_company or not candidate_customers:
            logger.warning("Missing extracted_company or candidates")
            return None

        try:
            # Format candidates as JSON for DSPy
            candidates_json = json.dumps([
                {'id': c.get('id'), 'name': c.get('name', '')}
                for c in candidate_customers
            ], indent=2)

            logger.debug(f"Matching '{extracted_company}' against {len(candidate_customers)} candidates")
            logger.debug(f"Candidates: {candidates_json[:200]}...")

            # Call DSPy matcher
            result = self.matcher(
                extracted_company=extracted_company,
                candidate_customers=candidates_json
            )

            # Parse result
            best_match_name = result.best_match_name.strip()
            confidence = float(result.match_confidence)
            reasoning = result.reasoning

            logger.info(f"   [DSPy Customer Match]")
            logger.info(f"      Best match: '{best_match_name}' ({confidence:.0%})")
            logger.info(f"      Reasoning: {reasoning[:100]}...")

            # Check if match meets confidence threshold
            if not best_match_name or confidence < min_confidence:
                logger.warning(f"   [REJECTED] Confidence {confidence:.0%} below threshold {min_confidence:.0%}")
                return None

            # Find the matched customer in candidates
            matched_customer = None
            for candidate in candidate_customers:
                if candidate.get('name', '').strip() == best_match_name:
                    matched_customer = candidate
                    break

            if not matched_customer:
                logger.warning(f"   [ERROR] DSPy returned '{best_match_name}' but not found in candidates")
                return None

            # Return matched customer with metadata
            return {
                'id': matched_customer.get('id'),
                'name': matched_customer.get('name'),
                'email': matched_customer.get('email', ''),
                'phone': matched_customer.get('phone', ''),
                'confidence': confidence,
                'reasoning': reasoning,
                'match_method': 'dspy_ai'
            }

        except Exception as e:
            logger.error(f"Error in DSPy customer matching: {e}", exc_info=True)
            return None

    def save_trained_model(self, path: str = "trained_models/matchcustomertodatabase_trained.json"):
        """Save trained matcher model"""
        try:
            import os
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.matcher.save(path)
            logger.info(f"Saved trained customer matcher to {path}")
        except Exception as e:
            logger.error(f"Failed to save customer matcher: {e}")

    def load_trained_model(self, path: str = "trained_models/matchcustomertodatabase_trained.json"):
        """Load trained matcher model"""
        try:
            self.matcher.load(path)
            logger.info(f"Loaded trained customer matcher from {path}")
        except Exception as e:
            logger.error(f"Failed to load customer matcher: {e}")
            raise


# Example training function (to be called from train_from_feedback.py)
def train_customer_matcher(training_examples: List, save_path: str = "trained_models/matchcustomertodatabase_trained.json"):
    """
    Train customer matcher with feedback examples

    Args:
        training_examples: List of dspy.Example with inputs/outputs
        save_path: Where to save trained model

    Example:
        >>> examples = [
        ...     dspy.Example(
        ...         extracted_company="COVERIS Flexibles Deutschland GmbH",
        ...         candidate_customers='[{"id": 123, "name": "COVERIS Flexibles Deutschland GmbH"}, {"id": 456, "name": "Amcor Flexibles Kreuzlingen GmbH"}]',
        ...         best_match_name="COVERIS Flexibles Deutschland GmbH",
        ...         match_confidence=1.0,
        ...         reasoning="Exact match on all key terms"
        ...     ).with_inputs("extracted_company", "candidate_customers")
        ... ]
        >>> train_customer_matcher(examples)
    """
    logger.info(f"Training customer matcher with {len(training_examples)} examples...")

    # Define metric
    def customer_match_accuracy(example, pred, trace=None):
        """Check if predicted match is correct"""
        expected = example.best_match_name.strip().lower()
        actual = pred.best_match_name.strip().lower()
        return expected == actual

    # Initialize matcher
    matcher = CustomerMatcher(use_chain_of_thought=True)

    # Use BootstrapFewShot optimizer
    optimizer = dspy.BootstrapFewShot(
        metric=customer_match_accuracy,
        max_bootstrapped_demos=4,
        max_labeled_demos=8
    )

    # Compile (optimize) the module
    compiled_matcher = optimizer.compile(
        matcher.matcher,
        trainset=training_examples
    )

    # Update matcher with trained version
    matcher.matcher = compiled_matcher

    # Save trained model
    matcher.save_trained_model(save_path)

    logger.info("Customer matcher training complete!")
    return matcher
