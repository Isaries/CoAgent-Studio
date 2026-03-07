"""
Tier 3 — LLM Extractor

Refactored LLM extraction that receives known entities from Tier 1+2
to avoid redundant extraction. Focuses on CONCEPT nodes and semantic
relationship classification. Accepts a configurable model parameter.
"""

from typing import List

import instructor
import structlog
from openai import AsyncOpenAI

from app.models.graph_schemas import CommunityReport, EntityNode, GraphChunk

logger = structlog.get_logger()

EXTRACTION_SYSTEM_PROMPT = """You are an expert knowledge graph extractor for an educational collaboration platform.

Given a conversation chunk between students, teachers, and AI agents, extract:
1. ENTITIES: Concepts/Topics discussed, abstract ideas, learning objectives, design patterns, methodologies — things NOT already in the known entities list.
2. RELATIONSHIPS: How entities (including known ones) relate to each other (DISCUSSES, CREATES, RESOLVES, STRUGGLES_WITH, MENTIONS, COLLABORATES_WITH, DEPENDS_ON).

Rules:
- Use canonical names (e.g., "Alice" not "alice" or "A")
- Merge similar concepts (e.g., "PostgreSQL" and "Postgres" → "PostgreSQL")
- Focus on substantive relationships, skip trivial greetings
- Each evidence field should be a direct quote or close paraphrase
- Focus on CONCEPT-type entities — higher-level ideas, topics, patterns
- You may create relationships TO or FROM known entities, but do NOT re-extract them as new nodes"""


async def extract_concepts_from_chunk(
    chunk_text: str,
    known_nodes: List[EntityNode],
    api_key: str,
    model: str = "gpt-4o-mini",
) -> GraphChunk:
    """
    Use instructor + OpenAI to extract structured concepts & relationships.

    Args:
        chunk_text: The conversation chunk to analyze.
        known_nodes: Entities already found by Tier 1+2 (passed in prompt to avoid duplication).
        api_key: OpenAI API key.
        model: Model to use for extraction (configurable per-room).

    Returns:
        GraphChunk with new CONCEPT nodes and relationships.
    """
    client = instructor.from_openai(AsyncOpenAI(api_key=api_key, timeout=60.0))

    known_list = "\n".join(f"- {n.name} ({n.type})" for n in known_nodes) if known_nodes else "None"

    user_prompt = f"""The following entities are already known — do NOT re-extract these as nodes:

{known_list}

Extract NEW concepts and relationships from this conversation:

{chunk_text}"""

    result = await client.chat.completions.create(
        model=model,
        response_model=GraphChunk,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_retries=2,
        max_tokens=2048,
    )

    # Validate the response
    if not result or not hasattr(result, "nodes"):
        logger.warning("llm_extractor_invalid_response", detail="LLM returned invalid GraphChunk")
        return GraphChunk(nodes=[], edges=[])

    # Filter out entities missing required fields
    valid_nodes = [e for e in result.nodes if e.name and e.type]
    if len(valid_nodes) < len(result.nodes):
        logger.warning(
            "llm_extractor_filtered_entities",
            total=len(result.nodes),
            valid=len(valid_nodes),
        )
    result.nodes = valid_nodes

    # Filter out edges missing required fields
    valid_edges = [e for e in result.edges if e.source and e.target and e.relation]
    if len(valid_edges) < len(result.edges):
        logger.warning(
            "llm_extractor_filtered_edges",
            total=len(result.edges),
            valid=len(valid_edges),
        )
    result.edges = valid_edges

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
    model: str = "gpt-4o-mini",
    level: int = 0,
) -> CommunityReport:
    """Generate a structured community report using instructor with configurable model."""
    client = instructor.from_openai(AsyncOpenAI(api_key=api_key, timeout=60.0))

    prompt = f"""Community #{community_id} contains these entities and relationships:

ENTITIES:
{nodes_text}

RELATIONSHIPS:
{edges_text}

Generate a comprehensive analytical report for this community."""

    result = await client.chat.completions.create(
        model=model,
        response_model=CommunityReport,
        messages=[
            {"role": "system", "content": COMMUNITY_SUMMARY_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_retries=2,
        max_tokens=2048,
    )
    result.community_id = community_id
    result.level = level
    return result
