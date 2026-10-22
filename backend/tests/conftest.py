"""Keep unit/integration tests offline and independent of large model downloads."""

from __future__ import annotations

import pytest

from app.services.embedding_service import EmbeddingService
from app.services.nli_service import NLIService


@pytest.fixture(autouse=True)
def disable_heavy_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(EmbeddingService, "_ensure_model", lambda self: None)
    monkeypatch.setattr(NLIService, "_ensure_model", lambda self: None)
