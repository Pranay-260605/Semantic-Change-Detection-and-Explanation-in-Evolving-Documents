"""Natural language inference used as one signal for change reasoning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NLIResult:
    label: str
    confidence: float
    scores: dict[str, float]


class NLIService:
    """Lazy-loaded NLI model with batch inference and graceful failure."""

    _model = None
    _model_name: str | None = None
    _labels: list[str] | None = None
    _load_error: str | None = None

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def available(self) -> bool:
        if not self.settings.enable_nli:
            return False
        return self._ensure_model() is not None

    def _ensure_model(self):
        if not self.settings.enable_nli:
            return None
        name = self.settings.nli_model
        if NLIService._model is not None and NLIService._model_name == name:
            return NLIService._model
        if NLIService._load_error and NLIService._model_name == name:
            return None
        try:
            from sentence_transformers import CrossEncoder

            logger.info("Loading NLI model name=%s", name)
            model = CrossEncoder(name)
            labels = _labels_from_model(model)
            NLIService._model = model
            NLIService._model_name = name
            NLIService._labels = labels
            NLIService._load_error = None
            logger.info("NLI model ready name=%s labels=%s", name, labels)
        except Exception:
            NLIService._model = None
            NLIService._model_name = name
            NLIService._load_error = "load_failed"
            logger.exception("Failed to load NLI model name=%s", name)
        return NLIService._model

    def classify_pair(self, premise: str, hypothesis: str) -> NLIResult:
        results = self.classify_pairs([(premise, hypothesis)])
        return results[0] if results else NLIResult("NEUTRAL", 0.0, {})

    def classify_pairs(self, pairs: Sequence[tuple[str, str]]) -> list[NLIResult]:
        if not pairs:
            return []
        model = self._ensure_model()
        if model is None:
            return [NLIResult("NEUTRAL", 0.0, {}) for _ in pairs]

        logger.info("NLI execution pairs=%s", len(pairs))
        try:
            raw_scores = model.predict(
                list(pairs),
                batch_size=self.settings.nli_batch_size,
                show_progress_bar=False,
            )
        except Exception:
            logger.exception("NLI inference failed")
            return [NLIResult("NEUTRAL", 0.0, {}) for _ in pairs]

        matrix = np.atleast_2d(np.asarray(raw_scores, dtype=np.float32))
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        labels = NLIService._labels or _default_labels(matrix.shape[1])
        results: list[NLIResult] = []
        for row in matrix:
            if row.size == 1:
                # Some cross-encoders emit a single contradiction-style score.
                score = float(row[0])
                label = "CONTRADICTION" if score >= 0.5 else "NEUTRAL"
                results.append(NLIResult(label, abs(score), {"score": score}))
                continue
            probs = _softmax(row)
            best = int(np.argmax(probs))
            mapped = _normalize_label(labels[best] if best < len(labels) else "NEUTRAL")
            score_map = {
                _normalize_label(labels[i] if i < len(labels) else f"label_{i}"): float(probs[i])
                for i in range(len(probs))
            }
            results.append(NLIResult(mapped, float(probs[best]), score_map))
        return results


def _labels_from_model(model) -> list[str]:
    config = getattr(getattr(model, "model", None), "config", None)
    id2label = getattr(config, "id2label", None) if config is not None else None
    if isinstance(id2label, dict) and id2label:
        return [_normalize_label(id2label[i]) for i in sorted(id2label)]
    return ["CONTRADICTION", "ENTAILMENT", "NEUTRAL"]


def _default_labels(width: int) -> list[str]:
    if width >= 3:
        return ["CONTRADICTION", "ENTAILMENT", "NEUTRAL"][:width]
    return ["SCORE"]


def _normalize_label(label: str) -> str:
    value = str(label).strip().upper().replace("LABEL_", "")
    if value in {"CONTRADICTION", "CONTRADICT", "2"}:
        return "CONTRADICTION"
    if value in {"ENTAILMENT", "ENTAIL", "0"}:
        return "ENTAILMENT"
    if value in {"NEUTRAL", "1"}:
        return "NEUTRAL"
    return value


def _softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values)
    exp = np.exp(shifted)
    total = np.sum(exp)
    if total <= 0:
        return np.ones_like(values) / len(values)
    return exp / total
