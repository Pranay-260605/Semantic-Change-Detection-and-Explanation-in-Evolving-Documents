"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.comparisons import router as comparisons_router
from app.api.documents import router as documents_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)
settings = get_settings()
configure_logging(settings.log_level)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Semantic Change Detection and Explanation in Evolving Documents. "
        "Upload two versions of a PDF, DOCX, or TXT file to identify meaningful "
        "additions, deletions, numerical changes, date changes, entity changes, "
        "contradictions, and refinements."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(comparisons_router)


@app.on_event("startup")
def on_startup() -> None:
    Path(settings.upload_path).mkdir(parents=True, exist_ok=True)
    Path(settings.upload_path).parent.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("Application startup complete")


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.code, message=exc.message).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred while processing the request.",
        ).model_dump(),
    )


@app.get("/health", tags=["Health"], summary="Health check", response_model=dict)
def health() -> dict:
    """Return service status for load balancers and local smoke tests."""
    return {
        "status": "ok",
        "service": "semantic-document-change-analyzer",
        "version": settings.app_version,
    }
