"""
Storage service — safely saves uploaded files to disk.
"""
import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings


def _upload_dir() -> Path:
    settings = get_settings()
    path = Path(settings.UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def save_upload(file: UploadFile, safe_filename: str) -> tuple[Path, int]:
    """
    Save the uploaded file to the uploads directory.

    The file is stored under a UUID-prefixed name to prevent collisions.
    Returns (absolute_path, file_size_bytes).
    """
    uid = uuid.uuid4().hex
    stored_name = f"{uid}_{safe_filename}"
    dest = _upload_dir() / stored_name

    content = await file.read()
    await file.seek(0)  # Reset for potential re-reads

    dest.write_bytes(content)
    return dest, len(content)


def delete_upload(file_path: Path) -> None:
    """
    Delete a stored upload. Silently ignores missing files.
    """
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        pass
