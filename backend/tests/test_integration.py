from pathlib import Path

from app.models.change import ChangeType
from app.services.comparison_service import ComparisonService
from app.services.embedding_service import EmbeddingService
from app.services.nli_service import NLIService

FIXTURES = Path(__file__).parent / "fixtures"


class DisabledNLI(NLIService):
    def __init__(self) -> None:
        super().__init__()

    @property
    def available(self) -> bool:
        return False


def test_full_pipeline_detects_expected_categories() -> None:
    service = ComparisonService(
        embedding_service=EmbeddingService(),
        nli_service=DisabledNLI(),
    )
    result = service.compare_files(
        FIXTURES / "document_v1.txt",
        FIXTURES / "document_v2.txt",
        old_filename="document_v1.txt",
        new_filename="document_v2.txt",
    )
    types = {change.type for change in result.changes}

    assert ChangeType.UNCHANGED in types
    assert ChangeType.ADDITION in types
    assert ChangeType.DELETION in types
    assert ChangeType.NUMERICAL_CHANGE in types
    assert ChangeType.TEMPORAL_CHANGE in types
    assert ChangeType.ENTITY_CHANGE in types
    assert ChangeType.CONTRADICTION in types
    assert ChangeType.REFINEMENT in types

    numerical = next(change for change in result.changes if change.type == ChangeType.NUMERICAL_CHANGE)
    assert numerical.details.get("percentage_change") == 50.0
    assert numerical.explanation

    temporal = next(change for change in result.changes if change.type == ChangeType.TEMPORAL_CHANGE)
    assert temporal.details.get("days_changed") == 46

    assert result.summary.total_changes >= 7
    assert result.old_document.filename == "document_v1.txt"
    assert result.new_document.filename == "document_v2.txt"
    assert result.alignment_stats["old_sentences"] >= 8
    assert result.alignment_stats["new_sentences"] >= 8
