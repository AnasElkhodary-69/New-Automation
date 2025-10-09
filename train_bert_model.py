"""
Train BERT Model on Product Catalog

Run this script to fine-tune BERT on your specific products.
This will significantly improve matching accuracy.

Usage:
    python train_bert_model.py

The fine-tuned model will be saved to: models/finetuned-product-matcher
"""

import logging
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from retriever_module.bert_finetuner import BERTFineTuner

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main training function."""

    # Check if CUDA is available
    import torch
    has_cuda = torch.cuda.is_available()
    device_info = "GPU (CUDA)" if has_cuda else "CPU"
    time_estimate = "3-10 minutes" if has_cuda else "10-30 minutes"

    print(f"""
{'='*80}
                  BERT Fine-tuning for Product Matching
{'='*80}

  This will fine-tune the BERT model on your product catalog (2025 products)
  to improve matching accuracy for your specific domain.

  What this does:
  - Learns your product categories (L, E, G, SDS, etc.)
  - Understands dimension patterns (310x25, L1335, etc.)
  - Recognizes material types (blade, seal, tape, adhesive)
  - Maps customer terminology to your product codes

  Training Device: {device_info}
  Estimated time: {time_estimate}
  Disk space needed: ~500MB for model

  Note: Training uses {device_info}, but production uses CPU for inference
{'='*80}
    """)

    # Confirm
    response = input("Do you want to proceed with fine-tuning? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Fine-tuning cancelled.")
        return

    try:
        # Initialize fine-tuner
        logger.info("Initializing BERT Fine-tuner...")
        finetuner = BERTFineTuner(
            products_json_path="odoo_database/odoo_products.json",
            base_model="Alibaba-NLP/gte-modernbert-base",
            output_model_path="models/finetuned-product-matcher",
            use_cuda_for_training=True  # Use GPU if available (much faster!)
        )

        # Run fine-tuning
        logger.info("Starting fine-tuning process...")
        finetuner.fine_tune(
            epochs=3,  # Number of training passes
            batch_size=16,  # Batch size (reduce if out of memory)
            warmup_steps=100
        )

        # Evaluate
        logger.info("Evaluating fine-tuned model...")
        finetuner.evaluate_model()

        print(f"""
{'='*80}
                         Fine-tuning Complete!
{'='*80}

  SUCCESS: Model trained successfully
  Location: models/finetuned-product-matcher

  Next Steps:
  1. The system will automatically use the fine-tuned model
  2. Run main.py to test improved matching
  3. Compare results with previous matching scores

  The fine-tuned model is now production-ready!
{'='*80}
        """)

    except Exception as e:
        logger.error(f"Fine-tuning failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        print("\nPlease check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
