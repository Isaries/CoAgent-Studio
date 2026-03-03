"""
Tier 1 — Structural Extractor

Derives graph nodes and edges directly from database relations.
Zero AI cost — purely deterministic.
"""

from typing import List
from uuid import UUID

import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.artifact import Artifact
from app.models.graph_schemas import EntityNode, EntityRelationship, GraphChunk
from app.models.message import Message
from app.models.room import RoomAgentLink, UserRoomLink
from app.models.agent_config import AgentConfig
from app.models.user import User

logger = structlog.get_logger()


async def extract_structural_facts(
    session: AsyncSession, room_id: str
) -> GraphChunk:
    """
    Query DB to derive nodes/edges from room membership, agents, and artifacts.

    Produces:
    - PERSON nodes from UserRoomLink + User
    - AGENT nodes from RoomAgentLink + AgentConfig
    - ARTIFACT nodes from Artifact + CREATES edges to creator
    - COLLABORATES_WITH edges from distinct message sender pairs
    """
    nodes: List[EntityNode] = []
    edges: List[EntityRelationship] = []
    seen_names: set = set()

    room_uuid = UUID(room_id) if isinstance(room_id, str) else room_id

    # ── PERSON nodes from room members ──
    stmt = (
        select(User.username, User.full_name, UserRoomLink.role)
        .join(UserRoomLink, User.id == UserRoomLink.user_id)
        .where(UserRoomLink.room_id == room_uuid)
    )
    result = await session.exec(stmt)
    members = list(result.all())

    for username, full_name, role in members:
        name = full_name or username
        if name.lower() not in seen_names:
            seen_names.add(name.lower())
            nodes.append(
                EntityNode(
                    name=name,
                    type="PERSON",
                    description=f"Room member with role: {role}",
                )
            )

    # ── AGENT nodes from assigned agents ──
    stmt = (
        select(AgentConfig.name, AgentConfig.type, AgentConfig.category)
        .join(RoomAgentLink, AgentConfig.id == RoomAgentLink.agent_id)
        .where(RoomAgentLink.room_id == room_uuid)
        .where(RoomAgentLink.is_active == True)  # noqa: E712
    )
    result = await session.exec(stmt)
    agents = list(result.all())

    for agent_name, agent_type, agent_category in agents:
        if agent_name.lower() not in seen_names:
            seen_names.add(agent_name.lower())
            nodes.append(
                EntityNode(
                    name=agent_name,
                    type="AGENT",
                    description=f"{agent_type or ''} agent ({agent_category or 'utility'})",
                )
            )

    # ── ARTIFACT nodes + CREATES edges ──
    stmt = (
        select(Artifact.title, Artifact.type, User.username, User.full_name)
        .outerjoin(User, Artifact.created_by == User.id)
        .where(Artifact.room_id == room_uuid)
        .where(Artifact.is_deleted == False)  # noqa: E712
    )
    result = await session.exec(stmt)
    artifacts = list(result.all())

    for title, art_type, creator_username, creator_full_name in artifacts:
        if title.lower() not in seen_names:
            seen_names.add(title.lower())
            nodes.append(
                EntityNode(
                    name=title,
                    type="ARTIFACT",
                    description=f"{art_type} artifact",
                )
            )
        creator = creator_full_name or creator_username
        if creator:
            edges.append(
                EntityRelationship(
                    source=creator,
                    target=title,
                    relation="CREATES",
                    evidence=f"{creator} created artifact '{title}'",
                    strength=1.0,
                )
            )

    # ── COLLABORATES_WITH edges from message sender pairs ──
    stmt = (
        select(Message.sender_id)
        .where(Message.room_id == room_uuid)
        .where(Message.sender_id.isnot(None))
        .distinct()
    )
    result = await session.exec(stmt)
    sender_ids = list(result.all())

    if len(sender_ids) > 1:
        # Resolve sender IDs to names
        sender_names: List[str] = []
        for (sid,) in sender_ids if isinstance(sender_ids[0], tuple) else [(s,) for s in sender_ids]:
            user = await session.get(User, sid)
            if user:
                sender_names.append(user.full_name or user.username)

        # Create pairwise COLLABORATES_WITH edges
        for i in range(len(sender_names)):
            for j in range(i + 1, len(sender_names)):
                edges.append(
                    EntityRelationship(
                        source=sender_names[i],
                        target=sender_names[j],
                        relation="COLLABORATES_WITH",
                        evidence=f"{sender_names[i]} and {sender_names[j]} both participate in this room",
                        strength=0.8,
                    )
                )

    logger.info(
        "structural_extraction_complete",
        room_id=room_id,
        nodes=len(nodes),
        edges=len(edges),
    )
    return GraphChunk(nodes=nodes, edges=edges)
