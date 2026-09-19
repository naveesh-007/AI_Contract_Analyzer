"""
Document repository — all database CRUD operations for documents and pages.
"""
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentPage
from app.services.extraction import ExtractedPage


class DocumentRepository:
    """Encapsulates all DB operations for Document and DocumentPage models."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_document(
        self,
        *,
        filename: str,
        document_type: str,
        file_type: str,
        file_size: int,
        status: str = "UPLOADED",
    ) -> Document:
        doc = Document(
            filename=filename,
            document_type=document_type,
            file_type=file_type,
            file_size=file_size,
            status=status,
        )
        self.session.add(doc)
        await self.session.flush()  # populate id
        return doc

    async def save_pages(
        self,
        document_id: uuid.UUID,
        pages: list[ExtractedPage],
    ) -> list[DocumentPage]:
        db_pages = [
            DocumentPage(
                document_id=document_id,
                page_number=p.page_number,
                text=p.text,
                char_start=p.char_start,
                char_end=p.char_end,
            )
            for p in pages
        ]
        self.session.add_all(db_pages)
        await self.session.flush()
        return db_pages

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_document(self, document_id: uuid.UUID) -> Document | None:
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_document_with_pages(
        self, document_id: uuid.UUID
    ) -> Document | None:
        result = await self.session.execute(
            select(Document)
            .options(selectinload(Document.pages))
            .where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_status(
        self, document_id: uuid.UUID, status: str
    ) -> Document | None:
        doc = await self.get_document(document_id)
        if doc:
            doc.status = status
            await self.session.flush()
        return doc
