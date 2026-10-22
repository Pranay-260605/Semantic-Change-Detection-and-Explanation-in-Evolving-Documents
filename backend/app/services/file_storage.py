"""Safe upload storage using UUID filenames."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings, get_settings
from app.core.exceptions import FileTooLargeError, MissingFileError, UnsupportedFileTypeError
from app.core.logging import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
CONTENT_TYPE_HINTS = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    },
    ".txt": {"text/plain", "application/octet-stream"},
}


class FileStorage:
    """Writes uploaded files under a configured directory with UUID names."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.upload_dir = self.settings.upload_path
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_filename(self, filename: str | None, field: str) -> str:
        if not filename:
            raise MissingFileError(field)
        name = Path(filename).name
        extension = Path(name).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFileTypeError()
        return extension

    async def save_upload(self, upload: UploadFile, field: str) -> tuple[Path, str, str]:
        """Save an upload and return (path, original_filename, extension)."""
        original = Path(upload.filename or "").name
        extension = self.validate_filename(upload.filename, field)
        destination = self.upload_dir / f"{uuid4().hex}{extension}"
        size = 0
        try:
            with destination.open("wb") as handle:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > self.settings.max_upload_bytes:
                        handle.close()
                        destination.unlink(missing_ok=True)
                        raise FileTooLargeError(self.settings.max_upload_size_mb)
                    handle.write(chunk)
        finally:
            await upload.close()

        if size == 0:
            destination.unlink(missing_ok=True)
            raise MissingFileError(field)

        logger.info("Stored upload field=%s size_bytes=%s", field, size)
        return destination, original, extension.lstrip(".")
