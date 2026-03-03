from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.core.security import decrypt_api_key
from app.services.agents.system_agents import AnalyticsAgent
from app.models.agent_config import AgentConfig, AgentType
from app.models.analytics import AnalyticsReport
from app.models.space import Space
from app.models.message import Message
from app.models.room import Room
from app.models.user import User, UserRole

router = APIRouter()


@router.post("/{space_id}/generate", response_model=AnalyticsReport)
async def generate_space_analytics(
    space_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> AnalyticsReport:  # type: ignore[func-returns-value]
    """
    Trigger analysis for the entire space (all rooms).
    For MVP, we also just pick the first room to demonstrate specific room analysis.
    """
    space = await session.get(Space, space_id)  # type: ignore[func-returns-value]
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # Check permissions (Teacher or Admin)
    # Allow TA to view
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.TEACHER]:
        from app.models.space import UserSpaceLink

        link = await session.get(UserSpaceLink, (current_user.id, space_id))
        if not link or link.role != "ta":
            raise HTTPException(status_code=403, detail="Not enough permissions")

    # 1. Get System Analytics Agent Config
    sys_query = select(AgentConfig).where(
        AgentConfig.project_id == None, AgentConfig.type == AgentType.ANALYTICS
    )
    sys_result = await session.exec(sys_query)
    sys_config = sys_result.first()

    prompt = sys_config.system_prompt if sys_config else None
    encrypted_key = sys_config.encrypted_api_key if sys_config else None

    if not encrypted_key:
        raise HTTPException(
            status_code=400, detail="Analytics Agent not configured (Missing API Key)"
        )

    # Decrypt the API key before use
    key = decrypt_api_key(encrypted_key)
    if not key:
        raise HTTPException(
            status_code=500, detail="Failed to decrypt Analytics Agent API key"
        )

    # 2. Initialize Agent
    agent = AnalyticsAgent(provider="gemini", api_key=key, system_prompt=prompt)

    # 3. Gather Data (All messages from all rooms in space)
    # For MVP, let's limit to the "most active" room or just fetch all
    rooms_query = select(Room).where(Room.space_id == space_id)
    rooms_res = await session.exec(rooms_query)
    rooms = rooms_res.all()

    combined_report = f"# Space Analytics Report: {space.title}\n\n"

    for room in rooms:
        msgs_query = (
            select(Message)
            .where(Message.room_id == room.id)
            .order_by(col(Message.created_at).desc())
            .limit(50)
        )
        msgs_res = await session.exec(msgs_query)
        messages = list(reversed(msgs_res.all()))

        if not messages:
            continue

        room_analysis = await agent.analyze_room(messages)
        combined_report += f"## Room: {room.name}\n{room_analysis}\n\n"

    # 4. Save Report
    report = AnalyticsReport(
        space_id=space_id, content=combined_report, report_type="space_summary"
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)

    return report


@router.get("/{space_id}", response_model=List[AnalyticsReport])
async def read_analytics_reports(
    space_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    query: Any = (
        select(AnalyticsReport)
        .where(AnalyticsReport.space_id == space_id)
        .order_by(col(AnalyticsReport.created_at).desc())
    )
    result = await session.exec(query)
    return result.all()


@router.delete("/reports/{report_id}", status_code=204)
async def delete_analytics_report(
    report_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> None:
    """
    Delete an analytics report by ID.
    Only accessible by Teacher, Admin, or Super Admin roles.
    """
    report = await session.get(AnalyticsReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Analytics report not found")

    # Check permissions (same as generate endpoint)
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.TEACHER]:
        from app.models.space import UserSpaceLink

        link = await session.get(UserSpaceLink, (current_user.id, report.space_id))
        if not link or link.role != "ta":
            raise HTTPException(status_code=403, detail="Not enough permissions")

    await session.delete(report)
    await session.commit()
    return None
