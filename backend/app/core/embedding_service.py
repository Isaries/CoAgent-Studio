"""
Embedding Service — Async text-to-vector generation.

Uses OpenAI text-embedding-3-small by default. Falls back gracefully.
"""

from typing import List, Optional

import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger()

DEFAULT_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


class EmbeddingService:
    """Generates embeddings via OpenAI API."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self.api_key = api_key
        self.model = model
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text string."""
        result = await self.get_embeddings_batch([text])
        return result[0]

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts in a single API call.

        Empty or whitespace-only texts are replaced with a placeholder
        to avoid API errors.
        """
        if not texts:
            return []

        # Sanitize inputs
        clean_texts = [t.strip() if t.strip() else "empty" for t in texts]

        try:
            client = self._get_client()
            response = await client.embeddings.create(
                model=self.model,
                input=clean_texts,
            )
        except Exception as e:
            logger.error("embedding_api_error", error=str(e), text_count=len(texts))
            raise

        # Sort by index to maintain order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]
