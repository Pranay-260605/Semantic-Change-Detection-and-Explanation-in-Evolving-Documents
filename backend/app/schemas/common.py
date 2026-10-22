"""Shared API schemas."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Stable error payload returned to API clients."""

    error: str = Field(examples=["UNSUPPORTED_FILE_TYPE"])
    message: str = Field(
        examples=["Only PDF, DOCX and TXT files are supported."],
    )
