"""
File validation utilities — extension, MIME type, size, filename safety.
"""
import os
import re
import unicodedata
from pathlib import PurePosixPath

from fastapi import UploadFile

from app.core.config import get_settings


def _settings():
    return get_settings()


class FileValidationError(ValueError):
    """Raised when an uploaded file fails validation."""


async def validate_upload(file: UploadFile) -> None:
    """
    Validate an uploaded file.

    Checks:
    - File is not empty (content-length or actual peek)
    - Extension is allowed
    - MIME type is allowed
    - File size is within limits

    Raises FileValidationError on any failure.
    """
    settings = _settings()

    if not file.filename:
        raise FileValidationError("No filename provided.")

    # ── Extension check ───────────────────────────────────────────────────────
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f'File extension "{ext}" is not allowed. '
            f'Accepted: {", ".join(sorted(settings.ALLOWED_EXTENSIONS))}'
        )

    # ── MIME type check ────────────────────────────────────────────────────────
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in settings.ALLOWED_MIME_TYPES:
        raise FileValidationError(
            f'MIME type "{content_type}" is not accepted. '
            f'Accepted: {", ".join(sorted(settings.ALLOWED_MIME_TYPES))}'
        )

    # ── Read content into memory for size + empty check ───────────────────────
    content = await file.read()
    await file.seek(0)  # Reset stream for downstream use

    if len(content) == 0:
        raise FileValidationError("Uploaded file is empty.")

    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        size_mb = len(content) / 1024 / 1024
        limit_mb = settings.MAX_FILE_SIZE_BYTES / 1024 / 1024
        raise FileValidationError(
            f"File is too large ({size_mb:.1f} MB). Maximum size is {limit_mb:.0f} MB."
        )


def sanitize_filename(filename: str) -> str:
    """
    Return a safe version of the filename.

    - Normalises unicode
    - Strips path separators (prevents path traversal)
    - Removes unsafe characters
    - Truncates to 200 characters
    - Falls back to 'upload' if result is empty
    """
    # Normalise unicode
    filename = unicodedata.normalize("NFKD", filename)

    # Take only the basename — prevents traversal like ../../etc/passwd
    filename = PurePosixPath(filename).name
    filename = os.path.basename(filename)  # Windows path as well

    # Replace unsafe chars with underscores
    filename = re.sub(r"[^\w\s.\-]", "_", filename)

    # Collapse whitespace
    filename = re.sub(r"\s+", "_", filename).strip("_.")

    # Truncate
    if len(filename) > 200:
        stem, ext = os.path.splitext(filename)
        filename = stem[: 200 - len(ext)] + ext

    return filename or "upload"
