"""Change classification types and in-memory change records."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ChangeType(str, Enum):
    """Supported semantic change categories."""

    UNCHANGED = "UNCHANGED"
    ADDITION = "ADDITION"
    DELETION = "DELETION"
    MODIFICATION = "MODIFICATION"
    NUMERICAL_CHANGE = "NUMERICAL_CHANGE"
    TEMPORAL_CHANGE = "TEMPORAL_CHANGE"
    ENTITY_CHANGE = "ENTITY_CHANGE"
    CONTRADICTION = "CONTRADICTION"
    REFINEMENT = "REFINEMENT"


@dataclass
class Change:
    """A structured change produced by the detector and explanation layer."""

    id: str
    type: ChangeType
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    old_sentence_id: Optional[str] = None
    new_sentence_id: Optional[str] = None
    old_page: Optional[int] = None
    new_page: Optional[int] = None
    old_section: Optional[str] = None
    new_section: Optional[str] = None
    similarity: Optional[float] = None
    confidence: float = 0.0
    explanation: str = ""
    details: dict[str, Any] = field(default_factory=dict)
