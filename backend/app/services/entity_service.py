"""Named entity extraction with optional spaCy NER and a gazetteer fallback."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.services.value_extractor import ValueExtractor

logger = get_logger(__name__)

TARGET_LABELS = {
    "PERSON",
    "ORG",
    "GPE",
    "LOC",
    "DATE",
    "MONEY",
    "PERCENT",
    "CARDINAL",
    "QUANTITY",
}

KNOWN_ORGS = {
    "microsoft",
    "google",
    "apple",
    "amazon",
    "meta",
    "facebook",
    "tesla",
    "ibm",
    "oracle",
    "infosys",
    "tcs",
    "wipro",
    "accenture",
    "netflix",
    "openai",
}

KNOWN_GPE = {
    "india",
    "singapore",
    "delhi",
    "new delhi",
    "bangalore",
    "bengaluru",
    "mumbai",
    "hyderabad",
    "chennai",
    "pune",
    "kolkata",
    "united states",
    "usa",
    "uk",
    "london",
    "new york",
    "california",
    "china",
    "japan",
}

ORG_SUFFIX_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*)*)\s+"
    r"(Inc|Incorporated|Ltd|Limited|LLC|Corp|Corporation|Company|Co|GmbH|Pvt|Private)\b"
)
PERSON_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")


@dataclass
class ExtractedEntity:
    text: str
    label: str
    normalized: str
    start: int = 0
    end: int = 0


class EntityService:
    """Extract entities. NER upgrades independently of sentence segmentation."""

    _nlp = None
    _nlp_name: str | None = None
    _load_attempted = False

    def __init__(
        self,
        settings: Settings | None = None,
        value_extractor: ValueExtractor | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.value_extractor = value_extractor or ValueExtractor()

    def extract(self, text: str) -> list[ExtractedEntity]:
        entities = self._extract_spacy(text)
        if not entities:
            entities = self._extract_fallback(text)
        else:
            entities.extend(self._extract_fallback(text, only_missing=True, existing=entities))
        return _dedupe(entities)

    def _ensure_nlp(self):
        if EntityService._load_attempted:
            return EntityService._nlp
        EntityService._load_attempted = True
        name = self.settings.ner_model
        try:
            import spacy

            EntityService._nlp = spacy.load(name)
            EntityService._nlp_name = name
            logger.info("Loaded spaCy NER model name=%s", name)
        except Exception:
            EntityService._nlp = None
            EntityService._nlp_name = name
            logger.warning("spaCy NER model unavailable name=%s; using fallback extractor", name)
        return EntityService._nlp

    def _extract_spacy(self, text: str) -> list[ExtractedEntity]:
        nlp = self._ensure_nlp()
        if nlp is None:
            return []
        try:
            doc = nlp(text)
        except Exception:
            logger.warning("spaCy NER failed; falling back")
            return []
        entities: list[ExtractedEntity] = []
        for ent in doc.ents:
            label = ent.label_
            if label not in TARGET_LABELS:
                continue
            entities.append(
                ExtractedEntity(
                    text=ent.text,
                    label=label,
                    normalized=_normalize(ent.text, label),
                    start=ent.start_char,
                    end=ent.end_char,
                )
            )
        return entities

    def _extract_fallback(
        self,
        text: str,
        *,
        only_missing: bool = False,
        existing: list[ExtractedEntity] | None = None,
    ) -> list[ExtractedEntity]:
        entities: list[ExtractedEntity] = []
        occupied = [(item.start, item.end) for item in existing or []]

        lower = text.lower()
        for name in sorted(KNOWN_ORGS, key=len, reverse=True):
            for match in re.finditer(rf"\b{re.escape(name)}\b", lower):
                if _span_overlaps(match.start(), match.end(), occupied):
                    continue
                surface = text[match.start() : match.end()]
                entities.append(ExtractedEntity(surface, "ORG", name, match.start(), match.end()))
                occupied.append((match.start(), match.end()))

        for name in sorted(KNOWN_GPE, key=len, reverse=True):
            for match in re.finditer(rf"\b{re.escape(name)}\b", lower):
                if _span_overlaps(match.start(), match.end(), occupied):
                    continue
                surface = text[match.start() : match.end()]
                entities.append(ExtractedEntity(surface, "GPE", name, match.start(), match.end()))
                occupied.append((match.start(), match.end()))

        if only_missing:
            return entities

        for match in ORG_SUFFIX_RE.finditer(text):
            if _span_overlaps(match.start(), match.end(), occupied):
                continue
            surface = match.group(0)
            entities.append(
                ExtractedEntity(surface, "ORG", _normalize(surface, "ORG"), match.start(), match.end())
            )
            occupied.append((match.start(), match.end()))

        for value in self.value_extractor.extract_dates(text):
            if _span_overlaps(value.start, value.end, occupied):
                continue
            entities.append(
                ExtractedEntity(value.raw_text, "DATE", value.iso_date or value.raw_text.lower(), value.start, value.end)
            )
            occupied.append((value.start, value.end))

        for value in self.value_extractor.extract_values(text):
            if _span_overlaps(value.start, value.end, occupied):
                continue
            if value.percentage:
                label = "PERCENT"
            elif value.currency:
                label = "MONEY"
            elif value.unit:
                label = "QUANTITY"
            else:
                label = "CARDINAL"
            entities.append(
                ExtractedEntity(
                    value.raw_text,
                    label,
                    str(value.normalized_value if value.normalized_value is not None else value.raw_text),
                    value.start,
                    value.end,
                )
            )
            occupied.append((value.start, value.end))

        for match in PERSON_RE.finditer(text):
            if _span_overlaps(match.start(), match.end(), occupied):
                continue
            surface = match.group(1)
            if surface.lower() in KNOWN_GPE or surface.lower() in KNOWN_ORGS:
                continue
            entities.append(
                ExtractedEntity(surface, "PERSON", surface.lower(), match.start(), match.end())
            )
        return entities


def compare_entities(
    old_entities: list[ExtractedEntity],
    new_entities: list[ExtractedEntity],
) -> list[dict]:
    """Return substitutions for important entity types."""
    important = {"PERSON", "ORG", "GPE", "LOC"}
    changes: list[dict] = []
    for label in important:
        old_set = {item.normalized for item in old_entities if item.label == label}
        new_set = {item.normalized for item in new_entities if item.label == label}
        removed = old_set - new_set
        added = new_set - old_set
        if removed and added:
            old_surface = next(item.text for item in old_entities if item.label == label and item.normalized in removed)
            new_surface = next(item.text for item in new_entities if item.label == label and item.normalized in added)
            changes.append(
                {
                    "label": label,
                    "old_entity": old_surface,
                    "new_entity": new_surface,
                    "old_normalized": sorted(removed),
                    "new_normalized": sorted(added),
                }
            )
    return changes


def entity_subset_extension(
    old_entities: list[ExtractedEntity],
    new_entities: list[ExtractedEntity],
) -> bool:
    """True when new entities contain all old important entities plus extras."""
    important = {"PERSON", "ORG", "GPE", "LOC"}
    old_set = {(item.label, item.normalized) for item in old_entities if item.label in important}
    new_set = {(item.label, item.normalized) for item in new_entities if item.label in important}
    return bool(old_set) and old_set.issubset(new_set) and new_set != old_set


def _normalize(text: str, label: str) -> str:
    cleaned = " ".join(text.strip().lower().split())
    cleaned = re.sub(r"\b(inc|ltd|llc|corp|corporation|company|co|pvt|private)\b\.?", "", cleaned)
    return " ".join(cleaned.split())


def _span_overlaps(start: int, end: int, occupied: list[tuple[int, int]]) -> bool:
    for left, right in occupied:
        if start < right and end > left:
            return True
    return False


def _dedupe(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    seen: set[tuple[str, str, int, int]] = set()
    unique: list[ExtractedEntity] = []
    for item in entities:
        key = (item.label, item.normalized, item.start, item.end)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
