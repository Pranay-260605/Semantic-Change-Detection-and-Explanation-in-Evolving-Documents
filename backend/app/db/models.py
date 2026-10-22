"""SQLAlchemy tables for documents, comparisons, and changes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    stored_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    structure_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    old_comparisons: Mapped[list["ComparisonRecord"]] = relationship(
        back_populates="old_document",
        foreign_keys="ComparisonRecord.old_document_id",
    )
    new_comparisons: Mapped[list["ComparisonRecord"]] = relationship(
        back_populates="new_document",
        foreign_keys="ComparisonRecord.new_document_id",
    )


class ComparisonRecord(Base):
    __tablename__ = "comparisons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    old_document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    new_document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    alignment_stats_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    old_document: Mapped[DocumentRecord] = relationship(
        foreign_keys=[old_document_id],
        back_populates="old_comparisons",
    )
    new_document: Mapped[DocumentRecord] = relationship(
        foreign_keys=[new_document_id],
        back_populates="new_comparisons",
    )
    changes: Mapped[list["ChangeRecord"]] = relationship(
        back_populates="comparison",
        cascade="all, delete-orphan",
    )


class ChangeRecord(Base):
    __tablename__ = "changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    comparison_id: Mapped[str] = mapped_column(ForeignKey("comparisons.id"), nullable=False)
    change_type: Mapped[str] = mapped_column(String(32), nullable=False)
    old_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    old_sentence_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_sentence_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    old_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_section: Mapped[str | None] = mapped_column(String(512), nullable=True)
    new_section: Mapped[str | None] = mapped_column(String(512), nullable=True)
    similarity: Mapped[float | None] = mapped_column(nullable=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    explanation: Mapped[str] = mapped_column(Text, default="")
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    comparison: Mapped[ComparisonRecord] = relationship(back_populates="changes")
