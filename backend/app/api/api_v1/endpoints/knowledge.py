import logging
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user, get_session, require_role
from app.models.knowledge_base import KBCreate, KBRead, KBUpdate, KnowledgeBase
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[KBRead])
async def list_knowledge_bases(
    space_id: Optional[UUID] = None,
    room_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    query = select(KnowledgeBase)
    if space_id:
        query = query.where(KnowledgeBase.space_id == space_id)
    if room_id:
        query = query.where(KnowledgeBase.room_id == room_id)
    result = await session.exec(query)
    return result.all()


@router.post("/", response_model=KBRead)
async def create_knowledge_base(
    kb_in: KBCreate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.TEACHER])),
    session: AsyncSession = Depends(get_session),
):
    kb = KnowledgeBase(**kb_in.model_dump())
    session.add(kb)
    await session.commit()
    await session.refresh(kb)
    return kb


@router.get("/{kb_id}", response_model=KBRead)
async def get_knowledge_base(
    kb_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    kb = await session.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.put("/{kb_id}", response_model=KBRead)
async def update_knowledge_base(
    kb_id: UUID,
    kb_in: KBUpdate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.TEACHER])),
    session: AsyncSession = Depends(get_session),
):
    kb = await session.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    update_data = kb_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(kb, key, value)
    session.add(kb)
    await session.commit()
    await session.refresh(kb)
    return kb


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: UUID,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.TEACHER])),
    session: AsyncSession = Depends(get_session),
):
    kb = await session.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    await session.delete(kb)
    await session.commit()
    return {"message": "Knowledge base deleted"}


# ============================================================
# Build, Status, Merge, Query, Documents
# ============================================================


class MergeRequest(BaseModel):
    source_kb_id: str


class QueryRequest(BaseModel):
    question: str


@router.post("/{kb_id}/build")
async def build_knowledge_base(
    kb_id: UUID,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.TEACHER])),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Trigger a KB build. Delegates to graphrag_service if available."""
    kb = await session.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    if kb.build_status == "building":
        return {"status": "already_building", "message": "Build already in progress"}

    kb.build_status = "building"
    session.add(kb)
    await session.commit()

    # Attempt to enqueue graphrag build via ARQ
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        from app.core.config import settings

        redis_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        await redis_pool.enqueue_job(
            "build_knowledge_graph",
            str(kb_id),
            str(kb.room_id) if kb.room_id else None,
            str(kb.space_id) if kb.space_id else None,
        )
        logger.info("Enqueued KB build job for kb_id=%s", kb_id)
    except Exception as e:
        logger.warning("Could not enqueue KB build (ARQ/Redis unavailable): %s", e)
        # Mark as error since we can't actually build
        kb.build_status = "error"
        session.add(kb)
        await session.commit()

    return {"status": kb.build_status, "message": "Build triggered"}


@router.get("/{kb_id}/status")
async def get_knowledge_base_status(
    kb_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Get the current build status of a KB."""
    kb = await session.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    return {
        "build_status": kb.build_status,
        "node_count": kb.node_count,
        "edge_count": kb.edge_count,
        "last_built_at": kb.last_built_at.isoformat() if kb.last_built_at else None,
    }


@router.post("/{kb_id}/merge")
async def merge_knowledge_bases(
    kb_id: UUID,
    body: MergeRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.TEACHER])),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Merge a source KB into the target KB."""
    target = await session.get(KnowledgeBase, kb_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target knowledge base not found")

    source = await session.get(KnowledgeBase, UUID(body.source_kb_id))
    if not source:
        raise HTTPException(status_code=404, detail="Source knowledge base not found")

    # Update counts (actual graph merge would be done by graphrag_service)
    target.node_count += source.node_count
    target.edge_count += source.edge_count
    target.source_type = "merged"
    target.last_built_at = datetime.now(timezone.utc)
    session.add(target)
    await session.commit()

    logger.info("Merged KB %s into %s", body.source_kb_id, kb_id)
    return {"message": f"Merged {source.name} into {target.name}"}


@router.post("/{kb_id}/query")
async def query_knowledge_base(
    kb_id: UUID,
    body: QueryRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Query a KB using the graph search service."""
    kb = await session.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    if kb.build_status != "ready":
        raise HTTPException(
            status_code=400, detail="Knowledge base is not ready. Please build first."
        )

    # Delegate to graph_search_service
    try:
        from app.services.graph_search_service import GraphSearchService

        search_service = GraphSearchService()
        result = await search_service.search(
            query=body.question,
            room_id=str(kb.room_id) if kb.room_id else None,
        )
        return {
            "answer": result.get("answer", "No answer found."),
            "intent": result.get("intent", "unknown"),
            "sources": result.get("sources", []),
        }
    except Exception as e:
        logger.error("KB query failed for kb_id=%s: %s", kb_id, e)
        raise HTTPException(status_code=500, detail="Query failed") from e


@router.post("/{kb_id}/documents")
async def upload_document_to_kb(
    kb_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.TEACHER])),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Upload a document to a KB for extraction."""
    kb = await session.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Validate file type
    allowed_types = {
        "application/pdf",
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, TXT, MD, CSV, DOCX",
        )

    # Read file content
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")

    # Store document (in a real implementation, this would go to a document store)
    logger.info("Uploaded document '%s' (%d bytes) to KB %s", file.filename, len(content), kb_id)

    # Update source_type if this is the first document
    if kb.source_type == "conversation":
        kb.source_type = "document"
        session.add(kb)
        await session.commit()

    return {"message": f"Document '{file.filename}' uploaded successfully", "size": len(content)}
