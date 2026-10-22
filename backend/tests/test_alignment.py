import numpy as np

from app.models.comparison import AlignmentStatus
from app.models.document import Sentence
from app.services.alignment_service import AlignmentService


def sentences(texts: list[str], section: str | None = None) -> list[Sentence]:
    return [
        Sentence(
            id=f"s-{index:04d}",
            text=text,
            section_id=section,
            section_title=section,
            paragraph_id=f"p-{index:04d}",
            page_number=1,
        )
        for index, text in enumerate(texts, start=1)
    ]


def test_identical_sentences_match() -> None:
    old = sentences(["Alpha.", "Beta."])
    new = sentences(["Alpha.", "Beta."])
    matrix = np.eye(2, dtype=np.float32)
    result = AlignmentService().align(old, new, matrix)
    matched = result.matched()
    assert len(matched) == 2
    assert {pair.old_sentence_id for pair in matched} == {"s-0001", "s-0002"}
    assert not result.added()
    assert not result.deleted()


def test_reordered_sentences_still_match() -> None:
    old = sentences(["Alpha.", "Beta."])
    new = sentences(["Beta.", "Alpha."])
    matrix = np.array([[0.1, 0.99], [0.98, 0.1]], dtype=np.float32)
    result = AlignmentService().align(old, new, matrix)
    matched = {(pair.old_sentence_id, pair.new_sentence_id) for pair in result.matched()}
    assert matched == {("s-0001", "s-0002"), ("s-0002", "s-0001")}


def test_one_to_one_constraint_avoids_duplicate_targets() -> None:
    old = sentences(["The cat sat.", "The cat sat down."])
    new = sentences(["The cat sat on the mat."])
    matrix = np.array([[0.91], [0.92]], dtype=np.float32)
    result = AlignmentService().align(old, new, matrix)
    assert len(result.matched()) == 1
    assert len(result.deleted()) == 1
    assert result.matched()[0].new_sentence_id == "s-0001"


def test_additions_and_deletions() -> None:
    old = sentences(["Keep me.", "Delete me."])
    new = sentences(["Keep me.", "I am new."])
    matrix = np.array([[0.99, 0.1], [0.2, 0.15]], dtype=np.float32)
    result = AlignmentService().align(old, new, matrix)
    assert len(result.matched()) == 1
    assert result.matched()[0].old_sentence_id == "s-0001"
    assert result.deleted()[0].old_sentence_id == "s-0002"
    assert result.added()[0].new_sentence_id == "s-0002"


def test_paraphrase_alignment_uses_similarity_not_exact_text() -> None:
    old = sentences(["The company employs 500 people."])
    new = sentences(["The company has 500 employees."])
    matrix = np.array([[0.88]], dtype=np.float32)
    result = AlignmentService().align(old, new, matrix)
    assert result.matched()[0].status == AlignmentStatus.MATCHED
    assert result.matched()[0].similarity == 0.88


def test_section_aware_matching_prefers_same_section() -> None:
    old = [
        Sentence(id="o1", text="Same words.", section_id="finance", page_number=1),
        Sentence(id="o2", text="Same words.", section_id="legal", page_number=2),
    ]
    new = [
        Sentence(id="n1", text="Same words.", section_id="legal", page_number=2),
        Sentence(id="n2", text="Same words.", section_id="finance", page_number=1),
    ]
    matrix = np.array([[0.95, 0.95], [0.95, 0.95]], dtype=np.float32)
    result = AlignmentService().align(old, new, matrix)
    matched = {(pair.old_sentence_id, pair.new_sentence_id) for pair in result.matched()}
    assert ("o1", "n2") in matched
    assert ("o2", "n1") in matched
