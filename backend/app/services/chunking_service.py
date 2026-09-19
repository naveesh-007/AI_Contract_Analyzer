"""
Chunking Service — performs section-aware and clause-aware document chunking,
generates embeddings, and stores document_chunks in the database.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk
from app.models.clause import Clause
from app.models.document import DocumentPage
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class ChunkingService:
    """Creates and persists semantic chunks for vector retrieval."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: Optional[EmbeddingService] = None,
    ) -> None:
        self.session = session
        self.embedding_service = embedding_service or EmbeddingService()

    async def create_chunks_for_document(
        self,
        document_id: uuid.UUID,
        pages: list[DocumentPage],
        clauses: list[Clause],
    ) -> list[DocumentChunk]:
        """
        Generates section- and clause-aware chunks from pages & clauses,
        computes their vector embeddings, and persists them into document_chunks.
        """
        # 1. Clean existing chunks for this document
        existing = await self.session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        for old in existing.scalars().all():
            await self.session.delete(old)
        await self.session.flush()

        raw_chunks: list[dict] = []

        # Strategy A: Clause-aware chunks (primary for contracts)
        if clauses:
            for clause in clauses:
                chunk_title = f"{clause.section_number or ''} {clause.section_title or ''}".strip()
                prefix = f"Section {chunk_title}:\n" if chunk_title else ""
                full_chunk_text = f"{prefix}{clause.clause_text}".strip()

                raw_chunks.append(
                    {
                        "document_id": document_id,
                        "clause_id": clause.id,
                        "page_number": clause.page_number or 1,
                        "chunk_text": full_chunk_text,
                        "char_start": clause.char_start,
                        "char_end": clause.char_end,
                    }
                )

        # Strategy B: If no clauses or page text remains uncovered, chunk page paragraphs
        if not raw_chunks and pages:
            for page in pages:
                paragraphs = [p.strip() for p in (page.text or "").split("\n\n") if p.strip()]
                for para in paragraphs:
                    raw_chunks.append(
                        {
                            "document_id": document_id,
                            "clause_id": None,
                            "page_number": page.page_number,
                            "chunk_text": para,
                            "char_start": page.char_start,
                            "char_end": page.char_end,
                        }
                    )

        if not raw_chunks:
            return []

        # 2. Compute embeddings in batch
        texts_to_embed = [c["chunk_text"] for c in raw_chunks]
        try:
            embeddings = await self.embedding_service.get_embeddings(texts_to_embed)
        except Exception as exc:
            logger.warning("Embedding generation failed, saving chunks with null embedding: %s", exc)
            embeddings = [None] * len(raw_chunks)

        # 3. Create DocumentChunk DB entities
        db_chunks = [
            DocumentChunk(
                document_id=c["document_id"],
                clause_id=c["clause_id"],
                page_number=c["page_number"],
                chunk_text=c["chunk_text"],
                char_start=c["char_start"],
                char_end=c["char_end"],
                embedding=embeddings[i] if embeddings else None,
            )
            for i, c in enumerate(raw_chunks)
        ]

        self.session.add_all(db_chunks)
        await self.session.flush()
        logger.info("Created %d chunks for document %s", len(db_chunks), document_id)
        return db_chunks
