"""
Tier 2 — NLP Extractor

Uses spaCy NER + domain dictionaries to extract entities from message text.
No API cost — runs locally.
"""

from typing import Dict, List, Set

import structlog

from app.models.graph_schemas import EntityNode, EntityRelationship, GraphChunk

logger = structlog.get_logger()

# Lazy-loaded spaCy model singleton
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy

        _nlp = spacy.load("en_core_web_sm")
    return _nlp


# ── Domain dictionaries ──

TECH_DICTIONARY: Set[str] = {
    # Languages
    "python",
    "javascript",
    "typescript",
    "java",
    "rust",
    "go",
    "c++",
    "c#",
    "ruby",
    "php",
    "swift",
    "kotlin",
    "scala",
    "haskell",
    "elixir",
    # Frameworks & Libraries
    "react",
    "vue",
    "angular",
    "django",
    "flask",
    "fastapi",
    "express",
    "next.js",
    "nuxt",
    "spring",
    "rails",
    "laravel",
    "svelte",
    # Databases
    "postgresql",
    "postgres",
    "mysql",
    "mongodb",
    "redis",
    "neo4j",
    "sqlite",
    "qdrant",
    "elasticsearch",
    "dynamodb",
    "cassandra",
    # Infrastructure
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "terraform",
    "nginx",
    "kafka",
    "rabbitmq",
    "graphql",
    "rest",
    "grpc",
    # AI/ML
    "openai",
    "langchain",
    "langgraph",
    "pytorch",
    "tensorflow",
    "huggingface",
    "gpt-4",
    "gpt-4o",
    "claude",
    "llm",
    "rag",
    # Tools
    "git",
    "github",
    "gitlab",
    "jira",
    "figma",
    "vscode",
    "webpack",
    "vite",
    "npm",
    "yarn",
    "pip",
}

ISSUE_KEYWORDS: Set[str] = {
    "bug",
    "error",
    "issue",
    "problem",
    "crash",
    "failure",
    "timeout",
    "bottleneck",
    "vulnerability",
    "regression",
    "deadlock",
    "memory leak",
    "race condition",
    "exception",
    "broken",
}


def extract_nlp_facts(messages: List[Dict[str, str]]) -> GraphChunk:
    """
    Extract entities from message text using spaCy NER + domain dictionaries.

    Args:
        messages: List of dicts with 'sender' and 'content' keys.

    Returns:
        GraphChunk with PERSON, TECHNOLOGY, and ISSUE nodes + MENTIONS edges.
    """
    nlp = _get_nlp()
    nodes: List[EntityNode] = []
    edges: List[EntityRelationship] = []
    seen_names: Set[str] = set()

    for msg in messages:
        sender = msg["sender"]
        content = msg["content"]
        doc = nlp(content)

        # ── spaCy NER → PERSON nodes ──
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text.strip()
                if name.lower() not in seen_names and len(name) > 1:
                    seen_names.add(name.lower())
                    nodes.append(
                        EntityNode(
                            name=name,
                            type="PERSON",
                            description="Person mentioned in conversation",
                        )
                    )
                    edges.append(
                        EntityRelationship(
                            source=sender,
                            target=name,
                            relation="MENTIONS",
                            evidence=f"{sender} mentioned {name}",
                            strength=0.6,
                        )
                    )

        # ── Tech dictionary matching → TECHNOLOGY nodes ──
        content_lower = content.lower()
        for tech in TECH_DICTIONARY:
            if tech in content_lower and tech not in seen_names:
                seen_names.add(tech)
                # Use canonical casing
                canonical = tech.upper() if len(tech) <= 4 else tech.title()
                nodes.append(
                    EntityNode(
                        name=canonical,
                        type="TECHNOLOGY",
                        description="Technology mentioned in discussion",
                    )
                )
                edges.append(
                    EntityRelationship(
                        source=sender,
                        target=canonical,
                        relation="MENTIONS",
                        evidence=f"{sender} discussed {canonical}",
                        strength=0.6,
                    )
                )

        # ── Issue keyword matching → ISSUE nodes ──
        for keyword in ISSUE_KEYWORDS:
            if keyword in content_lower and keyword not in seen_names:
                seen_names.add(keyword)
                issue_name = keyword.title()
                nodes.append(
                    EntityNode(
                        name=issue_name,
                        type="ISSUE",
                        description=f"Issue/problem type: {keyword}",
                    )
                )
                edges.append(
                    EntityRelationship(
                        source=sender,
                        target=issue_name,
                        relation="MENTIONS",
                        evidence=f"{sender} referenced a {keyword}",
                        strength=0.6,
                    )
                )

    logger.info(
        "nlp_extraction_complete",
        nodes=len(nodes),
        edges=len(edges),
    )
    return GraphChunk(nodes=nodes, edges=edges)
