"""Canonical in-memory document structure used by the analysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Sentence:
    """A single sentence with provenance for highlighting and alignment."""

    id: str
    text: str
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    paragraph_id: Optional[str] = None
    page_number: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None


@dataclass
class Paragraph:
    """A paragraph of source text and the sentences derived from it."""

    id: str
    text: str
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    sentence_ids: list[str] = field(default_factory=list)


@dataclass
class Section:
    """A detected heading/section within a document."""

    id: str
    title: str
    paragraph_ids: list[str] = field(default_factory=list)


@dataclass
class Document:
    """Parsed document used throughout the comparison pipeline."""

    id: str
    filename: str
    file_type: str
    total_pages: int = 0
    sections: list[Section] = field(default_factory=list)
    paragraphs: list[Paragraph] = field(default_factory=list)
    sentences: list[Sentence] = field(default_factory=list)
    stored_path: Optional[str] = None

    def sentence_by_id(self, sentence_id: str) -> Optional[Sentence]:
        """Return a sentence by id, or None if it does not exist."""
        for sentence in self.sentences:
            if sentence.id == sentence_id:
                return sentence
        return None

    def paragraph_by_id(self, paragraph_id: str) -> Optional[Paragraph]:
        """Return a paragraph by id, or None if it does not exist."""
        for paragraph in self.paragraphs:
            if paragraph.id == paragraph_id:
                return paragraph
        return None
