"""
Graph API Endpoints — Knowledge graph operations for rooms.

Provides:
- Graph build trigger (manual)
- Graph data retrieval (for visualization)
- Graph query (Analytics Agent Q&A)
- Community summaries
- Graph status
"""

import os
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_session
from app.core.neo4j_client import neo4j_client
from app.core.qdrant_client import COMMUNITY_COLLECTION, vector_store
from app.models.graph_schemas import (
    GraphDataResponse,
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphQueryRequest,
    GraphQueryResponse,
    GraphStatusResponse,
)
from app.models.room import Room
from app.models.user import User
from app.services.graph_search_service import query_graph
from app.services.permission_service import permission_service

logger = structlog.get_logger()

router = APIRouter()


def _get_api_key() -> str:
    """Get OpenAI API key from environment."""
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    return key


async def _verify_room_access(
    room_id: UUID,
    current_user: User,
    session: AsyncSession,
) -> Room:
    """
    Verify user has read access to the room.
    Raises 404 if room doesn't exist, 403 if no permission.
    """
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not await permission_service.check(current_user, "read", room, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return room


@router.post("/{room_id}/build")
async def build_room_graph(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Trigger a full GraphRAG build for a room.
    Enqueues an ARQ background task.
    """
    await _verify_room_access(room_id, current_user, session)

    from app.main import app

    arq_pool = app.state.arq_pool
    job = await arq_pool.enqueue_job("full_graph_rebuild_task", str(room_id))

    logger.info("graphrag_build_enqueued", room_id=str(room_id), job_id=job.job_id)
    return {
        "status": "building",
        "job_id": job.job_id,
        "message": f"Graph build started for room {room_id}",
    }


@router.get("/{room_id}", response_model=GraphDataResponse)
async def get_room_graph(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GraphDataResponse:
    """
    Get the full knowledge graph for a room (for frontend visualization).
    """
    await _verify_room_access(room_id, current_user, session)

    data = await neo4j_client.get_full_graph(str(room_id))

    nodes = [
        GraphNodeResponse(
            id=n.get("id", n.get("name", "")),
            name=n.get("display_name", n.get("name", "")),
            type=n.get("type", "UNKNOWN"),
            description=n.get("description", ""),
            community_id=n.get("community_id"),
        )
        for n in data.get("nodes", [])
        if n
    ]

    edges = [
        GraphEdgeResponse(
            source=e.get("source", ""),
            target=e.get("target", ""),
            relation=e.get("relation", ""),
            evidence=e.get("evidence", ""),
        )
        for e in data.get("edges", [])
        if e
    ]

    return GraphDataResponse(
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
    )


@router.post("/{room_id}/query", response_model=GraphQueryResponse)
async def query_room_graph(
    room_id: UUID,
    body: GraphQueryRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GraphQueryResponse:
    """
    Query the Analytics Agent with a natural language question.
    Uses intent routing → global or local search.
    """
    await _verify_room_access(room_id, current_user, session)

    api_key = _get_api_key()
    result = await query_graph(str(room_id), body.question, api_key)

    return GraphQueryResponse(
        answer=result["answer"],
        intent=result["intent"],
        sources=result.get("sources", []),
    )


@router.get("/{room_id}/communities")
async def get_room_communities(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list:
    """
    Get all community summaries for a room.
    """
    await _verify_room_access(room_id, current_user, session)

    results = []
    try:
        scroll_result = await vector_store.client.scroll(
            collection_name=COMMUNITY_COLLECTION,
            scroll_filter={
                "must": [{"key": "room_id", "match": {"value": str(room_id)}}]
            },
            limit=100,
        )
        points, _next = scroll_result
        for point in points:
            payload = point.payload or {}
            results.append({
                "community_id": payload.get("community_id"),
                "title": payload.get("title", ""),
                "summary": payload.get("summary", ""),
                "key_findings": payload.get("key_findings", []),
                "key_entities": payload.get("key_entities", []),
                "level": payload.get("level", 0),
            })
    except Exception as e:
        logger.warning("community_scroll_failed", error=str(e))

    return results


@router.get("/{room_id}/status", response_model=GraphStatusResponse)
async def get_graph_status(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GraphStatusResponse:
    """
    Get the current graph indexing status for a room.
    """
    await _verify_room_access(room_id, current_user, session)

    stats = await neo4j_client.get_graph_stats(str(room_id))

    return GraphStatusResponse(
        room_id=str(room_id),
        node_count=stats.get("node_count", 0),
        edge_count=stats.get("edge_count", 0),
        community_count=stats.get("community_count", 0),
    )
