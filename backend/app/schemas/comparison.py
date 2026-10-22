"""Request and response models for document and comparison APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.change import Change, ChangeType
from app.models.comparison import ComparisonResult
from app.models.document import Document


class DocumentMeta(BaseModel):
    filename: str
    pages: int
    file_type: Optional[str] = None
    document_id: Optional[str] = None


class SentenceResponse(BaseModel):
    id: str
    text: str
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    paragraph_id: Optional[str] = None
    page_number: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class ParagraphResponse(BaseModel):
    id: str
    text: str
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    sentence_ids: list[str] = Field(default_factory=list)


class SectionResponse(BaseModel):
    id: str
    title: str
    paragraph_ids: list[str] = Field(default_factory=list)


class DocumentParseResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    pages: int
    paragraph_count: int
    sentence_count: int
    sections: list[SectionResponse]
    paragraphs: list[ParagraphResponse]
    sentences: list[SentenceResponse]


class ComparisonSummaryResponse(BaseModel):
    total_changes: int
    additions: int
    deletions: int
    modifications: int
    numerical_changes: int
    temporal_changes: int
    entity_changes: int
    contradictions: int
    refinements: int
    unchanged: int = 0


class ChangeResponse(BaseModel):
    id: str
    type: ChangeType
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    old_page: Optional[int] = None
    new_page: Optional[int] = None
    old_sentence_id: Optional[str] = None
    new_sentence_id: Optional[str] = None
    old_section: Optional[str] = None
    new_section: Optional[str] = None
    similarity: Optional[float] = None
    confidence: float
    explanation: str
    details: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_change(cls, change: Change) -> "ChangeResponse":
        return cls(
            id=change.id,
            type=change.type,
            old_text=change.old_text,
            new_text=change.new_text,
            old_page=change.old_page,
            new_page=change.new_page,
            old_sentence_id=change.old_sentence_id,
            new_sentence_id=change.new_sentence_id,
            old_section=change.old_section,
            new_section=change.new_section,
            similarity=change.similarity,
            confidence=change.confidence,
            explanation=change.explanation,
            details=change.details,
        )


class ComparisonResponse(BaseModel):
    comparison_id: str
    status: str
    created_at: datetime
    old_document: DocumentMeta
    new_document: DocumentMeta
    summary: ComparisonSummaryResponse
    changes: list[ChangeResponse]

    @classmethod
    def from_result(cls, result: ComparisonResult) -> "ComparisonResponse":
        return cls(
            comparison_id=result.comparison_id,
            status=result.status.value,
            created_at=result.created_at,
            old_document=_document_meta(result.old_document),
            new_document=_document_meta(result.new_document),
            summary=ComparisonSummaryResponse(
                total_changes=result.summary.total_changes,
                additions=result.summary.additions,
                deletions=result.summary.deletions,
                modifications=result.summary.modifications,
                numerical_changes=result.summary.numerical_changes,
                temporal_changes=result.summary.temporal_changes,
                entity_changes=result.summary.entity_changes,
                contradictions=result.summary.contradictions,
                refinements=result.summary.refinements,
                unchanged=result.summary.unchanged,
            ),
            changes=[ChangeResponse.from_change(change) for change in result.changes],
        )


class ComparisonHistoryItem(BaseModel):
    """Compact persisted comparison record for the history screen."""

    comparison_id: str
    status: str
    created_at: datetime
    old_document: DocumentMeta
    new_document: DocumentMeta
    summary: ComparisonSummaryResponse


class ComparisonHistoryResponse(BaseModel):
    """Paginated comparison history payload."""

    items: list[ComparisonHistoryItem]
    limit: int
    offset: int


def _document_meta(document: Document) -> DocumentMeta:
    return DocumentMeta(
        filename=document.filename,
        pages=document.total_pages,
        file_type=document.file_type,
        document_id=document.id,
    )


def document_to_parse_response(document: Document) -> DocumentParseResponse:
    return DocumentParseResponse(
        document_id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        pages=document.total_pages,
        paragraph_count=len(document.paragraphs),
        sentence_count=len(document.sentences),
        sections=[
            SectionResponse(
                id=section.id,
                title=section.title,
                paragraph_ids=section.paragraph_ids,
            )
            for section in document.sections
        ],
        paragraphs=[
            ParagraphResponse(
                id=paragraph.id,
                text=paragraph.text,
                section_id=paragraph.section_id,
                section_title=paragraph.section_title,
                page_number=paragraph.page_number,
                sentence_ids=paragraph.sentence_ids,
            )
            for paragraph in document.paragraphs
        ],
        sentences=[
            SentenceResponse(
                id=sentence.id,
                text=sentence.text,
                section_id=sentence.section_id,
                section_title=sentence.section_title,
                paragraph_id=sentence.paragraph_id,
                page_number=sentence.page_number,
                start_char=sentence.start_char,
                end_char=sentence.end_char,
            )
            for sentence in document.sentences
        ],
    )
