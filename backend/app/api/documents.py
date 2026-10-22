"""Document parsing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.repository import save_document
from app.schemas.comparison import DocumentParseResponse, document_to_parse_response
from app.services.runtime import get_comparison_service, get_file_storage

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.post(
    "/parse",
    response_model=DocumentParseResponse,
    summary="Parse a document into structured sections, paragraphs, and sentences",
)
async def parse_document(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT document"),
    db: Session = Depends(get_db),
) -> DocumentParseResponse:
    """Upload one document, parse it, and return structure for highlighting."""
    storage = get_file_storage()
    path, original_name, _extension = await storage.save_upload(file, "file")
    service = get_comparison_service()
    document = service.parse_document(path, original_filename=original_name)
    save_document(db, document)
    return document_to_parse_response(document)
