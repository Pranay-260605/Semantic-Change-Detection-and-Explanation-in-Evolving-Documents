"""Lazy-loaded sentence embeddings with in-memory model caching."""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.document import Sentence

logger = get_logger(__name__)


class EmbeddingService:
    """Encode sentences with a cached SentenceTransformer model."""

    _model = None
    _model_name: str | None = None
    _load_error: str | None = None

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def available(self) -> bool:
        return self._ensure_model() is not None

    def _ensure_model(self):
        name = self.settings.embedding_model
        if EmbeddingService._model is not None and EmbeddingService._model_name == name:
            return EmbeddingService._model
        if EmbeddingService._load_error and EmbeddingService._model_name == name:
            return None
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model name=%s", name)
            EmbeddingService._model = SentenceTransformer(name)
            EmbeddingService._model_name = name
            EmbeddingService._load_error = None
            logger.info("Embedding model ready name=%s", name)
        except Exception as exc:
            EmbeddingService._model = None
            EmbeddingService._model_name = name
            EmbeddingService._load_error = str(exc)
            logger.exception("Failed to load embedding model name=%s", name)
        return EmbeddingService._model

    def encode_sentences(self, sentences: Sequence[Sentence] | Sequence[str]) -> np.ndarray:
        """Batch-encode sentences and return L2-normalized embeddings."""
        texts = [
            item.text if isinstance(item, Sentence) else item
            for item in sentences
        ]
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)
        return self.encode_texts(texts)

    def encode_texts(self, texts: Sequence[str]) -> np.ndarray:
        model = self._ensure_model()
        if model is None:
            logger.warning("Embedding model unavailable; using lexical fallback vectors")
            return self._lexical_encode(texts)

        logger.info("embedding generation sentences=%s", len(texts))
        vectors = model.encode(
            list(texts),
            batch_size=self.settings.embedding_batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    def similarity(self, embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
        """Cosine similarity for already-normalized vectors."""
        if embedding_a.size == 0 or embedding_b.size == 0:
            return 0.0
        return float(np.dot(embedding_a, embedding_b))

    def similarity_matrix(self, old_vectors: np.ndarray, new_vectors: np.ndarray) -> np.ndarray:
        """Pairwise cosine similarities between two normalized embedding matrices."""
        if old_vectors.size == 0 or new_vectors.size == 0:
            return np.zeros((len(old_vectors), len(new_vectors)), dtype=np.float32)
        return old_vectors @ new_vectors.T

    def _lexical_encode(self, texts: Iterable[str]) -> np.ndarray:
        """Deterministic hashed bag-of-words fallback used if the model cannot load."""
        dim = 256
        items = list(texts)
        matrix = np.zeros((len(items), dim), dtype=np.float32)
        for row, text in enumerate(items):
            for token in _tokenize(text):
                matrix[row, hash(token) % dim] += 1.0
            norm = np.linalg.norm(matrix[row])
            if norm > 0:
                matrix[row] /= norm
        return matrix


_SYNONYMS = {
    "employees": "staff",
    "employee": "staff",
    "people": "staff",
    "persons": "staff",
    "person": "staff",
    "employs": "staff",
    "employment": "staff",
    "has": "have",
    "headquartered": "based",
}


def _tokenize(text: str) -> list[str]:
    raw = [token for token in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if token]
    return [_SYNONYMS.get(token, token) for token in raw]
