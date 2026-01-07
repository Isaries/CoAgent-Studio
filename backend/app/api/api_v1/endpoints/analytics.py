from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Any, List
from uuid import UUID
from app.api import deps
from app.models.user import User, UserRole
from app.models.course import Course
from app.models.room import Room
from app.models.message import Message
from app.models.agent_config import AgentConfig, AgentType
from app.models.analytics import AnalyticsReport
from app.core.specialized_agents import AnalyticsAgent

router = APIRouter()

@router.post("/{course_id}/generate", response_model=AnalyticsReport)
async def generate_course_analytics(
    course_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Trigger analysis for the entire course (all rooms). 
    For MVP, we also just pick the first room to demonstrate specific room analysis.
    """
    course = await session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    # Check permissions (Teacher or Admin)
    # if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER] ... (Simplified)

    # 1. Get Analytics Agent Config
    query = select(AgentConfig).where(AgentConfig.course_id == course_id, AgentConfig.type == AgentType.ANALYTICS)
    result = await session.exec(query)
    config = result.first()
    
    if not config or not config.encrypted_api_key:
        raise HTTPException(status_code=400, detail="Analytics Agent not configured for this course")

    # 2. Initialize Agent
    agent = AnalyticsAgent(provider=config.model_provider, api_key=config.encrypted_api_key)
    
    # 3. Gather Data (All messages from all rooms in course)
    # For MVP, let's limit to the "most active" room or just fetch all
    rooms_query = select(Room).where(Room.course_id == course_id)
    rooms_res = await session.exec(rooms_query)
    rooms = rooms_res.all()
    
    combined_report = f"# Course Analytics Report: {course.title}\n\n"
    
    for room in rooms:
        msgs_query = select(Message).where(Message.room_id == room.id).order_by(Message.created_at.desc()).limit(50)
        msgs_res = await session.exec(msgs_query)
        messages = list(reversed(msgs_res.all()))
        
        if not messages:
            continue
            
        room_analysis = await agent.analyze_room(messages)
        combined_report += f"## Room: {room.name}\n{room_analysis}\n\n"
    
    # 4. Save Report
    report = AnalyticsReport(
        course_id=course_id,
        content=combined_report,
        report_type="course_summary"
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    
    return report

@router.get("/{course_id}", response_model=List[AnalyticsReport])
async def read_analytics_reports(
    course_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    query = select(AnalyticsReport).where(AnalyticsReport.course_id == course_id).order_by(AnalyticsReport.created_at.desc())
    result = await session.exec(query)
    return result.all()
