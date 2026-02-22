"""
Qdrant Client — Async wrapper for Qdrant vector database operations.

Manages collections for entity descriptions, community summaries, and message chunks.
"""

from typing import Any, Dict, List, Optional

import structlog
from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings

logger = structlog.get_logger()

# Collection names
ENTITY_COLLECTION = "entity_descriptions"
COMMUNITY_COLLECTION = "community_summaries"
CHUNK_COLLECTION = "message_chunks"

EMBEDDING_DIM = 1536  # text-embedding-3-small dimension


class VectorStore:
    """Async Qdrant client wrapper for GraphRAG vector operations."""

    def __init__(self) -> None:
        self._client: Optional[AsyncQdrantClient] = None

    async def connect(self) -> None:
        """Initialize the Qdrant async client and ensure collections exist."""
        self._client = AsyncQdrantClient(
            host=settings.QDRANT_HOST, port=settings.QDRANT_PORT
        )

        # Ensure all required collections exist
        for collection in [ENTITY_COLLECTION, COMMUNITY_COLLECTION, CHUNK_COLLECTION]:
            await self._ensure_collection(collection)

        logger.info("qdrant_connected", host=settings.QDRANT_HOST)

    async def close(self) -> None:
        """Close the Qdrant client."""
        if self._client:
            await self._client.close()
            logger.info("qdrant_closed")

    @property
    def client(self) -> AsyncQdrantClient:
        if not self._client:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")
        return self._client

    async def _ensure_collection(self, name: str) -> None:
        """Create collection if it doesn't exist."""
        collections = await self.client.get_collections()
        existing = [c.name for c in collections.collections]
        if name not in existing:
            await self.client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_DIM,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("qdrant_collection_created", name=name)

    # ── Upsert Operations ──────────────────────────────────────────────

    async def upsert_embeddings(
        self,
        collection: str,
        points: List[Dict[str, Any]],
    ) -> None:
        """
        Upsert vectors with payloads.
        
        Each point: {"id": str, "vector": list[float], "payload": dict}
        """
        qdrant_points = [
            models.PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload=p.get("payload", {}),
            )
            for p in points
        ]
        await self.client.upsert(
            collection_name=collection,
            points=qdrant_points,
        )

    # ── Search Operations ──────────────────────────────────────────────

    async def search(
        self,
        collection: str,
        query_vector: List[float],
        limit: int = 10,
        room_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in a collection.
        
        Returns list of {id, score, payload} dicts.
        """
        query_filter = None
        if room_id:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="room_id",
                        match=models.MatchValue(value=room_id),
                    )
                ]
            )

        results = await self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
        )

        return [
            {
                "id": str(r.id),
                "score": r.score,
                "payload": r.payload or {},
            }
            for r in results
        ]

    async def delete_by_room(self, collection: str, room_id: str) -> None:
        """Delete all points for a specific room (for rebuilds)."""
        await self.client.delete(
            collection_name=collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="room_id",
                            match=models.MatchValue(value=room_id),
                        )
                    ]
                )
            ),
        )


# Module-level singleton
vector_store = VectorStore()
