"""Sentence embeddings with an in-process cache (SPEC.md section 5).

all-MiniLM-L6-v2 runs locally on CPU, is deterministic, and downloads once
(~90 MB). Nothing in scoring needs network access after that.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from novelty.text import neutralize_product_name


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> np.ndarray:
        """(n, d) matrix of L2-normalized vectors, one row per input text."""
        ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # lazy: slow import

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        get_dim = getattr(self._model, "get_embedding_dimension", None) or self._model.get_sentence_embedding_dimension
        self._dim = get_dim()
        self._cache: dict[str, np.ndarray] = {}

    def embed(self, texts: list[str]) -> np.ndarray:
        missing = [t for t in dict.fromkeys(texts) if t not in self._cache]
        if missing:
            vecs = self._model.encode(missing, normalize_embeddings=True, show_progress_bar=False)
            for t, v in zip(missing, vecs, strict=True):
                self._cache[t] = np.asarray(v, dtype=np.float32)
        if not texts:
            return np.zeros((0, self._dim), dtype=np.float32)
        return np.stack([self._cache[t] for t in texts])


def cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity between every row of a and every row of b. Inputs must be normalized."""
    if a.size == 0 or b.size == 0:
        return np.zeros((a.shape[0], b.shape[0]), dtype=np.float32)
    return a @ b.T


class ProductNeutralEmbedder:
    """Embeds text with the product name replaced by "the product" (see text.neutralize_product_name)."""

    def __init__(self, inner: Embedder, product_name: str):
        self.inner = inner
        self.product_name = product_name

    def embed(self, texts: list[str]) -> np.ndarray:
        return self.inner.embed([neutralize_product_name(t, self.product_name) for t in texts])
