"""
Embedding Service and Vector Math for Document Chunk Retrieval.

Supports:
- OpenAI / OpenAI-compatible Embedding API (e.g. text-embedding-3-small)
- Deterministic Heuristic Semantic Mock Provider (for offline development and zero-network tests)
"""
import hashlib
import logging
import math
import re
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class BaseEmbeddingProvider(ABC):
    """Abstract base class for vector embedding generation."""

    @abstractmethod
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generates embedding vectors for a batch of strings."""
        raise NotImplementedError

    async def get_embedding(self, text: str) -> list[float]:
        """Generates an embedding vector for a single string."""
        results = await self.get_embeddings([text])
        return results[0] if results else []


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Generates embeddings using OpenAI API."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout = timeout_seconds

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise ValueError("OpenAI API key missing for embeddings.")

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return [item["embedding"] for item in data["data"]]
            except Exception as exc:
                logger.error("OpenAI embedding request failed: %s", exc)
                raise


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic semantic hash/frequency embedding provider.
    Enables vector similarity search offline without any external network dependency.
    """

    def __init__(self, vector_dim: int = 128) -> None:
        self.dim = vector_dim

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_single(t) for t in texts]

    def _embed_single(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        cleaned = re.sub(r"[^\w\s]", "", text.lower())
        words = cleaned.split()

        if not words:
            return vec

        for word in words:
            # Map word hash into vector dimension
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            vec[idx] += 1.0

        # Also add character 3-grams for morphological/fuzzy matching
        for i in range(len(cleaned) - 2):
            trigram = cleaned[i : i + 3]
            h = int(hashlib.sha256(trigram.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            vec[idx] += 0.5

        # Normalize to unit vector
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]

        return vec


class EmbeddingService:
    """Factory and manager for embedding generation."""

    def __init__(
        self,
        provider: Optional[BaseEmbeddingProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.provider = provider or self._resolve_provider()

    def _resolve_provider(self) -> BaseEmbeddingProvider:
        api_key = self.settings.LLM_API_KEY.strip()
        provider_type = (self.settings.LLM_PROVIDER or "openai").lower()

        if not api_key or provider_type in ("mock", "groq", "grok") or api_key.startswith("gsk_") or (self.settings.LLM_BASE_URL and "groq.com" in self.settings.LLM_BASE_URL):
            logger.info("Using deterministic semantic MockEmbeddingProvider for vector search.")
            return MockEmbeddingProvider()

        return OpenAIEmbeddingProvider(
            api_key=api_key,
            base_url=self.settings.LLM_BASE_URL,
        )

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return await self.provider.get_embeddings(texts)

    async def get_embedding(self, text: str) -> list[float]:
        return await self.provider.get_embedding(text)
