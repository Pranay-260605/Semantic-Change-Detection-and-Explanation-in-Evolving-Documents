"""Persistence helpers for documents and comparisons."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ChangeRecord, ComparisonRecord, DocumentRecord
from app.models.change import Change
from app.models.comparison import ComparisonResult, ComparisonStatus
from app.models.document import Document, Paragraph, Section, Sentence


def serialize_document(document: Document) -> dict:
    """Serialize a domain document for JSON storage (no embeddings)."""
    return {
        "id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "total_pages": document.total_pages,
        "stored_path": document.stored_path,
        "sections": [
            {"id": section.id, "title": section.title, "paragraph_ids": section.paragraph_ids}
            for section in document.sections
        ],
        "paragraphs": [
            {
                "id": paragraph.id,
                "text": paragraph.text,
                "section_id": paragraph.section_id,
                "section_title": paragraph.section_title,
                "page_number": paragraph.page_number,
                "sentence_ids": paragraph.sentence_ids,
            }
            for paragraph in document.paragraphs
        ],
        "sentences": [
            {
                "id": sentence.id,
                "text": sentence.text,
                "section_id": sentence.section_id,
                "section_title": sentence.section_title,
                "paragraph_id": sentence.paragraph_id,
                "page_number": sentence.page_number,
                "start_char": sentence.start_char,
                "end_char": sentence.end_char,
            }
            for sentence in document.sentences
        ],
    }


def deserialize_document(payload: dict) -> Document:
    """Rebuild a domain document from stored JSON."""
    return Document(
        id=payload["id"],
        filename=payload["filename"],
        file_type=payload["file_type"],
        total_pages=payload.get("total_pages", 0),
        stored_path=payload.get("stored_path"),
        sections=[
            Section(
                id=item["id"],
                title=item["title"],
                paragraph_ids=list(item.get("paragraph_ids") or []),
            )
            for item in payload.get("sections") or []
        ],
        paragraphs=[
            Paragraph(
                id=item["id"],
                text=item["text"],
                section_id=item.get("section_id"),
                section_title=item.get("section_title"),
                page_number=item.get("page_number"),
                sentence_ids=list(item.get("sentence_ids") or []),
            )
            for item in payload.get("paragraphs") or []
        ],
        sentences=[
            Sentence(
                id=item["id"],
                text=item["text"],
                section_id=item.get("section_id"),
                section_title=item.get("section_title"),
                paragraph_id=item.get("paragraph_id"),
                page_number=item.get("page_number"),
                start_char=item.get("start_char"),
                end_char=item.get("end_char"),
            )
            for item in payload.get("sentences") or []
        ],
    )


def save_document(db: Session, document: Document) -> DocumentRecord:
    """Insert or replace a parsed document record."""
    record = db.get(DocumentRecord, document.id)
    if record is None:
        record = DocumentRecord(id=document.id)
        db.add(record)
    record.filename = document.filename
    record.file_type = document.file_type
    record.total_pages = document.total_pages
    record.stored_path = document.stored_path
    record.structure_json = serialize_document(document)
    record.created_at = record.created_at or datetime.utcnow()
    db.flush()
    return record


def save_comparison(db: Session, result: ComparisonResult) -> ComparisonRecord:
    """Persist a completed comparison and its changes."""
    save_document(db, result.old_document)
    save_document(db, result.new_document)

    record = db.get(ComparisonRecord, result.comparison_id)
    if record is None:
        record = ComparisonRecord(id=result.comparison_id)
        db.add(record)

    record.old_document_id = result.old_document.id
    record.new_document_id = result.new_document.id
    record.status = result.status.value
    record.summary_json = {
        "total_changes": result.summary.total_changes,
        "additions": result.summary.additions,
        "deletions": result.summary.deletions,
        "modifications": result.summary.modifications,
        "numerical_changes": result.summary.numerical_changes,
        "temporal_changes": result.summary.temporal_changes,
        "entity_changes": result.summary.entity_changes,
        "contradictions": result.summary.contradictions,
        "refinements": result.summary.refinements,
        "unchanged": result.summary.unchanged,
    }
    record.alignment_stats_json = result.alignment_stats
    record.created_at = result.created_at
    record.error_message = None

    record.changes.clear()
    db.flush()
    for change in result.changes:
        record.changes.append(
            ChangeRecord(
                id=change.id,
                comparison_id=result.comparison_id,
                change_type=change.type.value,
                old_text=change.old_text,
                new_text=change.new_text,
                old_sentence_id=change.old_sentence_id,
                new_sentence_id=change.new_sentence_id,
                old_page=change.old_page,
                new_page=change.new_page,
                old_section=change.old_section,
                new_section=change.new_section,
                similarity=change.similarity,
                confidence=change.confidence,
                explanation=change.explanation,
                details_json=change.details,
            )
        )
    db.flush()
    return record


def mark_comparison_failed(db: Session, comparison_id: str, message: str) -> None:
    """Persist a failed comparison status when possible."""
    record = db.get(ComparisonRecord, comparison_id)
    if record is None:
        return
    record.status = ComparisonStatus.FAILED.value
    record.error_message = message
    db.flush()


def get_comparison(db: Session, comparison_id: str) -> ComparisonRecord | None:
    statement = (
        select(ComparisonRecord)
        .options(
            selectinload(ComparisonRecord.changes),
            selectinload(ComparisonRecord.old_document),
            selectinload(ComparisonRecord.new_document),
        )
        .where(ComparisonRecord.id == comparison_id)
    )
    return db.execute(statement).scalar_one_or_none()


def list_comparisons(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[ComparisonRecord]:
    """Return recent comparisons with document metadata loaded."""
    statement = (
        select(ComparisonRecord)
        .options(
            selectinload(ComparisonRecord.old_document),
            selectinload(ComparisonRecord.new_document),
        )
        .order_by(desc(ComparisonRecord.created_at))
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(statement).scalars().all())
