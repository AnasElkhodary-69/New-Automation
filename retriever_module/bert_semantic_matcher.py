"""
BERT Semantic Matcher Module

This module provides semantic product matching using transformer embeddings.
Uses Alibaba-NLP/gte-modernbert-base model for state-of-the-art multilingual
semantic understanding of product descriptions.

Key Features:
- Semantic understanding (tape vs seal, blade vs adhesive, etc.)
- Multilingual support (German ↔ English)
- Long context support (8192 tokens)
- Cached embeddings for fast matching
- Filters semantically similar products for downstream token matching

Architecture:
This is Stage 1 of the Hybrid Matcher:
  Stage 1 (BERT): Semantic filter → Top 20 candidates @ 60% threshold
  Stage 2 (Token): Dimension precision → Final top 5 results

Author: Claude Code
Date: 2025-10-09
"""

import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging
import os

# GPU mode enabled - CUDA is now supported on Windows
# Removed CPU enforcement to allow GPU acceleration
import platform

from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)


class BertSemanticMatcher:
    """
    Semantic product matcher using BERT embeddings.

    Uses Alibaba-NLP/gte-modernbert-base model for semantic understanding.
    Computes and caches embeddings for all products, then performs cosine
    similarity matching against query embeddings.
    """

    def __init__(
        self,
        products_json_path: str,
        model_name: str = "Alibaba-NLP/gte-modernbert-base",
        cache_dir: str = ".bert_cache",
        device: Optional[str] = None
    ):
        """
        Initialize BERT Semantic Matcher.

        Args:
            products_json_path: Path to products JSON file
            model_name: HuggingFace model identifier (or path to fine-tuned model)
            cache_dir: Directory for caching embeddings
            device: Device to use ('cuda', 'cpu', or None for auto)
        """
        self.products_json_path = Path(products_json_path)

        # Check if fine-tuned model exists and use it automatically
        finetuned_model_path = Path("models/finetuned-product-matcher")
        if finetuned_model_path.exists() and model_name == "Alibaba-NLP/gte-modernbert-base":
            logger.info(f"Fine-tuned model found at {finetuned_model_path}, using it instead of base model")
            self.model_name = str(finetuned_model_path)
            self.is_finetuned = True
        else:
            self.model_name = model_name
            self.is_finetuned = False

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Auto-detect device (GPU if available, CPU fallback)
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            if self.device == 'cuda':
                logger.info(f"GPU detected: {torch.cuda.get_device_name(0)} - Using CUDA acceleration")
            else:
                logger.info("No GPU detected - Using CPU mode")
        else:
            self.device = device

        logger.info(f"Initializing BERT Semantic Matcher with {model_name} on {self.device}")

        # Load model
        try:
            # Explicitly set device and avoid CUDA initialization issues
            self.model = SentenceTransformer(model_name, device=self.device)

            # If CUDA failed but CPU is available, retry with CPU
            if self.device == 'cuda':
                try:
                    # Test if model actually loaded on CUDA
                    _ = self.model.encode("test", convert_to_numpy=True)
                except Exception as cuda_error:
                    logger.warning(f"CUDA model failed to initialize: {cuda_error}")
                    logger.info("Retrying with CPU...")
                    self.device = 'cpu'
                    self.model = SentenceTransformer(model_name, device='cpu')

            logger.info(f"[OK] Model loaded: {model_name} on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise

        # Load products
        self.products = self._load_products()
        logger.info(f"[OK] Loaded {len(self.products)} products")

        # Load or compute embeddings
        self.embeddings = self._load_or_compute_embeddings()
        logger.info(f"[OK] Embeddings ready: {self.embeddings.shape}")

    def _load_products(self) -> List[Dict]:
        """Load products from JSON file."""
        try:
            with open(self.products_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle both list and dict formats
            if isinstance(data, dict):
                products = data.get('products', [])
            else:
                products = data

            logger.info(f"Loaded {len(products)} products from {self.products_json_path}")
            return products

        except Exception as e:
            logger.error(f"Failed to load products: {e}")
            raise

    def _get_product_text(self, product: Dict) -> str:
        """
        Convert product to searchable text.

        Combines product code, name, and other fields into a single
        text representation for embedding.

        Args:
            product: Product dictionary

        Returns:
            Text representation of product
        """
        parts = []

        # Product code (most important) - try both field names
        code = product.get('default_code') or product.get('product_code')
        if code:
            parts.append(code)

        # Product name - try both field names
        name = product.get('name') or product.get('product_name')
        if name:
            parts.append(name)

        # Alternative names/codes
        if product.get('alternative_names'):
            if isinstance(product['alternative_names'], list):
                parts.extend(product['alternative_names'])
            else:
                parts.append(str(product['alternative_names']))

        # Category (helps semantic understanding)
        if product.get('category'):
            parts.append(product['category'])

        return ' '.join(parts)

    def _compute_embeddings(self) -> np.ndarray:
        """
        Compute embeddings for all products.

        Returns:
            Numpy array of shape (num_products, embedding_dim)
        """
        logger.info("Computing embeddings for all products...")

        # Prepare texts
        texts = [self._get_product_text(p) for p in self.products]

        # Compute embeddings in batches
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalization for cosine similarity
        )

        logger.info(f"Computed embeddings: {embeddings.shape}")
        return embeddings

    def _get_cache_path(self) -> Path:
        """Get path to embeddings cache file."""
        # Use model name and products file modification time in cache filename
        mtime = self.products_json_path.stat().st_mtime
        model_slug = self.model_name.replace('/', '_')
        cache_file = f"embeddings_{model_slug}_{int(mtime)}.npy"
        return self.cache_dir / cache_file

    def _load_or_compute_embeddings(self) -> np.ndarray:
        """
        Load embeddings from cache or compute if not cached.

        Returns:
            Numpy array of product embeddings
        """
        cache_path = self._get_cache_path()

        # Try to load from cache
        if cache_path.exists():
            try:
                logger.info(f"Loading cached embeddings from {cache_path}")
                embeddings = np.load(cache_path)

                # Validate shape
                if embeddings.shape[0] == len(self.products):
                    logger.info("[OK] Cache valid, using cached embeddings")
                    return embeddings
                else:
                    logger.warning("Cache invalid (product count mismatch), recomputing")

            except Exception as e:
                logger.warning(f"Failed to load cache: {e}, recomputing")

        # Compute embeddings
        embeddings = self._compute_embeddings()

        # Save to cache
        try:
            np.save(cache_path, embeddings)
            logger.info(f"[OK] Saved embeddings to cache: {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

        return embeddings

    def _cosine_similarity(self, query_embedding: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity between query and all products.

        Args:
            query_embedding: Query embedding vector (normalized)

        Returns:
            Array of similarity scores (0-1)
        """
        # Both are L2 normalized, so cosine = dot product
        similarities = np.dot(self.embeddings, query_embedding)
        return similarities

    def search(
        self,
        query: str,
        top_k: int = 20,
        min_score: float = 0.60
    ) -> List[Dict]:
        """
        Search for products semantically similar to query.

        Args:
            query: Search query (product name, code, description)
            top_k: Maximum number of results to return
            min_score: Minimum similarity score (0-1)

        Returns:
            List of matching products with scores, sorted by relevance
        """
        # Encode query
        query_embedding = self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        # Compute similarities
        similarities = self._cosine_similarity(query_embedding)

        # Filter by threshold
        mask = similarities >= min_score
        valid_indices = np.where(mask)[0]

        # Sort by similarity (descending)
        sorted_indices = valid_indices[np.argsort(-similarities[valid_indices])]

        # Build results
        results = []
        for idx in sorted_indices[:top_k]:
            product = self.products[idx].copy()
            product['bert_score'] = float(similarities[idx])
            product['bert_score_percent'] = f"{similarities[idx] * 100:.1f}%"
            results.append(product)

        logger.info(f"BERT search: '{query}' → {len(results)} results (min: {min_score})")
        return results

    def search_by_code(
        self,
        product_code: str,
        min_score: float = 0.70
    ) -> Optional[Dict]:
        """
        Search for exact product by code with semantic fallback.

        First tries exact code match, then falls back to semantic search.

        Args:
            product_code: Product code to search for
            min_score: Minimum similarity score for semantic fallback

        Returns:
            Matching product or None
        """
        # Try exact match first - check both field names
        for idx, product in enumerate(self.products):
            code = product.get('default_code') or product.get('product_code')
            if code == product_code:
                logger.info(f"Exact code match: {product_code}")
                result = product.copy()
                result['bert_score'] = 1.0
                result['bert_score_percent'] = "100%"
                return result

        # Fall back to semantic search
        logger.info(f"No exact match for '{product_code}', using semantic search")
        results = self.search(product_code, top_k=1, min_score=min_score)
        return results[0] if results else None

    def get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding for arbitrary text.

        Useful for custom matching logic.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (normalized)
        """
        return self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True
        )


if __name__ == "__main__":
    # Test the matcher
    logging.basicConfig(level=logging.INFO)

    # Initialize
    matcher = BertSemanticMatcher("products.json")

    # Test semantic search
    test_queries = [
        "OPP Klischeeklebeband 310 x 25",
        "Rakelmesser Edelstahl Gold 35x0,20 RPE Länge 1335mm",
        "Foam Seal 120 x 31",
        "3M Cushion Mount Plus E1015"
    ]

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print('='*80)

        results = matcher.search(query, top_k=5)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. [{result['bert_score_percent']}] {result.get('product_code', 'N/A')}")
            print(f"   {result.get('product_name', 'N/A')}")
