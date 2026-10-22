from app.models.comparison import AlignmentPair, AlignmentResult, AlignmentStatus
from app.models.change import ChangeType
from app.services.change_detector import ChangeDetector
from app.services.entity_service import EntityService
from app.services.explanation_service import ExplanationService
from app.services.value_extractor import ValueExtractor
from tests.helpers import build_document


detector = ChangeDetector()
values = ValueExtractor()
entities = EntityService()
explainer = ExplanationService()


def _signals(old, new):
    all_sentences = [*old.sentences, *new.sentences]
    return {
        "values": {s.id: values.extract_values(s.text) for s in all_sentences},
        "dates": {s.id: values.extract_dates(s.text) for s in all_sentences},
        "entities": {s.id: entities.extract(s.text) for s in all_sentences},
        "nli_results": {},
    }


def _matched(old_id: str, new_id: str, similarity: float = 0.93) -> AlignmentResult:
    return AlignmentResult(
        pairs=[
            AlignmentPair(
                status=AlignmentStatus.MATCHED,
                old_sentence_id=old_id,
                new_sentence_id=new_id,
                similarity=similarity,
                confidence=0.9,
            )
        ]
    )


def _detect(old_text: str, new_text: str, similarity: float = 0.93):
    old = build_document([old_text], filename="old.txt")
    new = build_document([new_text], filename="new.txt")
    changes = detector.detect(
        old,
        new,
        _matched(old.sentences[0].id, new.sentences[0].id, similarity),
        **_signals(old, new),
    )
    explainer.explain_all(changes)
    return changes[0]


def test_unchanged_paraphrase() -> None:
    change = _detect(
        "The company employs 500 people.",
        "The company has 500 employees.",
        similarity=0.91,
    )
    assert change.type == ChangeType.UNCHANGED


def test_addition_and_deletion() -> None:
    old = build_document(["Keep this."], filename="old.txt")
    new = build_document(["A brand new sentence."], filename="new.txt")
    alignment = AlignmentResult(
        pairs=[
            AlignmentPair(status=AlignmentStatus.DELETED, old_sentence_id=old.sentences[0].id),
            AlignmentPair(status=AlignmentStatus.ADDED, new_sentence_id=new.sentences[0].id),
        ]
    )
    changes = detector.detect(old, new, alignment, **_signals(old, new))
    types = {item.type for item in changes}
    assert types == {ChangeType.ADDITION, ChangeType.DELETION}


def test_modification() -> None:
    change = _detect(
        "The roadmap focuses on reliability.",
        "The roadmap focuses on rapid international expansion.",
        similarity=0.72,
    )
    assert change.type == ChangeType.MODIFICATION


def test_numerical_change() -> None:
    change = _detect("Revenue was $10 million.", "Revenue was $15 million.")
    assert change.type == ChangeType.NUMERICAL_CHANGE
    assert change.details["old_value"] == 10_000_000
    assert change.details["new_value"] == 15_000_000
    assert change.details["percentage_change"] == 50.0
    assert "50" in change.explanation


def test_temporal_change() -> None:
    change = _detect(
        "The project deadline is March 15, 2026.",
        "The project deadline is April 30, 2026.",
    )
    assert change.type == ChangeType.TEMPORAL_CHANGE
    assert change.details["old_date"] == "2026-03-15"
    assert change.details["new_date"] == "2026-04-30"
    assert change.details["days_changed"] == 46
    assert "46 days" in change.explanation


def test_entity_change() -> None:
    change = _detect(
        "The organization partnered with Microsoft.",
        "The organization partnered with Google.",
    )
    assert change.type == ChangeType.ENTITY_CHANGE
    assert "Microsoft" in (change.details.get("old_entity") or "")
    assert "Google" in (change.details.get("new_entity") or "")


def test_contradiction() -> None:
    change = _detect(
        "The office is open on weekends.",
        "The office is closed on weekends.",
        similarity=0.86,
    )
    assert change.type == ChangeType.CONTRADICTION
    assert "contradict" in change.explanation.lower()


def test_refinement() -> None:
    change = _detect(
        "The company operates in India.",
        "The company operates in India and Singapore.",
        similarity=0.84,
    )
    assert change.type == ChangeType.REFINEMENT
