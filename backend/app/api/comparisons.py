"""Comparison endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi import Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import MissingFileError
from app.db.repository import list_comparisons
from app.models.change import ChangeType
from app.schemas.comparison import (
    ChangeResponse,
    ComparisonHistoryItem,
    ComparisonHistoryResponse,
    ComparisonResponse,
    ComparisonSummaryResponse,
)
from app.services.runtime import get_comparison_service, get_file_storage

router = APIRouter(prefix="/api/v1/comparisons", tags=["Comparisons"])


@router.get(
    "",
    response_model=ComparisonHistoryResponse,
    summary="List recent comparisons",
    description="Return persisted comparison metadata and summaries, newest first.",
)
def get_comparison_history(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ComparisonHistoryResponse:
    records = list_comparisons(db, limit=limit, offset=offset)
    items = []
    for record in records:
        summary = record.summary_json or {}
        items.append(
            ComparisonHistoryItem(
                comparison_id=record.id,
                status=record.status,
                created_at=record.created_at,
                old_document={
                    "filename": record.old_document.filename,
                    "pages": record.old_document.total_pages,
                    "file_type": record.old_document.file_type,
                    "document_id": record.old_document.id,
                },
                new_document={
                    "filename": record.new_document.filename,
                    "pages": record.new_document.total_pages,
                    "file_type": record.new_document.file_type,
                    "document_id": record.new_document.id,
                },
                summary=summary,
            )
        )
    return ComparisonHistoryResponse(items=items, limit=limit, offset=offset)


@router.post(
    "",
    response_model=ComparisonResponse,
    summary="Compare two document versions",
    description=(
        "Upload an older and a newer document. The backend parses both files, "
        "aligns sentences, extracts values and entities, classifies semantic changes, "
        "and returns a structured comparison."
    ),
)
async def create_comparison(
    old_file: UploadFile = File(..., description="Older document version (PDF, DOCX, or TXT)"),
    new_file: UploadFile = File(..., description="Newer document version (PDF, DOCX, or TXT)"),
    db: Session = Depends(get_db),
) -> ComparisonResponse:
    if old_file is None or not old_file.filename:
        raise MissingFileError("old_file")
    if new_file is None or not new_file.filename:
        raise MissingFileError("new_file")

    storage = get_file_storage()
    old_path, old_name, _old_ext = await storage.save_upload(old_file, "old_file")
    new_path, new_name, _new_ext = await storage.save_upload(new_file, "new_file")
    service = get_comparison_service()
    result = service.compare_files(
        old_path,
        new_path,
        old_filename=old_name,
        new_filename=new_name,
        db=db,
    )
    return ComparisonResponse.from_result(result)


@router.get(
    "/{comparison_id}",
    response_model=ComparisonResponse,
    summary="Get a stored comparison",
)
def get_comparison(
    comparison_id: str,
    db: Session = Depends(get_db),
) -> ComparisonResponse:
    service = get_comparison_service()
    result = service.get_comparison_result(db, comparison_id)
    return ComparisonResponse.from_result(result)


@router.get(
    "/{comparison_id}/changes",
    response_model=list[ChangeResponse],
    summary="Get changes for a comparison",
)
def get_comparison_changes(
    comparison_id: str,
    db: Session = Depends(get_db),
    include_unchanged: bool = False,
) -> list[ChangeResponse]:
    service = get_comparison_service()
    result = service.get_comparison_result(db, comparison_id)
    changes = result.changes
    if not include_unchanged:
        changes = [change for change in changes if change.type != ChangeType.UNCHANGED]
    return [ChangeResponse.from_change(change) for change in changes]


@router.get(
    "/{comparison_id}/summary",
    response_model=ComparisonSummaryResponse,
    summary="Get the change summary for a comparison",
)
def get_comparison_summary(
    comparison_id: str,
    db: Session = Depends(get_db),
) -> ComparisonSummaryResponse:
    service = get_comparison_service()
    result = service.get_comparison_result(db, comparison_id)
    return ComparisonResponse.from_result(result).summary
