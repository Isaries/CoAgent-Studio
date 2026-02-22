"""
GraphRAG Service — Core orchestrator for knowledge graph construction.

Contains ARQ-callable tasks for:
1. Entity/relationship extraction from messages
2. Community detection (Leiden clustering)
3. Community summarization
"""

import hashlib
import uuid
from typing import Any, Dict, List

import instructor
import structlog
import tiktoken
from openai import AsyncOpenAI
from sqlalchemy.orm import sessionmaker
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
    CommunityReport,
    EntityNode,
    EntityRelationship,
    GraphChunk,
)
from app.models.message import Message

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


# ── LLM Extraction ────────────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """You are an expert knowledge graph extractor for an educational collaboration platform.

Given a conversation chunk between students, teachers, and AI agents, extract:
1. ENTITIES: People (students, teachers), AI Agents, Concepts/Topics discussed, Technologies mentioned, Artifacts created, Issues/Problems encountered.
2. RELATIONSHIPS: How entities relate to each other (DISCUSSES, CREATES, RESOLVES, STRUGGLES_WITH, MENTIONS, COLLABORATES_WITH, DEPENDS_ON).

Rules:
- Use canonical names (e.g., "Alice" not "alice" or "A")
- Merge similar concepts (e.g., "PostgreSQL" and "Postgres" → "PostgreSQL")
- Focus on substantive relationships, skip trivial greetings
- Each evidence field should be a direct quote or close paraphrase"""


async def extract_graph_from_chunk(
    chunk_text: str, api_key: str
) -> GraphChunk:
    """Use instructor + OpenAI to extract structured entities & relationships."""
    client = instructor.from_openai(AsyncOpenAI(api_key=api_key))

    result = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_model=GraphChunk,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract entities and relationships from this conversation:\n\n{chunk_text}"},
        ],
        max_retries=2,
    )
    return result


COMMUNITY_SUMMARY_PROMPT = """You are an expert educational analyst. Given a cluster of related entities and their relationships from a collaborative learning environment, write a comprehensive summary.

Include:
1. A descriptive title for this topic cluster
2. A multi-paragraph summary explaining what happened, who was involved, and what was discussed
3. 3-5 key findings as bullet points
4. List the most important entity names

Write in a professional analytical tone."""


async def generate_community_report(
    community_id: int,
    nodes_text: str,
    edges_text: str,
    api_key: str,
    level: int = 0,
) -> CommunityReport:
    """Generate a structured community report using instructor."""
    client = instructor.from_openai(AsyncOpenAI(api_key=api_key))

    prompt = f"""Community #{community_id} contains these entities and relationships:

ENTITIES:
{nodes_text}

RELATIONSHIPS:
{edges_text}

Generate a comprehensive analytical report for this community."""

    result = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_model=CommunityReport,
        messages=[
            {"role": "system", "content": COMMUNITY_SUMMARY_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_retries=2,
    )
    result.community_id = community_id
    result.level = level
    return result


# ── ARQ Tasks ──────────────────────────────────────────────────────────

async def extract_entities_task(ctx: Dict[str, Any], room_id: str) -> Dict[str, int]:
    """
    ARQ task: Extract entities & relationships from recent room messages.
    
    1. Fetch messages from PostgreSQL
    2. Chunk them
    3. Call LLM for structured extraction
    4. Upsert into Neo4j
    5. Embed descriptions into Qdrant
    """
    logger.info("graphrag_extract_start", room_id=room_id)

    session_factory = ctx["session_factory"]
    api_key = ctx.get("embedding_api_key", "")

    if not api_key:
        logger.error("graphrag_no_api_key")
        return {"error": "No API key configured"}

    # 1. Fetch messages
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

    # 2. Chunk
    chunks = chunk_messages(formatted, max_tokens=settings.GRAPHRAG_CHUNK_TOKENS)
    logger.info("graphrag_chunked", room_id=room_id, chunks=len(chunks))

    # 3. Extract entities from each chunk
    all_nodes: List[EntityNode] = []
    all_edges: List[EntityRelationship] = []

    for chunk_text in chunks:
        try:
            graph_chunk = await extract_graph_from_chunk(chunk_text, api_key)
            all_nodes.extend(graph_chunk.nodes)
            all_edges.extend(graph_chunk.edges)
        except Exception as e:
            logger.warning("graphrag_extraction_failed", error=str(e))
            continue

    # 4. Upsert into Neo4j
    node_dicts = [n.model_dump() for n in all_nodes]
    edge_dicts = [e.model_dump() for e in all_edges]

    node_count = await neo4j_client.upsert_entities(room_id, node_dicts)
    edge_count = await neo4j_client.upsert_relationships(room_id, edge_dicts)

    # 5. Embed entity descriptions → Qdrant
    embedding_service = EmbeddingService(api_key=api_key)

    # Deduplicate nodes by name
    unique_nodes = {n.name: n for n in all_nodes}
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
        await vector_store.upsert_embeddings(ENTITY_COLLECTION, points)

    # 6. Embed message chunks → Qdrant
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
                    "text": chunk_text[:2000],  # Truncate for storage
                    "chunk_index": i,
                },
            })
        await vector_store.upsert_embeddings(CHUNK_COLLECTION, chunk_points)

    logger.info(
        "graphrag_extract_complete",
        room_id=room_id,
        nodes=node_count,
        edges=edge_count,
        chunks=len(chunks),
    )
    return {"nodes": node_count, "edges": edge_count, "chunks": len(chunks)}


async def build_communities_task(ctx: Dict[str, Any], room_id: str) -> Dict[str, int]:
    """
    ARQ task: Run Leiden clustering + generate community summaries.
    
    1. Run Leiden algorithm on Neo4j
    2. For each community, gather members
    3. Generate summary via LLM
    4. Embed summaries into Qdrant
    """
    logger.info("graphrag_communities_start", room_id=room_id)

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

            # Format for LLM
            nodes_text = "\n".join(
                [f"- {n['name']} ({n['type']}): {n.get('description', 'N/A')}" for n in nodes if n]
            )
            edges_text = "\n".join(
                [f"- {e['source']} --[{e['relation']}]--> {e['target']}: {e.get('evidence', 'N/A')}" for e in edges if e]
            ) or "No explicit relationships found."

            report = await generate_community_report(cid, nodes_text, edges_text, api_key)

            # Embed summary
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
        # Clear old summaries for this room first
        await vector_store.delete_by_room(COMMUNITY_COLLECTION, room_id)
        await vector_store.upsert_embeddings(COMMUNITY_COLLECTION, summary_points)

    logger.info(
        "graphrag_communities_complete",
        room_id=room_id,
        communities=len(community_ids),
        summaries=len(summary_points),
    )
    return {"communities": len(community_ids), "summaries": len(summary_points)}


async def full_graph_rebuild_task(ctx: Dict[str, Any], room_id: str) -> Dict[str, Any]:
    """
    ARQ task: Full pipeline — wipe old data, extract entities, build communities.
    """
    logger.info("graphrag_full_rebuild_start", room_id=room_id)

    # ── Step 0: Wipe old graph data for idempotent rebuilds ──
    deleted = await neo4j_client.delete_room_graph(room_id)
    await vector_store.delete_by_room(ENTITY_COLLECTION, room_id)
    await vector_store.delete_by_room(CHUNK_COLLECTION, room_id)
    await vector_store.delete_by_room(COMMUNITY_COLLECTION, room_id)
    logger.info("graphrag_old_data_wiped", room_id=room_id, neo4j_deleted=deleted)

    extract_result = await extract_entities_task(ctx, room_id)
    community_result = await build_communities_task(ctx, room_id)

    return {
        "extraction": extract_result,
        "communities": community_result,
    }
