"""In-memory comparison results and alignment structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from app.models.change import Change
from app.models.document import Document


class AlignmentStatus(str, Enum):
    """How a sentence participates in alignment."""

    MATCHED = "MATCHED"
    ADDED = "ADDED"
    DELETED = "DELETED"


class ComparisonStatus(str, Enum):
    """Lifecycle of a persisted comparison."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class AlignmentPair:
    """One alignment decision between old and new sentences."""

    status: AlignmentStatus
    old_sentence_id: Optional[str] = None
    new_sentence_id: Optional[str] = None
    similarity: Optional[float] = None
    confidence: Optional[float] = None


@dataclass
class AlignmentResult:
    """Full alignment of two documents."""

    pairs: list[AlignmentPair] = field(default_factory=list)

    def matched(self) -> list[AlignmentPair]:
        return [pair for pair in self.pairs if pair.status == AlignmentStatus.MATCHED]

    def added(self) -> list[AlignmentPair]:
        return [pair for pair in self.pairs if pair.status == AlignmentStatus.ADDED]

    def deleted(self) -> list[AlignmentPair]:
        return [pair for pair in self.pairs if pair.status == AlignmentStatus.DELETED]


@dataclass
class ComparisonSummary:
    """Aggregate counts for a comparison (excludes UNCHANGED)."""

    total_changes: int = 0
    additions: int = 0
    deletions: int = 0
    modifications: int = 0
    numerical_changes: int = 0
    temporal_changes: int = 0
    entity_changes: int = 0
    contradictions: int = 0
    refinements: int = 0
    unchanged: int = 0


@dataclass
class ComparisonResult:
    """Complete pipeline output for two document versions."""

    comparison_id: str
    old_document: Document
    new_document: Document
    summary: ComparisonSummary
    changes: list[Change] = field(default_factory=list)
    status: ComparisonStatus = ComparisonStatus.COMPLETED
    created_at: datetime = field(default_factory=datetime.utcnow)
    alignment_stats: dict[str, Any] = field(default_factory=dict)
