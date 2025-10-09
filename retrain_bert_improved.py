"""
Retrain BERT model with improved seal sub-type distinction
Non-interactive version for automation
"""
import logging
import torch
from retriever_module.bert_finetuner import BERTFineTuner

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    logger.info("="*80)
    logger.info("RETRAINING BERT with Improved Seal Sub-type Distinction")
    logger.info("="*80)

    # Check CUDA
    has_cuda = torch.cuda.is_available()
    device_info = "GPU (CUDA)" if has_cuda else "CPU"

    logger.info(f"Training Device: {device_info}")
    logger.info(f"Expected time: {'3-10 minutes' if has_cuda else '10-30 minutes'}")
    logger.info("")
    logger.info("Key Improvements:")
    logger.info("  1. Seal sub-type detection (duro_seal, foam_seal, end_seal, side_seal)")
    logger.info("  2. Prevents Duro Seal from matching with Foam Seal")
    logger.info("  3. Explicit negative pairs between different seal types")
    logger.info("="*80)
    logger.info("")

    # Initialize fine-tuner
    logger.info("Initializing fine-tuner...")
    finetuner = BERTFineTuner(
        products_json_path="odoo_database/odoo_products.json",
        base_model="Alibaba-NLP/gte-modernbert-base",
        output_model_path="models/finetuned-product-matcher",
        use_cuda_for_training=True  # Use GPU if available
    )

    # Train
    logger.info("Starting training...")
    finetuner.fine_tune(epochs=3, batch_size=16)

    # Evaluate
    logger.info("")
    logger.info("Evaluating model...")
    finetuner.evaluate_model()

    logger.info("")
    logger.info("="*80)
    logger.info("RETRAINING COMPLETE!")
    logger.info("="*80)
    logger.info("Model saved to: models/finetuned-product-matcher/")
    logger.info("The hybrid matcher will automatically use this fine-tuned model.")
    logger.info("="*80)

if __name__ == "__main__":
    main()
