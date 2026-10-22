"""Lazy process-wide service instances so models are not reloaded per request."""

from __future__ import annotations

from app.services.comparison_service import ComparisonService
from app.services.file_storage import FileStorage

_comparison_service: ComparisonService | None = None
_file_storage: FileStorage | None = None


def get_comparison_service() -> ComparisonService:
    """Return the singleton comparison pipeline."""
    global _comparison_service
    if _comparison_service is None:
        _comparison_service = ComparisonService()
    return _comparison_service


def get_file_storage() -> FileStorage:
    """Return the singleton upload storage helper."""
    global _file_storage
    if _file_storage is None:
        _file_storage = FileStorage()
    return _file_storage
