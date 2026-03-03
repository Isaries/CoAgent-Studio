"""
GraphRAG Service — 3-tier hybrid orchestrator for knowledge graph construction.

Pipeline: Structural (DB) → NLP (spaCy) → LLM (configurable model)
Contains ARQ-callable tasks for:
1. Entity/relationship extraction via 3-tier pipeline
2. Community detection (Leiden clustering)
3. Community summarization
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List

import redis.asyncio as aioredis
import structlog
import tiktoken
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.embedding_service import EmbeddingService
from app.core.neo4j_client import neo4j_client
from app.core.qdrant_client import (
    CHUNK_COLLECTION,
    COMMUNITY_COLLECTION,
    ENTITY_COLLECTION,
    vector_store,
)
from app.models.graph_schemas import (
    EntityNode,
    EntityRelationship,
    GraphChunk,
)
from app.models.message import Message
from app.services.extractors import (
    extract_concepts_from_chunk,
    extract_nlp_facts,
    extract_structural_facts,
    generate_community_report,
)

logger = structlog.get_logger()


# ── Text Chunking ──────────────────────────────────────────────────────

def chunk_messages(messages: List[Dict[str, str]], max_tokens: int = 600) -> List[str]:
    """
    Group messages into chunks that fit within `max_tokens`.
    Each message is formatted as "sender: content".
    """
    enc = tiktoken.encoding_for_model("gpt-4o")
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_tokens = 0

    for msg in messages:
        line = f"{msg['sender']}: {msg['content']}"
        line_tokens = len(enc.encode(line))

        if current_tokens + line_tokens > max_tokens and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_tokens = 0

        current_chunk.append(line)
        current_tokens += line_tokens

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


# ── Merge Logic ────────────────────────────────────────────────────────

def _merge_graph_chunks(*chunks: GraphChunk) -> GraphChunk:
    """
    Merge multiple GraphChunks, deduplicating nodes and edges.

    - Nodes are deduped by lowercase name; later tiers override earlier descriptions.
    - Edges are deduped by (source_lower, target_lower, relation_lower) tuple.
    """
    merged_nodes: Dict[str, EntityNode] = {}
    merged_edges: Dict[tuple, EntityRelationship] = {}

    for chunk in chunks:
        for node in chunk.nodes:
            key = node.name.lower()
            merged_nodes[key] = node  # Later tier overrides

        for edge in chunk.edges:
            key = (edge.source.lower(), edge.target.lower(), edge.relation.lower())
            if key not in merged_edges:
                merged_edges[key] = edge

    return GraphChunk(
        nodes=list(merged_nodes.values()),
        edges=list(merged_edges.values()),
    )


# ── ARQ Tasks ──────────────────────────────────────────────────────────

async def extract_entities_task(
    ctx: Dict[str, Any],
    room_id: str,
    extraction_model: str = "gpt-4o-mini",
) -> Dict[str, int]:
    """
    ARQ task: 3-tier entity extraction pipeline.

    1. Tier 1: Structural facts from DB (zero cost)
    2. Tier 2: NLP extraction via spaCy (zero cost)
    3. Merge T1+T2 → known_nodes
    4. Tier 3: LLM concept extraction (configurable model)
    5. Final merge of all 3 tiers
    6. Upsert into Neo4j + embed into Qdrant
    """
    logger.info("graphrag_extract_start", room_id=room_id, model=extraction_model)

    session_factory = ctx["session_factory"]
    api_key = ctx.get("embedding_api_key", "")

    if not api_key:
        logger.error("graphrag_no_api_key")
        return {"error": "No API key configured"}

    # ── Fetch messages ──
    async with session_factory() as session:
        query = (
            select(Message)
            .where(Message.room_id == room_id)
            .order_by(Message.created_at.asc())
        )
        result = await session.exec(query)
        db_messages = list(result.all())

    if not db_messages:
        return {"nodes": 0, "edges": 0, "chunks": 0}

    # Format messages
    formatted = []
    for msg in db_messages:
        sender = msg.agent_type or str(msg.sender_id) if msg.sender_id else "System"
        formatted.append({"sender": sender, "content": msg.content})

    # ── Tier 1: Structural extraction (DB-derived) ──
    async with session_factory() as session:
        tier1_chunk = await extract_structural_facts(session, room_id)
    logger.info("graphrag_tier1_complete", nodes=len(tier1_chunk.nodes), edges=len(tier1_chunk.edges))

    # ── Tier 2: NLP extraction (spaCy) ──
    tier2_chunk = extract_nlp_facts(formatted)
    logger.info("graphrag_tier2_complete", nodes=len(tier2_chunk.nodes), edges=len(tier2_chunk.edges))

    # ── Merge T1+T2 to build known_nodes for LLM prompt ──
    pre_llm = _merge_graph_chunks(tier1_chunk, tier2_chunk)
    known_nodes = pre_llm.nodes

    # ── Tier 3: LLM concept extraction ──
    chunks = chunk_messages(formatted, max_tokens=settings.GRAPHRAG_CHUNK_TOKENS)
    logger.info("graphrag_chunked", room_id=room_id, chunks=len(chunks))

    tier3_nodes: List[EntityNode] = []
    tier3_edges: List[EntityRelationship] = []

    for chunk_text in chunks:
        try:
            graph_chunk = await extract_concepts_from_chunk(
                chunk_text, known_nodes, api_key, model=extraction_model
            )
            tier3_nodes.extend(graph_chunk.nodes)
            tier3_edges.extend(graph_chunk.edges)
        except Exception as e:
            logger.warning("graphrag_tier3_extraction_failed", error=str(e))
            continue

    tier3_chunk = GraphChunk(nodes=tier3_nodes, edges=tier3_edges)
    logger.info("graphrag_tier3_complete", nodes=len(tier3_nodes), edges=len(tier3_edges))

    # ── Final merge of all 3 tiers ──
    final = _merge_graph_chunks(tier1_chunk, tier2_chunk, tier3_chunk)

    # ── Upsert into Neo4j ──
    node_dicts = [n.model_dump() for n in final.nodes]
    edge_dicts = [e.model_dump() for e in final.edges]

    node_count = await neo4j_client.upsert_entities(room_id, node_dicts)
    edge_count = await neo4j_client.upsert_relationships(room_id, edge_dicts)
    logger.info("graphrag_neo4j_upsert_complete", room_id=room_id, entity_count=len(final.nodes), edge_count=edge_count)

    # ── Embed entity descriptions → Qdrant ──
    embedding_service = EmbeddingService(api_key=api_key)

    unique_nodes = {n.name: n for n in final.nodes}
    if unique_nodes:
        descriptions = [f"{n.name} ({n.type}): {n.description}" for n in unique_nodes.values()]
        vectors = await embedding_service.get_embeddings_batch(descriptions)

        points = []
        for (name, node), vector in zip(unique_nodes.items(), vectors):
            point_id = hashlib.md5(f"{room_id}:{name}".encode()).hexdigest()
            points.append({
                "id": point_id,
                "vector": vector,
                "payload": {
                    "room_id": room_id,
                    "name": node.name,
                    "type": node.type,
                    "description": node.description,
                },
            })
        try:
            await vector_store.upsert_embeddings(ENTITY_COLLECTION, points)
            logger.info("graphrag_qdrant_upsert_complete", room_id=room_id, point_count=len(points))
        except Exception as e:
            logger.error(
                "graphrag_qdrant_upsert_failed_after_neo4j",
                room_id=room_id,
                error=str(e),
                detail="Neo4j entities were written but Qdrant embeddings failed. "
                       "Re-run extraction to fix inconsistency.",
            )
            raise

    # ── Embed message chunks → Qdrant ──
    if chunks:
        chunk_vectors = await embedding_service.get_embeddings_batch(chunks)
        chunk_points = []
        for i, (chunk_text, vector) in enumerate(zip(chunks, chunk_vectors)):
            chunk_id = hashlib.md5(f"{room_id}:chunk:{i}".encode()).hexdigest()
            chunk_points.append({
                "id": chunk_id,
                "vector": vector,
                "payload": {
                    "room_id": room_id,
                    "text": chunk_text[:2000],
                    "chunk_index": i,
                },
            })
        try:
            await vector_store.upsert_embeddings(CHUNK_COLLECTION, chunk_points)
            logger.info("graphrag_qdrant_chunks_complete", room_id=room_id, chunk_count=len(chunk_points))
        except Exception as e:
            logger.error(
                "graphrag_qdrant_chunk_upsert_failed",
                room_id=room_id,
                error=str(e),
                detail="Neo4j entities were written but Qdrant chunk embeddings failed. "
                       "Re-run extraction to fix inconsistency.",
            )
            raise

    logger.info(
        "graphrag_extract_complete",
        room_id=room_id,
        nodes=node_count,
        edges=edge_count,
        chunks=len(chunks),
        tier1_nodes=len(tier1_chunk.nodes),
        tier2_nodes=len(tier2_chunk.nodes),
        tier3_nodes=len(tier3_nodes),
    )

    # Clear build status when done
    try:
        redis_client = aioredis.from_url(settings.redis_url)
        await redis_client.set(f"graphrag:build_status:{room_id}", "idle", ex=3600)
        await redis_client.set(
            f"graphrag:build_completed:{room_id}",
            datetime.now(timezone.utc).isoformat(),
            ex=86400,
        )
        await redis_client.close()
    except Exception as e:
        logger.debug("graphrag_timestamp_update_failed", room_id=room_id, error=str(e))

    return {"nodes": node_count, "edges": edge_count, "chunks": len(chunks)}


async def build_communities_task(
    ctx: Dict[str, Any],
    room_id: str,
    summarization_model: str = "gpt-4o-mini",
) -> Dict[str, int]:
    """
    ARQ task: Run Leiden clustering + generate community summaries.

    1. Run Leiden algorithm on Neo4j
    2. For each community, gather members
    3. Generate summary via LLM (configurable model)
    4. Embed summaries into Qdrant
    """
    logger.info("graphrag_communities_start", room_id=room_id, model=summarization_model)

    api_key = ctx.get("embedding_api_key", "")
    if not api_key:
        return {"error": "No API key configured"}

    # 1. Run Leiden clustering
    community_count = await neo4j_client.run_leiden_clustering(room_id)
    if community_count == 0:
        logger.info("graphrag_no_communities", room_id=room_id)
        return {"communities": 0, "summaries": 0}

    # 2. Get distinct community IDs
    community_ids = await neo4j_client.get_distinct_communities(room_id)

    # 3. Generate summaries for each community
    embedding_service = EmbeddingService(api_key=api_key)
    summary_points = []

    for cid in community_ids:
        try:
            members = await neo4j_client.get_community_members(room_id, cid)
            nodes = members.get("nodes", [])
            edges = members.get("edges", [])

            if not nodes:
                continue

            nodes_text = "\n".join(
                [f"- {n['name']} ({n['type']}): {n.get('description', 'N/A')}" for n in nodes if n]
            )
            edges_text = "\n".join(
                [f"- {e['source']} --[{e['relation']}]--> {e['target']}: {e.get('evidence', 'N/A')}" for e in edges if e]
            ) or "No explicit relationships found."

            report = await generate_community_report(
                cid, nodes_text, edges_text, api_key, model=summarization_model
            )

            summary_text = f"{report.title}\n{report.summary}"
            vector = await embedding_service.get_embedding(summary_text)

            point_id = hashlib.md5(f"{room_id}:community:{cid}".encode()).hexdigest()
            summary_points.append({
                "id": point_id,
                "vector": vector,
                "payload": {
                    "room_id": room_id,
                    "community_id": cid,
                    "title": report.title,
                    "summary": report.summary,
                    "key_findings": report.key_findings,
                    "key_entities": report.key_entities,
                    "level": report.level,
                },
            })
        except Exception as e:
            logger.warning("graphrag_community_summary_failed", community_id=cid, error=str(e))
            continue

    # 4. Upsert summaries into Qdrant
    if summary_points:
        await vector_store.delete_by_room(COMMUNITY_COLLECTION, room_id)
        await vector_store.upsert_embeddings(COMMUNITY_COLLECTION, summary_points)

    logger.info(
        "graphrag_communities_complete",
        room_id=room_id,
        communities=len(community_ids),
        summaries=len(summary_points),
    )
    return {"communities": len(community_ids), "summaries": len(summary_points)}


async def full_graph_rebuild_task(
    ctx: Dict[str, Any],
    room_id: str,
    extraction_model: str = "gpt-4o-mini",
    summarization_model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    ARQ task: Full pipeline — wipe old data, extract entities, build communities.
    Passes per-room model configuration through to sub-tasks.
    """
    logger.info(
        "graphrag_full_rebuild_start",
        room_id=room_id,
        extraction_model=extraction_model,
        summarization_model=summarization_model,
    )

    # ── Step 0: Wipe old graph data for idempotent rebuilds ──
    deleted = await neo4j_client.delete_room_graph(room_id)
    await vector_store.delete_by_room(ENTITY_COLLECTION, room_id)
    await vector_store.delete_by_room(CHUNK_COLLECTION, room_id)
    await vector_store.delete_by_room(COMMUNITY_COLLECTION, room_id)
    logger.info("graphrag_old_data_wiped", room_id=room_id, neo4j_deleted=deleted)

    extract_result = await extract_entities_task(ctx, room_id, extraction_model=extraction_model)
    community_result = await build_communities_task(ctx, room_id, summarization_model=summarization_model)

    return {
        "extraction": extract_result,
        "communities": community_result,
    }
