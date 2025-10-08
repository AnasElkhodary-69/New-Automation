"""
True RAG Implementation with FAISS and Sentence Transformers

This module provides semantic search capabilities for product matching using:
- Sentence Transformers for generating embeddings (multilingual model for German support)
- FAISS for efficient vector similarity search
"""

import os
import json
import pickle
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class ProductRAG:
    """
    RAG system for semantic product matching using vector embeddings
    """

    def __init__(
        self,
        products_json: str = "odoo_database/odoo_products.json",
        model_name: str = "Alibaba-NLP/gte-modernbert-base",
        index_path: str = "odoo_database/product_faiss.index",
        metadata_path: str = "odoo_database/product_metadata.pkl"
    ):
        """
        Initialize RAG system

        Args:
            products_json: Path to products JSON file
            model_name: Sentence Transformers model name
                - Alibaba-NLP/gte-modernbert-base: State-of-the-art retrieval (768 dim) - DEFAULT [0.92-0.97 confidence]
                - all-MiniLM-L6-v2: Fast, lightweight baseline (384 dim) [0.82-0.98 confidence]
                - paraphrase-multilingual-mpnet-base-v2: Multilingual/German (768 dim)
            index_path: Path to save/load FAISS index
            metadata_path: Path to save/load product metadata
        """
        self.products_json = products_json
        self.model_name = model_name
        self.index_path = index_path
        self.metadata_path = metadata_path

        # Will be initialized in load_or_build_index()
        self.model = None
        self.index = None
        self.products_metadata = []  # List of product dicts matching index order

        logger.info(f"Initializing ProductRAG with model: {model_name}")

    def load_or_build_index(self):
        """
        Load existing FAISS index or build new one from products JSON
        """
        # Check if index exists
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            logger.info("Loading existing FAISS index...")
            self._load_index()
        else:
            logger.info("Building new FAISS index from products JSON...")
            self._build_index()

    def _load_index(self):
        """Load pre-built FAISS index and metadata"""
        # Load embedding model
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

        # Load FAISS index
        self.index = faiss.read_index(self.index_path)

        # Load metadata
        with open(self.metadata_path, 'rb') as f:
            self.products_metadata = pickle.load(f)

        logger.info(f"Loaded FAISS index with {self.index.ntotal} products")
        logger.info(f"Embedding dimension: {self.model.get_sentence_embedding_dimension()}")

    def _build_index(self):
        """Build FAISS index from products JSON"""
        # Load products JSON
        logger.info(f"Loading products from {self.products_json}")
        with open(self.products_json, 'r', encoding='utf-8') as f:
            products = json.load(f)

        if not products:
            raise ValueError("No products found in JSON file")

        logger.info(f"Loaded {len(products)} products")

        # Load embedding model
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {embedding_dim}")

        # Prepare product texts for embedding
        logger.info("Preparing product descriptions for embedding...")
        product_texts = []
        self.products_metadata = []

        for product in products:
            # Create rich text representation for better semantic matching
            text_parts = []

            # Product code (HIGHEST PRIORITY - repeat 3x for emphasis)
            if product.get('default_code'):
                code = product['default_code']
                # Repeat code multiple times to increase matching weight
                text_parts.append(f"{code} {code} {code}")
                text_parts.append(f"Code: {code}")
                text_parts.append(f"Product Code: {code}")

            # Product name
            if product.get('name'):
                text_parts.append(f"Name: {product['name']}")

            # Display name (often contains more details)
            if product.get('display_name'):
                text_parts.append(f"Display: {product['display_name']}")

            # Combine all parts
            product_text = " | ".join(text_parts)
            product_texts.append(product_text)
            self.products_metadata.append(product)

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(product_texts)} products...")
        logger.info("(This may take a few minutes on first run...)")

        embeddings = self.model.encode(
            product_texts,
            show_progress_bar=True,
            batch_size=32,
            convert_to_numpy=True
        )

        logger.info(f"Generated embeddings shape: {embeddings.shape}")

        # Build FAISS index
        logger.info("Building FAISS index...")

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)

        # Create index (IndexFlatIP = Inner Product = Cosine similarity for normalized vectors)
        self.index = faiss.IndexFlatIP(embedding_dim)

        # Add embeddings to index
        self.index.add(embeddings)

        logger.info(f"FAISS index built with {self.index.ntotal} products")

        # Save index and metadata
        logger.info("Saving FAISS index and metadata...")
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)

        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.products_metadata, f)

        logger.info("Index saved successfully")

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.5
    ) -> List[Dict]:
        """
        Semantic search for products

        Args:
            query: Product name or description to search
            top_k: Number of results to return
            min_score: Minimum similarity score (0.0 to 1.0)

        Returns:
            List of products with similarity scores
        """
        if self.index is None or self.model is None:
            raise RuntimeError("Index not loaded. Call load_or_build_index() first.")

        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)

        # Search in FAISS index
        scores, indices = self.index.search(query_embedding, top_k)

        # Prepare results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= min_score:
                product = self.products_metadata[idx].copy()
                product['similarity_score'] = float(score)
                product['match_method'] = 'semantic_rag'
                results.append(product)

        return results

    def rebuild_index(self):
        """Force rebuild of FAISS index from products JSON"""
        logger.info("Forcing rebuild of FAISS index...")
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.metadata_path):
            os.remove(self.metadata_path)
        self._build_index()
