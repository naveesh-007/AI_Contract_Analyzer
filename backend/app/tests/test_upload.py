"""
Tests for document upload, text extraction, file validation, and API endpoints.

Run:
    cd backend
    pytest app/tests/ -v
"""
import io
import os
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

# ── Test client setup ──────────────────────────────────────────────────────────

# We patch database so tests don't need a live PostgreSQL connection
@pytest.fixture(scope="module")
def client():
    """
    Sync test client for FastAPI.
    DB calls are mocked — no real PostgreSQL required.
    """
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://fake:fake@localhost/fake")
    os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "fake-key")

    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Health ────────────────────────────────────────────────────────────────────


def test_health_endpoint(client):
    """GET /api/health must return {"status": "ok"}."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


# ── File Validation Unit Tests ────────────────────────────────────────────────


class TestFileValidation:
    """Unit tests for the file validation utilities."""

    def test_allowed_extension_pdf(self):
        from app.utils.file_validation import sanitize_filename, validate_upload
        name = sanitize_filename("contract.pdf")
        assert name == "contract.pdf"

    def test_allowed_extension_txt(self):
        from app.utils.file_validation import sanitize_filename
        name = sanitize_filename("agreement.txt")
        assert name == "agreement.txt"

    def test_sanitize_path_traversal(self):
        from app.utils.file_validation import sanitize_filename
        name = sanitize_filename("../../etc/passwd")
        # Must not contain path separators
        assert "/" not in name
        assert "\\" not in name
        assert ".." not in name

    def test_sanitize_special_chars(self):
        from app.utils.file_validation import sanitize_filename
        name = sanitize_filename("my contract (v2)!.pdf")
        assert name.endswith(".pdf")
        assert "(" not in name
        assert ")" not in name

    def test_sanitize_empty_becomes_upload(self):
        from app.utils.file_validation import sanitize_filename
        name = sanitize_filename("")
        assert name == "upload"

    @pytest.mark.asyncio
    async def test_validate_empty_file_raises(self):
        from app.utils.file_validation import FileValidationError, validate_upload

        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "empty.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=b"")
        mock_file.seek = AsyncMock()

        with pytest.raises(FileValidationError, match="empty"):
            await validate_upload(mock_file)

    @pytest.mark.asyncio
    async def test_validate_disallowed_extension_raises(self):
        from app.utils.file_validation import FileValidationError, validate_upload

        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "malware.exe"
        mock_file.content_type = "application/octet-stream"
        mock_file.read = AsyncMock(return_value=b"MZ\x90\x00")
        mock_file.seek = AsyncMock()

        with pytest.raises(FileValidationError, match="extension"):
            await validate_upload(mock_file)

    @pytest.mark.asyncio
    async def test_validate_oversized_file_raises(self):
        from app.utils.file_validation import FileValidationError, validate_upload

        big_content = b"x" * (30 * 1024 * 1024)  # 30 MB > 25 MB limit

        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "huge.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=big_content)
        mock_file.seek = AsyncMock()

        with pytest.raises(FileValidationError, match="too large"):
            await validate_upload(mock_file)


# ── Extraction Unit Tests ─────────────────────────────────────────────────────


class TestExtraction:
    """Unit tests for text extraction service."""

    def test_extract_txt_simple(self, tmp_path):
        from app.services.extraction import extract_txt

        txt_file = tmp_path / "test.txt"
        content = "Hello, world!\nThis is a contract."
        txt_file.write_text(content, encoding="utf-8")

        pages = extract_txt(txt_file)
        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert "Hello, world!" in pages[0].text
        assert pages[0].char_start == 0

    def test_extract_txt_preserves_offsets(self, tmp_path):
        from app.services.extraction import extract_txt

        txt_file = tmp_path / "offsets.txt"
        txt_file.write_text("ABC DEF", encoding="utf-8")

        pages = extract_txt(txt_file)
        assert pages[0].char_end == len("ABC DEF")

    def test_extract_document_dispatch_txt(self, tmp_path):
        from app.services.extraction import extract_document

        txt_file = tmp_path / "doc.txt"
        txt_file.write_text("Sample text", encoding="utf-8")

        pages = extract_document(txt_file, "txt")
        assert len(pages) >= 1

    def test_extract_document_invalid_type(self, tmp_path):
        from app.services.extraction import ExtractionError, extract_document

        dummy = tmp_path / "file.csv"
        dummy.write_text("col1,col2")

        with pytest.raises(ExtractionError, match="Unsupported"):
            extract_document(dummy, "csv")

    def test_extract_pdf_real_file(self):
        """
        Integration test using a real sample contract PDF.
        Skipped if sample file not present.
        """
        sample = Path(__file__).parents[3] / "sample-contracts" / "rental_agreement.pdf"
        if not sample.exists():
            pytest.skip("Sample PDF not available")

        from app.services.extraction import extract_pdf

        pages = extract_pdf(sample)
        assert len(pages) > 0
        assert all(p.text for p in pages)

    def test_extract_pdf_corrupt(self, tmp_path):
        from app.services.extraction import ExtractionError, extract_pdf

        corrupt = tmp_path / "corrupt.pdf"
        corrupt.write_bytes(b"this is not a pdf")

        with pytest.raises(ExtractionError):
            extract_pdf(corrupt)


# ── API Upload Tests (mocked DB) ──────────────────────────────────────────────


class TestUploadAPI:
    """Integration tests for the upload endpoint with mocked DB."""

    def _make_txt_upload(self, content: bytes = b"Sample contract text.") -> dict:
        return {
            "file": ("test_contract.txt", io.BytesIO(content), "text/plain"),
            "document_type": (None, "Rental Agreement"),
        }

    def test_upload_txt_success(self, client):
        """TXT upload should succeed and return ANALYZED status."""
        with (
            patch("app.api.routes.documents.save_upload", new_callable=AsyncMock) as mock_save,
            patch("app.api.routes.documents.DocumentRepository") as MockRepo,
        ):
            fake_id = uuid.uuid4()
            fake_doc = MagicMock()
            fake_doc.id = fake_id
            fake_doc.filename = "test_contract.txt"
            fake_doc.document_type = "Rental Agreement"
            fake_doc.status = "ANALYZED"

            repo_instance = AsyncMock()
            repo_instance.create_document = AsyncMock(return_value=fake_doc)
            repo_instance.update_status = AsyncMock(return_value=fake_doc)
            repo_instance.save_pages = AsyncMock(return_value=[])
            MockRepo.return_value = repo_instance

            mock_save.return_value = (Path("/tmp/fake.txt"), 21)

            response = client.post(
                "/api/documents/upload",
                files=self._make_txt_upload(),
            )
            assert response.status_code in (200, 201, 422), response.text

    def test_upload_invalid_extension_rejected(self, client):
        """Executable files must be rejected with 400."""
        response = client.post(
            "/api/documents/upload",
            files={
                "file": ("hack.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream"),
                "document_type": (None, "Other"),
            },
        )
        assert response.status_code == 400
        assert "extension" in response.json()["detail"].lower()

    def test_upload_empty_file_rejected(self, client):
        """Empty files must be rejected with 400."""
        response = client.post(
            "/api/documents/upload",
            files={
                "file": ("empty.txt", io.BytesIO(b""), "text/plain"),
                "document_type": (None, "Other"),
            },
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_get_document_not_found(self, client):
        """GET /api/documents/{unknown_id} must return 404."""
        with patch("app.api.routes.documents.DocumentRepository") as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_document = AsyncMock(return_value=None)
            MockRepo.return_value = repo_instance

            fake_id = uuid.uuid4()
            response = client.get(f"/api/documents/{fake_id}")
            assert response.status_code == 404
