"""Orchestrates the full semantic comparison pipeline."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ComparisonFailedError, ComparisonNotFoundError
from app.core.logging import get_logger
from app.db.models import ChangeRecord, ComparisonRecord
from app.db.repository import deserialize_document, get_comparison, save_comparison
from app.models.change import Change, ChangeType
from app.models.comparison import ComparisonResult, ComparisonStatus, ComparisonSummary
from app.models.document import Document
from app.services.alignment_service import AlignmentService
from app.services.change_detector import ChangeDetector
from app.services.document_parser import DocumentParser
from app.services.embedding_service import EmbeddingService
from app.services.entity_service import EntityService
from app.services.explanation_service import ExplanationService
from app.services.nli_service import NLIResult, NLIService
from app.services.text_processor import TextProcessor
from app.services.value_extractor import ValueExtractor

logger = get_logger(__name__)


class ComparisonService:
    """Parse, analyze, classify, explain, and persist document comparisons."""

    def __init__(
        self,
        settings: Settings | None = None,
        parser: DocumentParser | None = None,
        text_processor: TextProcessor | None = None,
        embedding_service: EmbeddingService | None = None,
        alignment_service: AlignmentService | None = None,
        entity_service: EntityService | None = None,
        value_extractor: ValueExtractor | None = None,
        nli_service: NLIService | None = None,
        change_detector: ChangeDetector | None = None,
        explanation_service: ExplanationService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.parser = parser or DocumentParser()
        self.text_processor = text_processor or TextProcessor()
        self.embedding_service = embedding_service or EmbeddingService(self.settings)
        self.alignment_service = alignment_service or AlignmentService(self.settings)
        self.value_extractor = value_extractor or ValueExtractor()
        self.entity_service = entity_service or EntityService(self.settings, self.value_extractor)
        self.nli_service = nli_service or NLIService(self.settings)
        self.change_detector = change_detector or ChangeDetector(self.settings)
        self.explanation_service = explanation_service or ExplanationService()

    def parse_document(
        self,
        file_path: str | Path,
        *,
        original_filename: str | None = None,
        document_id: str | None = None,
    ) -> Document:
        document = self.parser.parse(
            file_path,
            original_filename=original_filename,
            document_id=document_id,
        )
        return self.text_processor.process(document)

    def compare_files(
        self,
        old_path: str | Path,
        new_path: str | Path,
        *,
        old_filename: str | None = None,
        new_filename: str | None = None,
        db: Session | None = None,
    ) -> ComparisonResult:
        old_document = self.parse_document(old_path, original_filename=old_filename)
        new_document = self.parse_document(new_path, original_filename=new_filename)
        return self.compare_documents(old_document, new_document, db=db)

    def compare_documents(
        self,
        old_document: Document,
        new_document: Document,
        *,
        db: Session | None = None,
    ) -> ComparisonResult:
        comparison_id = str(uuid4())
        try:
            result = self._run_pipeline(comparison_id, old_document, new_document)
        except Exception:
            logger.exception("comparison failed comparison_id=%s", comparison_id)
            raise ComparisonFailedError() from None

        if db is not None:
            save_comparison(db, result)
            db.flush()
        logger.info(
            "comparison completion comparison_id=%s changes=%s",
            comparison_id,
            result.summary.total_changes,
        )
        return result

    def _run_pipeline(
        self,
        comparison_id: str,
        old_document: Document,
        new_document: Document,
    ) -> ComparisonResult:
        old_vectors = self.embedding_service.encode_sentences(old_document.sentences)
        new_vectors = self.embedding_service.encode_sentences(new_document.sentences)
        similarity_matrix = self.embedding_service.similarity_matrix(old_vectors, new_vectors)
        alignment = self.alignment_service.align(
            old_document.sentences,
            new_document.sentences,
            similarity_matrix,
        )

        values = {
            sentence.id: self.value_extractor.extract_values(sentence.text)
            for sentence in (*old_document.sentences, *new_document.sentences)
        }
        dates = {
            sentence.id: self.value_extractor.extract_dates(sentence.text)
            for sentence in (*old_document.sentences, *new_document.sentences)
        }
        entities = {
            sentence.id: self.entity_service.extract(sentence.text)
            for sentence in (*old_document.sentences, *new_document.sentences)
        }

        nli_results = self._run_nli(old_document, new_document, alignment, values, dates, entities)
        changes = self.change_detector.detect(
            old_document,
            new_document,
            alignment,
            values=values,
            dates=dates,
            entities=entities,
            nli_results=nli_results,
        )
        self.explanation_service.explain_all(changes)
        summary = build_summary(changes)
        logger.info("number of detected changes=%s", summary.total_changes)

        return ComparisonResult(
            comparison_id=comparison_id,
            old_document=old_document,
            new_document=new_document,
            summary=summary,
            changes=changes,
            status=ComparisonStatus.COMPLETED,
            alignment_stats={
                "matched": len(alignment.matched()),
                "added": len(alignment.added()),
                "deleted": len(alignment.deleted()),
                "old_sentences": len(old_document.sentences),
                "new_sentences": len(new_document.sentences),
                "old_paragraphs": len(old_document.paragraphs),
                "new_paragraphs": len(new_document.paragraphs),
            },
        )

    def _run_nli(
        self,
        old_document: Document,
        new_document: Document,
        alignment,
        values,
        dates,
        entities,
    ) -> dict[tuple[str, str], NLIResult]:
        old_by_id = {sentence.id: sentence for sentence in old_document.sentences}
        new_by_id = {sentence.id: sentence for sentence in new_document.sentences}
        pending: list[tuple[str, str, str, str]] = []
        extractor = self.value_extractor

        for pair in alignment.matched():
            old_sentence = old_by_id[pair.old_sentence_id]
            new_sentence = new_by_id[pair.new_sentence_id]
            old_values = values.get(old_sentence.id, [])
            new_values = values.get(new_sentence.id, [])
            old_dates = dates.get(old_sentence.id, [])
            new_dates = dates.get(new_sentence.id, [])
            value_deltas = extractor.compare_values(old_values, new_values)
            date_deltas = extractor.compare_dates(old_dates, new_dates)
            from app.services.entity_service import compare_entities

            entity_changes = compare_entities(
                entities.get(old_sentence.id, []),
                entities.get(new_sentence.id, []),
            )
            if self.change_detector.should_run_nli(
                old_sentence,
                new_sentence,
                pair.similarity,
                old_values,
                new_values,
                old_dates,
                new_dates,
                value_deltas,
                date_deltas,
                entity_changes,
            ):
                pending.append((old_sentence.id, new_sentence.id, old_sentence.text, new_sentence.text))

        results: dict[tuple[str, str], NLIResult] = {}
        if not pending or not self.nli_service.available:
            return results
        inferences = self.nli_service.classify_pairs([(item[2], item[3]) for item in pending])
        for item, inference in zip(pending, inferences):
            results[(item[0], item[1])] = inference
        return results

    def get_comparison_result(self, db: Session, comparison_id: str) -> ComparisonResult:
        record = get_comparison(db, comparison_id)
        if record is None:
            raise ComparisonNotFoundError(comparison_id)
        return record_to_result(record)


def build_summary(changes: list[Change]) -> ComparisonSummary:
    counts = Counter(change.type for change in changes)
    meaningful = [change for change in changes if change.type != ChangeType.UNCHANGED]
    return ComparisonSummary(
        total_changes=len(meaningful),
        additions=counts.get(ChangeType.ADDITION, 0),
        deletions=counts.get(ChangeType.DELETION, 0),
        modifications=counts.get(ChangeType.MODIFICATION, 0),
        numerical_changes=counts.get(ChangeType.NUMERICAL_CHANGE, 0),
        temporal_changes=counts.get(ChangeType.TEMPORAL_CHANGE, 0),
        entity_changes=counts.get(ChangeType.ENTITY_CHANGE, 0),
        contradictions=counts.get(ChangeType.CONTRADICTION, 0),
        refinements=counts.get(ChangeType.REFINEMENT, 0),
        unchanged=counts.get(ChangeType.UNCHANGED, 0),
    )


def record_to_result(record: ComparisonRecord) -> ComparisonResult:
    old_payload = record.old_document.structure_json or {}
    new_payload = record.new_document.structure_json or {}
    summary_payload = record.summary_json or {}
    changes = [_change_from_record(item) for item in record.changes]
    return ComparisonResult(
        comparison_id=record.id,
        old_document=deserialize_document(old_payload),
        new_document=deserialize_document(new_payload),
        summary=ComparisonSummary(
            total_changes=summary_payload.get("total_changes", 0),
            additions=summary_payload.get("additions", 0),
            deletions=summary_payload.get("deletions", 0),
            modifications=summary_payload.get("modifications", 0),
            numerical_changes=summary_payload.get("numerical_changes", 0),
            temporal_changes=summary_payload.get("temporal_changes", 0),
            entity_changes=summary_payload.get("entity_changes", 0),
            contradictions=summary_payload.get("contradictions", 0),
            refinements=summary_payload.get("refinements", 0),
            unchanged=summary_payload.get("unchanged", 0),
        ),
        changes=changes,
        status=ComparisonStatus(record.status),
        created_at=record.created_at,
        alignment_stats=record.alignment_stats_json or {},
    )


def _change_from_record(record: ChangeRecord) -> Change:
    return Change(
        id=record.id,
        type=ChangeType(record.change_type),
        old_text=record.old_text,
        new_text=record.new_text,
        old_sentence_id=record.old_sentence_id,
        new_sentence_id=record.new_sentence_id,
        old_page=record.old_page,
        new_page=record.new_page,
        old_section=record.old_section,
        new_section=record.new_section,
        similarity=record.similarity,
        confidence=record.confidence,
        explanation=record.explanation,
        details=record.details_json or {},
    )
