"""
GraphRAG Pydantic Schemas — Structured LLM extraction models.

Used with the `instructor` library to force LLM output into strict JSON
conforming to these schemas.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# --- Entity & Relationship Extraction ---

class EntityNode(BaseModel):
    """A single entity extracted from conversation text."""
    name: str = Field(description="Canonical name of the entity (e.g. 'Alice', 'PostgreSQL', 'JWT Token')")
    type: str = Field(description="Entity type: PERSON, AGENT, CONCEPT, TECHNOLOGY, ARTIFACT, ISSUE")
    description: str = Field(description="Brief description of this entity in context")


class EntityRelationship(BaseModel):
    """A directional relationship between two entities."""
    source: str = Field(description="Name of the source entity")
    target: str = Field(description="Name of the target entity")
    relation: str = Field(description="Relationship type: DISCUSSES, CREATES, RESOLVES, STRUGGLES_WITH, MENTIONS, COLLABORATES_WITH, DEPENDS_ON")
    evidence: str = Field(description="One-sentence evidence from the original text")
    strength: float = Field(default=1.0, ge=0.0, le=1.0, description="Relationship strength 0-1")


class GraphChunk(BaseModel):
    """Structured extraction result from a single text chunk."""
    nodes: List[EntityNode] = Field(default_factory=list, description="Entities found in this chunk")
    edges: List[EntityRelationship] = Field(default_factory=list, description="Relationships between entities")


# --- Community Summarization ---

class CommunityReport(BaseModel):
    """LLM-generated summary of a graph community (cluster of related entities)."""
    community_id: int = Field(description="Numeric community ID from Leiden clustering")
    title: str = Field(description="Short title for this community theme")
    summary: str = Field(description="Multi-paragraph summary of what this community represents")
    key_findings: List[str] = Field(default_factory=list, description="Bullet-point key findings")
    key_entities: List[str] = Field(default_factory=list, description="Most important entity names in this community")
    level: int = Field(default=0, description="Hierarchy level (0 = leaf, higher = more abstract)")


# --- Query Intent ---

class QueryIntent(BaseModel):
    """Classification of a user question for routing."""
    intent: str = Field(description="Either 'global' or 'local'")
    entities: List[str] = Field(default_factory=list, description="Entity names mentioned in the question (for local search)")
    reasoning: str = Field(description="Brief explanation of classification")


# --- API Response Models ---

class GraphNodeResponse(BaseModel):
    """Node data for frontend visualization."""
    id: str
    name: str
    type: str
    description: str
    community_id: Optional[int] = None


class GraphEdgeResponse(BaseModel):
    """Edge data for frontend visualization."""
    source: str
    target: str
    relation: str
    evidence: str


class GraphDataResponse(BaseModel):
    """Full graph payload for frontend rendering."""
    nodes: List[GraphNodeResponse] = Field(default_factory=list)
    edges: List[GraphEdgeResponse] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


class GraphStatusResponse(BaseModel):
    """Graph indexing status for a room."""
    room_id: str
    node_count: int = 0
    edge_count: int = 0
    community_count: int = 0
    last_updated: Optional[str] = None
    is_building: bool = False


class GraphQueryRequest(BaseModel):
    """Request body for graph query endpoint."""
    question: str


class GraphQueryResponse(BaseModel):
    """Response from the Analytics Agent graph query."""
    answer: str
    intent: str  # "global" or "local"
    sources: List[str] = Field(default_factory=list, description="Key entities or communities referenced")
