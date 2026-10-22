"""Deterministic change classification from alignment and extracted signals."""

from __future__ import annotations

import re
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.models.change import Change, ChangeType
from app.models.comparison import AlignmentPair, AlignmentResult, AlignmentStatus
from app.models.document import Document, Sentence
from app.services.entity_service import (
    ExtractedEntity,
    compare_entities,
    entity_subset_extension,
)
from app.services.nli_service import NLIResult
from app.services.value_extractor import DateDelta, ExtractedDate, ExtractedValue, ValueDelta

ANTONYM_PAIRS = (
    ("open", "closed"),
    ("available", "unavailable"),
    ("allowed", "forbidden"),
    ("allowed", "prohibited"),
    ("true", "false"),
    ("included", "excluded"),
    ("include", "exclude"),
    ("enabled", "disabled"),
    ("enable", "disable"),
    ("success", "failure"),
    ("active", "inactive"),
    ("present", "absent"),
    ("mandatory", "optional"),
    ("always", "never"),
)

NEGATION_RE = re.compile(
    r"\b(?:not|never|no|cannot|can't|won't|isn't|aren't|wasn't|weren't|n't)\b",
    re.IGNORECASE,
)


class ChangeDetector:
    """Central reasoning layer that turns pipeline evidence into Change objects."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def detect(
        self,
        old_document: Document,
        new_document: Document,
        alignment: AlignmentResult,
        *,
        values: dict[str, list[ExtractedValue]],
        dates: dict[str, list[ExtractedDate]],
        entities: dict[str, list[ExtractedEntity]],
        nli_results: dict[tuple[str, str], NLIResult],
    ) -> list[Change]:
        old_by_id = {sentence.id: sentence for sentence in old_document.sentences}
        new_by_id = {sentence.id: sentence for sentence in new_document.sentences}
        changes: list[Change] = []

        for pair in alignment.pairs:
            if pair.status == AlignmentStatus.ADDED:
                sentence = new_by_id[pair.new_sentence_id]  # type: ignore[index]
                changes.append(
                    self._simple_change(
                        ChangeType.ADDITION,
                        new_sentence=sentence,
                        confidence=pair.confidence or 0.9,
                    )
                )
            elif pair.status == AlignmentStatus.DELETED:
                sentence = old_by_id[pair.old_sentence_id]  # type: ignore[index]
                changes.append(
                    self._simple_change(
                        ChangeType.DELETION,
                        old_sentence=sentence,
                        confidence=pair.confidence or 0.9,
                    )
                )
            else:
                old_sentence = old_by_id[pair.old_sentence_id]  # type: ignore[index]
                new_sentence = new_by_id[pair.new_sentence_id]  # type: ignore[index]
                changes.append(
                    self._classify_match(
                        pair,
                        old_sentence,
                        new_sentence,
                        old_values=values.get(old_sentence.id, []),
                        new_values=values.get(new_sentence.id, []),
                        old_dates=dates.get(old_sentence.id, []),
                        new_dates=dates.get(new_sentence.id, []),
                        old_entities=entities.get(old_sentence.id, []),
                        new_entities=entities.get(new_sentence.id, []),
                        nli=nli_results.get((old_sentence.id, new_sentence.id)),
                    )
                )
        return changes

    def should_run_nli(
        self,
        old_sentence: Sentence,
        new_sentence: Sentence,
        similarity: float | None,
        old_values: list[ExtractedValue],
        new_values: list[ExtractedValue],
        old_dates: list[ExtractedDate],
        new_dates: list[ExtractedDate],
        value_deltas: list[ValueDelta],
        date_deltas: list[DateDelta],
        entity_changes: list[dict],
    ) -> bool:
        if _normalize_text(old_sentence.text) == _normalize_text(new_sentence.text):
            return False
        if (similarity or 0) >= 0.95 and not value_deltas and not date_deltas and not entity_changes:
            return False
        return True

    def _classify_match(
        self,
        pair: AlignmentPair,
        old_sentence: Sentence,
        new_sentence: Sentence,
        *,
        old_values: list[ExtractedValue],
        new_values: list[ExtractedValue],
        old_dates: list[ExtractedDate],
        new_dates: list[ExtractedDate],
        old_entities: list[ExtractedEntity],
        new_entities: list[ExtractedEntity],
        nli: NLIResult | None,
    ) -> Change:
        from app.services.value_extractor import ValueExtractor

        extractor = ValueExtractor()
        value_deltas = extractor.compare_values(old_values, new_values)
        date_deltas = extractor.compare_dates(old_dates, new_dates)
        entity_changes = compare_entities(old_entities, new_entities)
        similarity = pair.similarity or 0.0
        details: dict = {"alignment_confidence": pair.confidence}

        if _normalize_text(old_sentence.text) == _normalize_text(new_sentence.text):
            return self._matched_change(
                ChangeType.UNCHANGED,
                old_sentence,
                new_sentence,
                similarity,
                0.99,
                details,
            )

        if value_deltas:
            delta = value_deltas[0]
            details.update(
                _value_details(delta, old_sentence.text, new_sentence.text)
            )
            return self._matched_change(
                ChangeType.NUMERICAL_CHANGE,
                old_sentence,
                new_sentence,
                similarity,
                min(0.99, 0.75 + similarity * 0.2),
                details,
            )

        if date_deltas:
            delta = date_deltas[0]
            details.update(
                {
                    "old_date": delta.old.iso_date,
                    "new_date": delta.new.iso_date,
                    "days_changed": delta.days_changed,
                    "old_date_raw": delta.old.raw_text,
                    "new_date_raw": delta.new.raw_text,
                }
            )
            return self._matched_change(
                ChangeType.TEMPORAL_CHANGE,
                old_sentence,
                new_sentence,
                similarity,
                min(0.99, 0.78 + similarity * 0.2),
                details,
            )

        if entity_changes and not entity_subset_extension(old_entities, new_entities):
            change = entity_changes[0]
            details.update(change)
            details["entity"] = change.get("new_entity") or change.get("old_entity")
            return self._matched_change(
                ChangeType.ENTITY_CHANGE,
                old_sentence,
                new_sentence,
                similarity,
                min(0.98, 0.74 + similarity * 0.2),
                details,
            )

        contradiction = _contradiction_signal(
            old_sentence.text,
            new_sentence.text,
            nli,
            self.settings.nli_contradiction_threshold,
        )
        if contradiction:
            details.update(contradiction)
            return self._matched_change(
                ChangeType.CONTRADICTION,
                old_sentence,
                new_sentence,
                similarity,
                float(contradiction.get("confidence", 0.85)),
                details,
            )

        if _is_refinement(
            old_sentence,
            new_sentence,
            old_entities,
            new_entities,
            nli,
            self.settings.nli_entailment_threshold,
        ):
            details["reason"] = "new_sentence_adds_compatible_information"
            return self._matched_change(
                ChangeType.REFINEMENT,
                old_sentence,
                new_sentence,
                similarity,
                min(0.96, 0.7 + similarity * 0.25),
                details,
            )

        if _values_consistent(old_values, new_values) and not entity_changes:
            if similarity >= self.settings.unchanged_similarity_threshold:
                return self._matched_change(
                    ChangeType.UNCHANGED,
                    old_sentence,
                    new_sentence,
                    similarity,
                    similarity,
                    details,
                )
            if similarity >= self.settings.paraphrase_threshold:
                return self._matched_change(
                    ChangeType.UNCHANGED,
                    old_sentence,
                    new_sentence,
                    similarity,
                    similarity,
                    details,
                )

        return self._matched_change(
            ChangeType.MODIFICATION,
            old_sentence,
            new_sentence,
            similarity,
            max(0.55, similarity),
            details,
        )

    def _simple_change(
        self,
        change_type: ChangeType,
        *,
        old_sentence: Sentence | None = None,
        new_sentence: Sentence | None = None,
        confidence: float,
    ) -> Change:
        return Change(
            id=str(uuid4()),
            type=change_type,
            old_text=old_sentence.text if old_sentence else None,
            new_text=new_sentence.text if new_sentence else None,
            old_sentence_id=old_sentence.id if old_sentence else None,
            new_sentence_id=new_sentence.id if new_sentence else None,
            old_page=old_sentence.page_number if old_sentence else None,
            new_page=new_sentence.page_number if new_sentence else None,
            old_section=old_sentence.section_title if old_sentence else None,
            new_section=new_sentence.section_title if new_sentence else None,
            similarity=None,
            confidence=round(confidence, 4),
            details={},
        )

    def _matched_change(
        self,
        change_type: ChangeType,
        old_sentence: Sentence,
        new_sentence: Sentence,
        similarity: float,
        confidence: float,
        details: dict,
    ) -> Change:
        return Change(
            id=str(uuid4()),
            type=change_type,
            old_text=old_sentence.text,
            new_text=new_sentence.text,
            old_sentence_id=old_sentence.id,
            new_sentence_id=new_sentence.id,
            old_page=old_sentence.page_number,
            new_page=new_sentence.page_number,
            old_section=old_sentence.section_title,
            new_section=new_sentence.section_title,
            similarity=round(similarity, 4),
            confidence=round(min(confidence, 0.99), 4),
            details=details,
        )


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def _values_consistent(old_values: list[ExtractedValue], new_values: list[ExtractedValue]) -> bool:
    if not old_values or not new_values:
        return True
    old_norms = [item.normalized_value for item in old_values if item.normalized_value is not None]
    new_norms = [item.normalized_value for item in new_values if item.normalized_value is not None]
    if not old_norms or not new_norms:
        return True
    for old in old_norms:
        if any(abs(old - new) < 1e-6 for new in new_norms):
            return True
    return False


def _value_details(
    delta: ValueDelta,
    old_text: str,
    new_text: str,
) -> dict:
    entity = _guess_topic(old_text, delta.old.start) or _guess_topic(new_text, delta.new.start)
    return {
        "entity": entity,
        "old_value": delta.old.normalized_value,
        "new_value": delta.new.normalized_value,
        "old_raw": delta.old.raw_text,
        "new_raw": delta.new.raw_text,
        "unit": delta.new.unit or delta.old.unit,
        "currency": delta.new.currency or delta.old.currency,
        "percentage": delta.old.percentage or delta.new.percentage,
        "absolute_change": delta.absolute_change,
        "percentage_change": delta.percentage_change,
    }


def _guess_topic(text: str, value_start: int) -> str | None:
    prefix = text[:value_start]
    words = re.findall(r"[A-Za-z][A-Za-z\-]+", prefix)
    stop = {
        "the",
        "a",
        "an",
        "was",
        "were",
        "is",
        "are",
        "to",
        "from",
        "of",
        "and",
        "in",
        "for",
        "with",
        "by",
    }
    content = [word for word in words if word.lower() not in stop]
    if not content:
        return None
    return content[-1]


def _contradiction_signal(
    old_text: str,
    new_text: str,
    nli: NLIResult | None,
    threshold: float,
) -> dict | None:
    if nli and nli.label == "CONTRADICTION" and nli.confidence >= threshold:
        return {
            "nli_label": nli.label,
            "nli_confidence": nli.confidence,
            "confidence": nli.confidence,
            "source": "nli",
        }
    old_tokens = set(re.findall(r"[a-z']+", old_text.lower()))
    new_tokens = set(re.findall(r"[a-z']+", new_text.lower()))
    for left, right in ANTONYM_PAIRS:
        if (left in old_tokens and right in new_tokens) or (right in old_tokens and left in new_tokens):
            return {
                "antonyms": [left, right],
                "confidence": 0.92,
                "source": "antonym_heuristic",
            }
    old_neg = bool(NEGATION_RE.search(old_text))
    new_neg = bool(NEGATION_RE.search(new_text))
    if old_neg != new_neg:
        overlap = old_tokens & new_tokens
        if len(overlap) >= 3:
            return {
                "confidence": 0.8,
                "source": "negation_heuristic",
            }
    return None


def _is_refinement(
    old_sentence: Sentence,
    new_sentence: Sentence,
    old_entities: list[ExtractedEntity],
    new_entities: list[ExtractedEntity],
    nli: NLIResult | None,
    entailment_threshold: float,
) -> bool:
    old_len = len(old_sentence.text)
    new_len = len(new_sentence.text)
    extra_length = new_len > old_len * 1.05 and new_len - old_len >= 8
    extra_entities = entity_subset_extension(old_entities, new_entities)
    nli_compatible = True
    if nli and nli.label == "CONTRADICTION":
        nli_compatible = False
    new_entails_old = False
    if nli and nli.label == "ENTAILMENT" and nli.confidence >= entailment_threshold:
        new_entails_old = True
    old_norm = _normalize_text(old_sentence.text).rstrip(".")
    new_norm = _normalize_text(new_sentence.text)
    contains_old = old_norm in new_norm
    return nli_compatible and extra_length and (extra_entities or contains_old or new_entails_old)
