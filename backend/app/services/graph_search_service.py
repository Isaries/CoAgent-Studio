"""
Graph Search Service — Intent routing + Global/Local search strategies.

Powers the Analytics Agent's ability to answer questions about room knowledge.
All functions accept a configurable `model` parameter (no hardcoded model names).
"""

from typing import Any, Dict, List

import instructor
import structlog
from openai import AsyncOpenAI

from app.core.embedding_service import EmbeddingService
from app.core.neo4j_client import neo4j_client
from app.core.qdrant_client import (
    CHUNK_COLLECTION,
    COMMUNITY_COLLECTION,
    vector_store,
)
from app.models.graph_schemas import QueryIntent

logger = structlog.get_logger()

INTENT_SYSTEM_PROMPT = """You classify user questions about a collaborative learning room.

- "global": Questions about overall themes, summaries, trends, patterns across the whole room.
  Examples: "What are the main topics discussed?", "Summarize the learning progress", "What were the biggest challenges?"

- "local": Questions about specific people, concepts, events, or artifacts.
  Examples: "What did Alice say about JWT?", "How was the database issue resolved?", "Which tasks are related to Docker?"

Also extract any specific entity names mentioned in the question."""


async def classify_intent(question: str, api_key: str, model: str = "gpt-4o-mini") -> dict:
    """
    Classify a question as global or local using a lightweight LLM call.

    Returns a dict with 'intent', 'entities', 'reasoning', and 'confidence' keys.
    Falls back to keyword heuristics if the LLM call fails.
    """
    try:
        client = instructor.from_openai(AsyncOpenAI(api_key=api_key))

        result = await client.chat.completions.create(
            model=model,
            response_model=QueryIntent,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            max_retries=1,
        )
        # LLM classification has high confidence
        return {
            "intent": result.intent,
            "entities": result.entities,
            "reasoning": result.reasoning,
            "confidence": 0.9,
        }
    except Exception as e:
        logger.warning("classify_intent_llm_failed", error=str(e))

    # ── Keyword-based fallback with confidence scoring ──
    question_lower = question.lower()
    global_keywords = {
        "summary",
        "summarize",
        "overview",
        "themes",
        "trends",
        "patterns",
        "main topics",
        "overall",
    }
    local_keywords = {"who", "what did", "how was", "which", "specific", "tell me about"}

    global_matches = sum(1 for kw in global_keywords if kw in question_lower)
    local_matches = sum(1 for kw in local_keywords if kw in question_lower)

    if global_matches > local_matches:
        confidence = 0.9 if global_matches >= 2 else 0.6
        return {
            "intent": "global",
            "entities": [],
            "reasoning": "Keyword-based fallback classification",
            "confidence": confidence,
        }
    elif local_matches > 0:
        confidence = 0.9 if local_matches >= 2 else 0.6
        return {
            "intent": "local",
            "entities": [],
            "reasoning": "Keyword-based fallback classification",
            "confidence": confidence,
        }
    else:
        return {
            "intent": "global",
            "entities": [],
            "reasoning": "Default fallback — no clear keyword signals",
            "confidence": 0.3,
        }


GLOBAL_ANSWER_PROMPT = """You are an expert Analytics Agent for an educational collaboration platform.

Based on the following community summaries from a knowledge graph, answer the user's question with a comprehensive, insightful analysis.

Be specific, cite community themes, and provide actionable insights when appropriate.
Write in a professional but accessible tone.

COMMUNITY SUMMARIES:
{context}

USER QUESTION: {question}"""


async def global_search(
    room_id: str, question: str, api_key: str, model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Global Search: Answer macro-level questions using community summaries.

    1. Embed the question
    2. Search Qdrant community_summaries collection
    3. Feed top K summaries as context to LLM
    """
    embedding_service = EmbeddingService(api_key=api_key)
    query_vector = await embedding_service.get_embedding(question)

    # Search community summaries
    results = await vector_store.search(
        collection=COMMUNITY_COLLECTION,
        query_vector=query_vector,
        limit=8,
        room_id=room_id,
    )

    if not results:
        return {
            "answer": "No knowledge graph data available for this room yet. Please build the graph first.",
            "sources": [],
        }

    # Build context from summaries
    context_parts = []
    sources = []
    for r in results:
        payload = r["payload"]
        title = payload.get("title", "Unknown")
        summary = payload.get("summary", "")
        findings = payload.get("key_findings", [])

        context_parts.append(f"## {title}\n{summary}\nKey findings: {', '.join(findings)}")
        sources.append(title)

    context = "\n\n".join(context_parts)

    # Generate answer
    async with AsyncOpenAI(api_key=api_key) as client:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": GLOBAL_ANSWER_PROMPT.format(context=context, question=question),
                },
            ],
        )

    answer = response.choices[0].message.content or "Unable to generate answer."
    return {"answer": answer, "sources": sources}


LOCAL_ANSWER_PROMPT = """You are an expert Analytics Agent for an educational collaboration platform.

Based on the following knowledge graph data (entities, relationships, and relevant conversation excerpts), answer the user's specific question.

Be precise, mention specific people/concepts, and trace the chain of events when relevant.

GRAPH CONTEXT:
{graph_context}

RELEVANT CONVERSATIONS:
{chunk_context}

USER QUESTION: {question}"""


async def local_search(
    room_id: str,
    question: str,
    entity_names: List[str],
    api_key: str,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    Local Search: Answer specific questions by traversing the knowledge graph.

    1. Find named entities in Neo4j
    2. Expand 2-hop subgraph
    3. Also search Qdrant chunks for supporting evidence
    4. LLM generates precise answer
    """
    embedding_service = EmbeddingService(api_key=api_key)

    # 1. Get subgraph from Neo4j
    subgraph = await neo4j_client.get_local_subgraph(room_id, entity_names, depth=2)
    nodes = subgraph.get("nodes", [])
    edges = subgraph.get("edges", [])

    # 2. Format graph context
    graph_parts = []
    for n in nodes:
        if n:
            graph_parts.append(
                f"Entity: {n.get('name', '?')} ({n.get('type', '?')}): {n.get('description', 'N/A')}"
            )
    for e in edges:
        if e:
            graph_parts.append(
                f"Relation: {e.get('source', '?')} --[{e.get('relation', '?')}]--> {e.get('target', '?')}: {e.get('evidence', 'N/A')}"
            )

    graph_context = (
        "\n".join(graph_parts) if graph_parts else "No graph data found for these entities."
    )

    # 3. Search relevant chunks for supporting text
    query_vector = await embedding_service.get_embedding(question)
    chunk_results = await vector_store.search(
        collection=CHUNK_COLLECTION,
        query_vector=query_vector,
        limit=5,
        room_id=room_id,
    )
    chunk_context = (
        "\n---\n".join([r["payload"].get("text", "") for r in chunk_results])
        or "No conversation excerpts found."
    )

    # 4. Generate answer
    async with AsyncOpenAI(api_key=api_key) as client:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": LOCAL_ANSWER_PROMPT.format(
                        graph_context=graph_context,
                        chunk_context=chunk_context,
                        question=question,
                    ),
                },
            ],
        )

    answer = response.choices[0].message.content or "Unable to generate answer."
    sources = entity_names + [n.get("name", "") for n in nodes if n]
    return {"answer": answer, "sources": list(set(sources))}


async def query_graph(
    room_id: str, question: str, api_key: str, model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Main entry point: classify intent -> route to global or local search.
    """
    intent = await classify_intent(question, api_key, model=model)
    logger.info(
        "graphrag_query",
        room_id=room_id,
        intent=intent["intent"],
        entities=intent.get("entities", []),
        confidence=intent.get("confidence"),
    )

    if intent["intent"] == "global":
        result = await global_search(room_id, question, api_key, model=model)
    else:
        result = await local_search(
            room_id, question, intent.get("entities", []), api_key, model=model
        )

    return {
        "answer": result["answer"],
        "intent": intent["intent"],
        "confidence": intent.get("confidence"),
        "sources": result.get("sources", []),
    }
