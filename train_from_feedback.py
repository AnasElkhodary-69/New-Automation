"""
DSPy Model Training from User Feedback
Uses collected feedback to train and improve the email processing model
"""

import json
import logging
from pathlib import Path
from orchestrator.dspy_config import setup_dspy
import dspy
from orchestrator.dspy_signatures import ExtractOrderEntities, ConfirmAllProducts, ClassifyEmailIntent, MatchCustomerToDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_training_examples():
    """Load all training examples from feedback"""
    training_path = Path('feedback/training_examples.json')

    if not training_path.exists():
        logger.error("No training examples found!")
        return []

    with open(training_path, 'r', encoding='utf-8') as f:
        examples = json.load(f)

    logger.info(f"Loaded {len(examples)} training examples")
    return examples


def load_corrections():
    """Load corrections from Telegram feedback"""
    corrections_path = Path('feedback/corrections.json')

    if not corrections_path.exists():
        logger.warning("No corrections found")
        return []

    with open(corrections_path, 'r', encoding='utf-8') as f:
        corrections = json.load(f)

    logger.info(f"Loaded {len(corrections)} correction feedbacks")
    return corrections


def convert_to_dspy_examples(training_examples):
    """Convert training examples to DSPy Example format"""
    # Map training signature names to actual DSPy signature classes
    signature_mapping = {
        'EntityExtractor': 'ExtractOrderEntities',
        'ProductConfirmer': 'ConfirmAllProducts',
        'CompleteExtractor': 'ExtractOrderEntities'
    }

    dspy_examples_by_signature = {
        'ExtractOrderEntities': [],
        'ConfirmAllProducts': []
    }

    for item in training_examples:
        if item.get('used_in_training', False):
            logger.info(f"Skipping {item['training_id']} - already used")
            continue

        signature_type = item.get('signature_type')
        training_data = item.get('training_data', {})

        # Map to actual signature name
        actual_signature = signature_mapping.get(signature_type, signature_type)

        if signature_type == 'ProductConfirmer':
            # Convert ProductConfirmer training data -> ConfirmAllProducts
            input_data = training_data.get('input', {})
            correct_output = training_data.get('correct_output', {})

            example = dspy.Example(
                email_body=input_data.get('email_body', ''),
                product_candidates=json.dumps(input_data.get('product_candidates', []), ensure_ascii=False),
                matched_products=json.dumps(correct_output.get('matched_products', []), ensure_ascii=False)
            ).with_inputs('email_body', 'product_candidates')

            dspy_examples_by_signature['ConfirmAllProducts'].append(example)
            logger.info(f"Added ConfirmAllProducts example: {item['training_id']}")

        elif signature_type in ['CompleteExtractor', 'EntityExtractor']:
            # Convert CompleteExtractor/EntityExtractor training data -> ExtractOrderEntities
            input_data = training_data.get('input', {})
            correct_output = training_data.get('correct_output', {})

            # Build entities JSON
            entities = correct_output.get('entities', {})
            if isinstance(entities, str):
                entities_json = entities
            else:
                entities_json = json.dumps(entities, ensure_ascii=False)

            example = dspy.Example(
                email_subject=input_data.get('email_subject', ''),
                email_body=input_data.get('email_body', ''),
                entities=entities_json
            ).with_inputs('email_subject', 'email_body')

            dspy_examples_by_signature['ExtractOrderEntities'].append(example)
            logger.info(f"Added ExtractOrderEntities example: {item['training_id']}")

    return dspy_examples_by_signature


def extract_customer_matching_examples(corrections):
    """
    Extract customer matching training examples from corrections

    Focus on corrections where customer was matched incorrectly
    """
    examples = []

    for correction in corrections:
        # Skip if already applied
        if correction.get('applied_to_model', False):
            continue

        # Check if this is customer matching correction
        mistral_parsing = correction.get('mistral_parsing', {})
        corrections_list = mistral_parsing.get('corrections_list', [])

        for corr in corrections_list:
            if corr.get('correction_type') == 'company_match':
                # Get original extraction data
                original = correction.get('original_extraction', {})
                entities = original.get('entities', {})
                context = original.get('context', {})

                extracted_company = entities.get('company_name', '')
                wrong_match = context.get('customer_info', {})

                if not extracted_company or not wrong_match.get('name'):
                    continue

                # Build candidates list with the wrong match
                candidates = [{
                    "id": wrong_match.get('id'),
                    "name": wrong_match.get('name', '')
                }]

                candidates_json = json.dumps(candidates, indent=2)

                # The correct answer: reject the wrong company
                # User said "Company is not in database, shouldn't match randomly"
                example = dspy.Example(
                    extracted_company=extracted_company,
                    candidate_customers=candidates_json,
                    best_match_name="",  # Empty = reject all
                    match_confidence=0.0,
                    reasoning=f"Reject '{wrong_match.get('name')}' - different company than '{extracted_company}'. User said company not in database."
                ).with_inputs("extracted_company", "candidate_customers")

                examples.append(example)
                logger.info(f"Created customer matching example: '{extracted_company}' should NOT match '{wrong_match.get('name')}'")

    return examples


def train_model(signature_type, examples):
    """Train a specific DSPy signature with examples"""
    if not examples:
        logger.warning(f"No examples for {signature_type}, skipping training")
        return None

    logger.info(f"\n{'='*70}")
    logger.info(f"Training {signature_type} with {len(examples)} examples")
    logger.info(f"{'='*70}")

    try:
        # Create the module based on signature type
        if signature_type == 'ConfirmAllProducts':
            module = dspy.ChainOfThought(ConfirmAllProducts)
        elif signature_type == 'ExtractOrderEntities':
            module = dspy.ChainOfThought(ExtractOrderEntities)
        elif signature_type == 'ClassifyEmailIntent':
            module = dspy.ChainOfThought(ClassifyEmailIntent)
        elif signature_type == 'MatchCustomerToDatabase':
            module = dspy.ChainOfThought(MatchCustomerToDatabase)
        else:
            logger.error(f"Unknown signature type: {signature_type}")
            return None

        # Create optimizer
        optimizer = dspy.BootstrapFewShot(
            metric=lambda example, pred, trace=None: True,  # Simple metric for now
            max_bootstrapped_demos=min(3, len(examples)),  # Use up to 3 examples
            max_labeled_demos=min(2, len(examples))  # Keep 2 as labeled
        )

        # Compile (train) the module
        logger.info(f"Compiling {signature_type} with BootstrapFewShot...")
        compiled_module = optimizer.compile(module, trainset=examples)

        logger.info(f"✓ {signature_type} training completed successfully!")

        # Save the compiled module
        output_dir = Path('trained_models')
        output_dir.mkdir(exist_ok=True)

        compiled_module.save(f'trained_models/{signature_type.lower()}_trained.json')
        logger.info(f"✓ Saved trained model to trained_models/{signature_type.lower()}_trained.json")

        return compiled_module

    except Exception as e:
        logger.error(f"Error training {signature_type}: {e}", exc_info=True)
        return None


def mark_examples_as_used(training_examples):
    """Mark all training examples as used"""
    for item in training_examples:
        item['used_in_training'] = True

    # Save updated training examples
    with open('feedback/training_examples.json', 'w', encoding='utf-8') as f:
        json.dump(training_examples, f, indent=2, ensure_ascii=False)

    logger.info("✓ Marked all examples as used in training")


def main():
    """Main training workflow"""
    logger.info("\n" + "="*70)
    logger.info("DSPy Model Training from User Feedback")
    logger.info("="*70 + "\n")

    # Setup DSPy
    logger.info("Initializing DSPy...")
    setup_dspy()

    # Load training examples
    logger.info("\nLoading training examples from feedback...")
    training_examples = load_training_examples()

    if not training_examples:
        logger.error("No training examples found. Exiting.")
        return

    # Load corrections for customer matching
    logger.info("\nLoading corrections for customer matching...")
    corrections = load_corrections()

    # Extract customer matching examples
    logger.info("\nExtracting customer matching examples...")
    customer_examples = extract_customer_matching_examples(corrections)

    # Convert to DSPy format
    logger.info("\nConverting examples to DSPy format...")
    examples_by_signature = convert_to_dspy_examples(training_examples)

    # Add customer matching examples
    if customer_examples:
        examples_by_signature['MatchCustomerToDatabase'] = customer_examples

    # Summary
    logger.info("\n" + "="*70)
    logger.info("Training Summary:")
    logger.info("="*70)
    for sig_type, examples in examples_by_signature.items():
        logger.info(f"  {sig_type}: {len(examples)} examples")
    logger.info("")

    # Train each signature
    results = {}
    for signature_type, examples in examples_by_signature.items():
        if examples:
            trained_model = train_model(signature_type, examples)
            results[signature_type] = trained_model is not None

    # Mark examples as used
    if any(results.values()):
        logger.info("\nMarking training examples as used...")
        mark_examples_as_used(training_examples)

        # Mark corrections as applied
        if customer_examples and results.get('MatchCustomerToDatabase'):
            logger.info("\nMarking corrections as applied...")
            for correction in corrections:
                if not correction.get('applied_to_model', False):
                    correction['applied_to_model'] = True

            # Save updated corrections
            with open('feedback/corrections.json', 'w', encoding='utf-8') as f:
                json.dump(corrections, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Marked {len(corrections)} corrections as applied")

    # Final summary
    logger.info("\n" + "="*70)
    logger.info("Training Complete!")
    logger.info("="*70)
    for sig_type, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        logger.info(f"  {sig_type}: {status}")
    logger.info("")

    if any(results.values()):
        logger.info("Trained models saved to: trained_models/")
        logger.info("\nNext Steps:")
        logger.info("1. Test the trained models with new emails")
        logger.info("2. If performance improves, integrate into production")
        logger.info("3. Continue collecting feedback for further improvements")
    else:
        logger.warning("No models were successfully trained. Check logs for errors.")


if __name__ == '__main__':
    main()
