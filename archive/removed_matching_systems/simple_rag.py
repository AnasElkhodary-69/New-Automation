"""
Simple RAG Implementation with FAISS (no sentence-transformers dependency)

Uses transformers library directly to avoid dependency conflicts
"""

import os
import json
import pickle
import logging
from typing import List, Dict

import numpy as np
import faiss
import torch
from transformers import AutoTokenizer, AutoModel

logger = logging.getLogger(__name__)


class SimpleProductRAG:
    """Simple RAG using transformers directly"""

    def __init__(
        self,
        products_json: str = "odoo_database/odoo_products.json",
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        index_path: str = "odoo_database/product_faiss.index",
        metadata_path: str = "odoo_database/product_metadata.pkl"
    ):
        self.products_json = products_json
        self.model_name = model_name
        self.index_path = index_path
        self.metadata_path = metadata_path

        self.tokenizer = None
        self.model = None
        self.index = None
        self.products_metadata = []

        logger.info(f"Initializing SimpleProductRAG with model: {model_name}")

    def _mean_pooling(self, model_output, attention_mask):
        """Mean pooling to get sentence embeddings"""
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    def _encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode texts to embeddings"""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Tokenize
            encoded_input = self.tokenizer(batch, padding=True, truncation=True, return_tensors='pt', max_length=512)

            # Generate embeddings
            with torch.no_grad():
                model_output = self.model(**encoded_input)

            # Mean pooling
            embeddings = self._mean_pooling(model_output, encoded_input['attention_mask'])

            # Normalize
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

            all_embeddings.append(embeddings.cpu().numpy())

            if (i // batch_size + 1) % 10 == 0:
                logger.info(f"  Encoded {i + len(batch)}/{len(texts)} texts...")

        return np.vstack(all_embeddings)

    def load_or_build_index(self):
        """Load existing index or build new one"""
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            logger.info("Loading existing FAISS index...")
            self._load_index()
        else:
            logger.info("Building new FAISS index...")
            self._build_index()

    def _load_index(self):
        """Load pre-built index"""
        logger.info(f"Loading model: {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.eval()

        self.index = faiss.read_index(self.index_path)

        with open(self.metadata_path, 'rb') as f:
            self.products_metadata = pickle.load(f)

        logger.info(f"Loaded FAISS index with {self.index.ntotal} products")

    def _build_index(self):
        """Build FAISS index from products JSON"""
        # Load products
        logger.info(f"Loading products from {self.products_json}")
        with open(self.products_json, 'r', encoding='utf-8') as f:
            products = json.load(f)

        logger.info(f"Loaded {len(products)} products")

        # Load model
        logger.info(f"Loading model: {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.eval()

        # Prepare texts
        logger.info("Preparing product texts...")
        product_texts = []
        self.products_metadata = []

        for product in products:
            parts = []
            if product.get('default_code'):
                parts.append(f"Code: {product['default_code']}")
            if product.get('name'):
                parts.append(f"Name: {product['name']}")
            if product.get('display_name'):
                parts.append(f"Display: {product['display_name']}")

            product_texts.append(" | ".join(parts))
            self.products_metadata.append(product)

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(product_texts)} products...")
        embeddings = self._encode(product_texts)

        logger.info(f"Generated embeddings shape: {embeddings.shape}")

        # Build FAISS index
        logger.info("Building FAISS index...")
        embedding_dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(embedding_dim)  # Inner product (cosine similarity for normalized)
        self.index.add(embeddings.astype('float32'))

        logger.info(f"FAISS index built with {self.index.ntotal} products")

        # Save
        logger.info("Saving index and metadata...")
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)

        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.products_metadata, f)

        logger.info("Index saved successfully")

    def search(self, query: str, top_k: int = 5, min_score: float = 0.5) -> List[Dict]:
        """Search for products"""
        if self.index is None or self.model is None:
            raise RuntimeError("Index not loaded. Call load_or_build_index() first.")

        # Encode query
        query_embedding = self._encode([query])

        # Search
        scores, indices = self.index.search(query_embedding.astype('float32'), top_k)

        # Prepare results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= min_score:
                product = self.products_metadata[idx].copy()
                product['similarity_score'] = float(score)
                product['match_method'] = 'semantic_rag'
                results.append(product)

        return results
