"""
BERT Fine-tuning Module for Product Matching

Fine-tunes the BERT semantic matcher on your specific product catalog
to improve matching accuracy for domain-specific terminology.

Training Strategy:
1. Generate positive pairs: Similar products (same category, similar dimensions)
2. Generate negative pairs: Different products (different categories)
3. Use Contrastive Learning to fine-tune embeddings
4. Save fine-tuned model for production use

Author: Claude Code
Date: 2025-10-09
"""

import json
import logging
import random
import re
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np

from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

logger = logging.getLogger(__name__)


class BERTFineTuner:
    """
    Fine-tune BERT model on product catalog for better domain-specific matching.
    """

    def __init__(
        self,
        products_json_path: str,
        base_model: str = "Alibaba-NLP/gte-modernbert-base",
        output_model_path: str = "models/finetuned-product-matcher",
        use_cuda_for_training: bool = True
    ):
        """
        Initialize fine-tuner.

        Args:
            products_json_path: Path to products JSON file
            base_model: Base BERT model to fine-tune
            output_model_path: Where to save fine-tuned model
            use_cuda_for_training: Use CUDA/GPU for training (faster, default: True)
        """
        self.products_json_path = Path(products_json_path)
        self.base_model = base_model
        self.output_model_path = Path(output_model_path)
        self.output_model_path.mkdir(parents=True, exist_ok=True)

        # Determine training device (CUDA for training if available)
        import torch
        if use_cuda_for_training and torch.cuda.is_available():
            self.device = 'cuda'
            logger.info("Using CUDA/GPU for training (much faster!)")
        else:
            self.device = 'cpu'
            logger.info("Using CPU for training")

        # Load products
        self.products = self._load_products()
        logger.info(f"Loaded {len(self.products)} products for fine-tuning")

    def _load_products(self) -> List[Dict]:
        """Load products from JSON file."""
        with open(self.products_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _extract_product_features(self, product: Dict) -> Dict:
        """
        Extract key features from product for similarity matching.

        Returns:
            Dictionary with extracted features
        """
        code = product.get('default_code', '')
        name = product.get('name', '')
        display_name = product.get('display_name', '')

        # Extract category from code (e.g., L1335, E1015, SDS2601)
        category = None
        if code:
            # Match prefix letters (L, E, G, SDS, RPR, etc.)
            match = re.match(r'^([A-Z]+)', code.upper())
            if match:
                category = match.group(1)

        # Extract dimensions
        dimensions = []
        text = f"{code} {name} {display_name}"

        # Pattern: NNNxNN or NNN x NN
        dim_matches = re.findall(r'(\d{2,4})\s*[xX*]\s*(\d{1,3}(?:[.,]\d{1,2})?)', text)
        for width, height in dim_matches:
            dimensions.append((float(width), float(height.replace(',', '.'))))

        # Pattern: Length NNNN
        length_matches = re.findall(r'[Ll](?:ength)?\s*(\d{3,5})', text)
        for length in length_matches:
            dimensions.append((float(length), None))

        # Extract material keywords
        materials = []
        material_keywords = [
            'stainless', 'steel', 'carbon', 'rubber', 'foam', 'adhesive',
            'tape', 'klebeband', 'blade', 'rakelmesser', 'seal', 'dichtung',
            'opp', '3m', 'tesa'
        ]
        text_lower = text.lower()
        for keyword in material_keywords:
            if keyword in text_lower:
                materials.append(keyword)

        # Extract seal sub-type for distinguishing different seal products
        seal_subtype = None
        if 'seal' in text_lower or 'dichtung' in text_lower:
            if 'duro seal' in text_lower or 'duroseal' in text_lower:
                seal_subtype = 'duro_seal'
            elif 'foam seal' in text_lower or 'schaumstoff' in text_lower:
                seal_subtype = 'foam_seal'
            elif 'end seal' in text_lower or 'enddichtung' in text_lower:
                seal_subtype = 'end_seal'
            elif 'side seal' in text_lower or 'seitendichtung' in text_lower:
                seal_subtype = 'side_seal'

        return {
            'category': category,
            'dimensions': dimensions,
            'materials': materials,
            'seal_subtype': seal_subtype,
            'full_text': f"{code} {name}".strip()
        }

    def _are_similar_products(self, prod1: Dict, prod2: Dict) -> bool:
        """
        Check if two products are similar (positive pair).

        Similar products:
        - Same category (L, E, G, etc.)
        - Similar dimensions (within 10%)
        - Same material type
        - Same seal sub-type (if applicable) - CRITICAL: Duro Seal != Foam Seal
        """
        feat1 = self._extract_product_features(prod1)
        feat2 = self._extract_product_features(prod2)

        # Must have same category
        if feat1['category'] and feat2['category']:
            if feat1['category'] != feat2['category']:
                return False

        # CRITICAL: If both have seal sub-types, they MUST match
        # This prevents Duro Seal from being matched with Foam Seal
        if feat1['seal_subtype'] and feat2['seal_subtype']:
            if feat1['seal_subtype'] != feat2['seal_subtype']:
                return False

        # Check dimension similarity
        if feat1['dimensions'] and feat2['dimensions']:
            dim1 = feat1['dimensions'][0]  # First dimension
            dim2 = feat2['dimensions'][0]

            # Compare width/length (first value)
            if dim1[0] and dim2[0]:
                diff_pct = abs(dim1[0] - dim2[0]) / max(dim1[0], dim2[0])
                if diff_pct > 0.10:  # More than 10% different
                    return False

        # Check material overlap
        if feat1['materials'] and feat2['materials']:
            overlap = set(feat1['materials']) & set(feat2['materials'])
            if not overlap:
                return False

        return True

    def _generate_training_pairs(self) -> Tuple[List[InputExample], List[InputExample]]:
        """
        Generate positive and hard negative training pairs.

        Returns:
            Tuple of (positive_pairs, negative_pairs)
        """
        logger.info("Generating training pairs from product catalog...")

        positive_pairs = []
        negative_pairs = []

        # Strategy 1: Generate positive pairs (similar products)
        for i, prod1 in enumerate(self.products):
            if i % 100 == 0:
                logger.info(f"Processing product {i}/{len(self.products)}")

            feat1 = self._extract_product_features(prod1)
            text1 = feat1['full_text']

            if not text1:
                continue

            # Find similar products
            similar_count = 0
            for j, prod2 in enumerate(self.products):
                if i == j:
                    continue

                if self._are_similar_products(prod1, prod2):
                    feat2 = self._extract_product_features(prod2)
                    text2 = feat2['full_text']

                    if text2:
                        # Create positive pair (similarity score: 0.8-1.0)
                        score = 0.9 + random.uniform(-0.1, 0.1)
                        positive_pairs.append(InputExample(
                            texts=[text1, text2],
                            label=score
                        ))
                        similar_count += 1

                        if similar_count >= 3:  # Limit to 3 positive pairs per product
                            break

        # Strategy 2: Generate hard negative pairs (different categories)
        random.shuffle(self.products)
        for i in range(min(len(positive_pairs) * 2, len(self.products) - 1)):
            prod1 = self.products[i]
            prod2 = self.products[i + 1]

            feat1 = self._extract_product_features(prod1)
            feat2 = self._extract_product_features(prod2)

            # Only use as negative if categories are different
            if feat1['category'] and feat2['category']:
                if feat1['category'] != feat2['category']:
                    text1 = feat1['full_text']
                    text2 = feat2['full_text']

                    if text1 and text2:
                        # Create negative pair (similarity score: 0.0-0.3)
                        score = random.uniform(0.0, 0.3)
                        negative_pairs.append(InputExample(
                            texts=[text1, text2],
                            label=score
                        ))

        # Strategy 3: Generate explicit negative pairs for different seal types
        # This is CRITICAL to prevent Duro Seal from matching with Foam Seal
        logger.info("Generating explicit seal sub-type negative pairs...")
        seal_products_by_type = {}
        for prod in self.products:
            feat = self._extract_product_features(prod)
            if feat['seal_subtype']:
                if feat['seal_subtype'] not in seal_products_by_type:
                    seal_products_by_type[feat['seal_subtype']] = []
                seal_products_by_type[feat['seal_subtype']].append(prod)

        # Create negative pairs between different seal types
        seal_types = list(seal_products_by_type.keys())
        for i, type1 in enumerate(seal_types):
            for type2 in seal_types[i+1:]:
                # Sample products from each type
                prods1 = seal_products_by_type[type1]
                prods2 = seal_products_by_type[type2]

                for prod1 in random.sample(prods1, min(5, len(prods1))):
                    for prod2 in random.sample(prods2, min(2, len(prods2))):
                        feat1 = self._extract_product_features(prod1)
                        feat2 = self._extract_product_features(prod2)

                        text1 = feat1['full_text']
                        text2 = feat2['full_text']

                        if text1 and text2:
                            # Very low similarity (0.0-0.2) for different seal types
                            score = random.uniform(0.0, 0.2)
                            negative_pairs.append(InputExample(
                                texts=[text1, text2],
                                label=score
                            ))

        logger.info(f"Generated {len(positive_pairs)} positive pairs")
        logger.info(f"Generated {len(negative_pairs)} negative pairs (including seal sub-type negatives)")

        return positive_pairs, negative_pairs

    def _generate_augmented_pairs(self) -> List[InputExample]:
        """
        Generate augmented training pairs by creating variations of product descriptions.

        This helps the model learn to match products even when described differently.
        """
        logger.info("Generating augmented training pairs...")

        augmented_pairs = []

        for product in self.products:
            code = product.get('default_code', '')
            name = product.get('name', '')

            if not code or not name:
                continue

            # Create variations of the same product
            variations = [
                f"{code} {name}",  # Full
                f"{code}",  # Code only
                name,  # Name only
                name.replace('x', ' x '),  # Add spaces around 'x'
                name.replace('mm', ' mm'),  # Add space before mm
                name.lower(),  # Lowercase
            ]

            # Each variation should match to the original (high similarity)
            base_text = f"{code} {name}"
            for variation in variations:
                if variation and variation != base_text:
                    augmented_pairs.append(InputExample(
                        texts=[base_text, variation],
                        label=0.95  # Very high similarity (same product)
                    ))

        logger.info(f"Generated {len(augmented_pairs)} augmented pairs")
        return augmented_pairs

    def fine_tune(
        self,
        epochs: int = 3,
        batch_size: int = 16,
        warmup_steps: int = 100
    ):
        """
        Fine-tune the BERT model on product catalog.

        Args:
            epochs: Number of training epochs
            batch_size: Training batch size
            warmup_steps: Warmup steps for learning rate scheduler
        """
        logger.info("="*80)
        logger.info("Starting BERT Fine-tuning for Product Matching")
        logger.info("="*80)

        # Load base model on training device (CUDA for training, CPU for production)
        logger.info(f"Loading base model: {self.base_model} on {self.device}")
        model = SentenceTransformer(self.base_model, device=self.device)

        # Generate training data
        positive_pairs, negative_pairs = self._generate_training_pairs()
        augmented_pairs = self._generate_augmented_pairs()

        # Combine all training examples
        train_examples = positive_pairs + negative_pairs + augmented_pairs
        random.shuffle(train_examples)

        logger.info(f"Total training examples: {len(train_examples)}")

        # Create DataLoader
        train_dataloader = DataLoader(
            train_examples,
            shuffle=True,
            batch_size=batch_size
        )

        # Define loss function (Cosine Similarity Loss)
        train_loss = losses.CosineSimilarityLoss(model)

        # Fine-tune
        logger.info(f"Training for {epochs} epochs with batch size {batch_size} on {self.device}")
        if self.device == 'cuda':
            logger.info("Training on GPU - Expected time: 3-10 minutes")
        else:
            logger.info("Training on CPU - Expected time: 10-30 minutes")

        model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=epochs,
            warmup_steps=warmup_steps,
            output_path=str(self.output_model_path),
            show_progress_bar=True
        )

        # Model is saved and can be loaded on any device (CPU or GPU)
        logger.info("Model saved - can be loaded on CPU or GPU for inference")

        logger.info("="*80)
        logger.info(f"Fine-tuning complete! Model saved to: {self.output_model_path}")
        logger.info("="*80)

    def evaluate_model(self):
        """
        Evaluate the fine-tuned model against test queries.
        """
        logger.info("Evaluating fine-tuned model...")

        # Load fine-tuned model on CPU (simulating production environment)
        logger.info("Loading model on CPU (production mode) for evaluation...")
        model = SentenceTransformer(str(self.output_model_path), device='cpu')

        # Test queries (examples from your actual emails)
        test_queries = [
            ("9000841", "Doctor Blade Stainless Steel Gold 35x0.20 RPE"),
            ("9000826", "DuroSeal W&H End Seals Miraflex SDS 007 CR Gray"),
            ("E1015", "3M Cushion Mount Plus"),
            ("L1335", "Doctor Blade Gold 35x0.20 RPE"),
            ("OPP Klischeeklebeband 310 x 25", ""),
        ]

        # Encode all products
        product_texts = [
            f"{p.get('default_code', '')} {p.get('name', '')}".strip()
            for p in self.products
        ]
        product_embeddings = model.encode(product_texts, convert_to_numpy=True)

        logger.info("\nTest Results:")
        logger.info("="*80)

        for code, description in test_queries:
            query = f"{code} {description}".strip()
            query_embedding = model.encode(query, convert_to_numpy=True)

            # Compute similarities
            similarities = np.dot(product_embeddings, query_embedding)
            top_3_idx = np.argsort(-similarities)[:3]

            logger.info(f"\nQuery: {query}")
            logger.info("-" * 80)
            for rank, idx in enumerate(top_3_idx, 1):
                product = self.products[idx]
                score = similarities[idx]
                logger.info(f"  {rank}. [{score:.1%}] {product.get('default_code', 'N/A')} - {product.get('name', 'N/A')[:60]}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  BERT Fine-tuning for Product Matching                       ║
║                                                                              ║
║  This will fine-tune the BERT model on your product catalog to improve      ║
║  matching accuracy for domain-specific products.                            ║
║                                                                              ║
║  Estimated time: 10-30 minutes on CPU                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    # Initialize fine-tuner
    finetuner = BERTFineTuner(
        products_json_path="odoo_database/odoo_products.json",
        base_model="Alibaba-NLP/gte-modernbert-base",
        output_model_path="models/finetuned-product-matcher"
    )

    # Run fine-tuning
    finetuner.fine_tune(epochs=3, batch_size=16)

    # Evaluate
    finetuner.evaluate_model()

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         Fine-tuning Complete!                                ║
║                                                                              ║
║  To use the fine-tuned model, update processor.py:                          ║
║    bert_model_name="models/finetuned-product-matcher"                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
