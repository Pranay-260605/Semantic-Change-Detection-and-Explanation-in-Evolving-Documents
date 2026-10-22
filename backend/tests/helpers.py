"""Shared test helpers."""

from __future__ import annotations

from pathlib import Path

from app.models.document import Document, Paragraph, Sentence
from app.services.document_parser import DocumentParser
from app.services.text_processor import TextProcessor


def build_document(texts: list[str], *, filename: str = "doc.txt") -> Document:
    paragraphs = [
        Paragraph(id=f"p-{index:04d}", text=text, page_number=1)
        for index, text in enumerate(texts, start=1)
    ]
    document = Document(
        id=filename,
        filename=filename,
        file_type="txt",
        total_pages=1,
        paragraphs=paragraphs,
    )
    return TextProcessor().process(document)


def parse_and_process(path: Path) -> Document:
    return TextProcessor().process(DocumentParser().parse(path))
