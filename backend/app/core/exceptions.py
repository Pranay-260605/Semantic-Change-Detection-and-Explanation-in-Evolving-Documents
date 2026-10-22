"""Application errors mapped to stable API error codes."""

from __future__ import annotations


class AppError(Exception):
    """Base class for client-facing application errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class UnsupportedFileTypeError(AppError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            "UNSUPPORTED_FILE_TYPE",
            message or "Only PDF, DOCX and TXT files are supported.",
            status_code=400,
        )


class FileTooLargeError(AppError):
    def __init__(self, max_mb: int) -> None:
        super().__init__(
            "FILE_TOO_LARGE",
            f"Uploaded file exceeds the maximum size of {max_mb} MB.",
            status_code=413,
        )


class MissingFileError(AppError):
    def __init__(self, field: str) -> None:
        super().__init__(
            "MISSING_FILE",
            f"A file is required for '{field}'.",
            status_code=400,
        )


class DocumentParseError(AppError):
    def __init__(self, message: str = "The document could not be parsed.") -> None:
        super().__init__("DOCUMENT_PARSE_ERROR", message, status_code=422)


class ComparisonNotFoundError(AppError):
    def __init__(self, comparison_id: str) -> None:
        super().__init__(
            "COMPARISON_NOT_FOUND",
            f"No comparison found with id '{comparison_id}'.",
            status_code=404,
        )


class ComparisonFailedError(AppError):
    def __init__(self, message: str = "The comparison could not be completed.") -> None:
        super().__init__("COMPARISON_FAILED", message, status_code=500)
