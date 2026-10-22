"""Sentence segmentation that preserves document structure."""

from __future__ import annotations

import re

import spacy
from spacy.language import Language

from app.core.logging import get_logger
from app.models.document import Document, Sentence

logger = get_logger(__name__)

# Protect common abbreviations so the rule-based sentencizer does not split them.
_ABBREVIATION_RE = re.compile(
    r"\b("
    r"Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|Inc|Ltd|Co|No|Nos|Fig|Eq|al|cf|viz|"
    r"e\.g|i\.e|U\.S|U\.K|Dept|approx|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    r")\.",
    re.IGNORECASE,
)
_PLACEHOLDER = "<ABB_DOT>"


class TextProcessor:
    """Split paragraphs into sentences using spaCy's rule-based sentencizer."""

    def __init__(self, nlp: Language | None = None) -> None:
        if nlp is None:
            nlp = spacy.blank("en")
            if "sentencizer" not in nlp.pipe_names:
                nlp.add_pipe("sentencizer")
            nlp.max_length = 5_000_000
        self.nlp = nlp

    def process(self, document: Document) -> Document:
        """Populate `document.sentences` and paragraph sentence ids in place."""
        sentences: list[Sentence] = []
        sentence_index = 0

        for paragraph in document.paragraphs:
            paragraph.sentence_ids = []
            try:
                pieces = self._split_sentences(paragraph.text)
            except Exception:
                logger.warning("Sentence split failed for paragraph_id=%s", paragraph.id)
                pieces = [(paragraph.text.strip(), 0, len(paragraph.text))] if paragraph.text.strip() else []

            for text, start_char, end_char in pieces:
                sentence_index += 1
                sentence_id = f"{document.id}-s-{sentence_index:04d}"
                sentences.append(
                    Sentence(
                        id=sentence_id,
                        text=text,
                        section_id=paragraph.section_id,
                        section_title=paragraph.section_title,
                        paragraph_id=paragraph.id,
                        page_number=paragraph.page_number,
                        start_char=start_char,
                        end_char=end_char,
                    )
                )
                paragraph.sentence_ids.append(sentence_id)

        document.sentences = sentences
        logger.info(
            "sentence segmentation complete paragraphs=%s sentences=%s",
            len(document.paragraphs),
            len(document.sentences),
        )
        return document

    def _split_sentences(self, text: str) -> list[tuple[str, int, int]]:
        if not text or not text.strip():
            return []

        protected = _ABBREVIATION_RE.sub(lambda match: f"{match.group(1)}{_PLACEHOLDER}", text)
        doc = self.nlp(protected)
        results: list[tuple[str, int, int]] = []

        for sent in doc.sents:
            raw = sent.text.replace(_PLACEHOLDER, ".")
            stripped = raw.strip()
            if not stripped:
                continue
            leading = len(raw) - len(raw.lstrip())
            start = sent.start_char + leading
            end = start + len(stripped)
            restored = stripped.replace(_PLACEHOLDER, ".")
            if not restored:
                continue
            results.append((restored, start, end))
        return results
