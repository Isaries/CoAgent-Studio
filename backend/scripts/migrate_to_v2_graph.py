import asyncio
import logging
import uuid
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select, SQLModel
from app.core.config import settings
from app.models.agent_config import AgentConfig
from app.models.room import Room, RoomAgentLink
from app.models.workflow import RoomWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_rooms():
    engine = create_async_engine(str(settings.async_database_url), echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Get all rooms
        result = await session.execute(select(Room))
        rooms = result.scalars().all()
        
        migrated_count = 0
        for room in rooms:
            if getattr(room, "workflow_engine_version", None) == "v2_graph":
                continue
                
            logger.info(f"Migrating room {room.id} to v2_graph")
            
            # Update room version
            room.workflow_engine_version = "v2_graph"
            
            # Fetch agents for this room
            stmt = (
                select(AgentConfig)
                .join(RoomAgentLink, RoomAgentLink.agent_id == AgentConfig.id)
                .where(RoomAgentLink.room_id == room.id)
                .where(RoomAgentLink.is_active == True)
            )
            result = await session.execute(stmt)
            agents = result.scalars().all()
            
            teacher = next((a for a in agents if a.agent_type == "teacher"), None)
            student = next((a for a in agents if a.agent_type == "student"), None)
            
            nodes = []
            edges = []
            
            # Build graph data representing the legacy flow
            # Start -> Student -> Teacher -> End (if evaluate true) or back to student
            nodes.append({"id": "start", "type": "start", "position": {"x": 50, "y": 200}})
            
            if student:
                nodes.append({"id": str(student.id), "type": "agent", "config": {"agent_id": str(student.id)}, "position": {"x": 250, "y": 200}})
                edges.append({"id": f"edge-start-{student.id}", "source": "start", "target": str(student.id), "type": "forward"})
                
            if teacher:
                nodes.append({"id": str(teacher.id), "type": "agent", "config": {"agent_id": str(teacher.id)}, "position": {"x": 500, "y": 200}})
                if student:
                    edges.append({"id": f"edge-{student.id}-{teacher.id}", "source": str(student.id), "target": str(teacher.id), "type": "forward"})
            
            if teacher and student:
                # Add a logic router for teacher evaluation
                router_id = "router-teacher-eval"
                nodes.append({"id": router_id, "type": "router", "config": {"condition": "is_approved"}, "position": {"x": 750, "y": 200}})
                edges.append({"id": f"edge-{teacher.id}-{router_id}", "source": str(teacher.id), "target": router_id, "type": "forward"})
                
                # if approved -> end
                nodes.append({"id": "end", "type": "end", "position": {"x": 950, "y": 200}})
                edges.append({"id": f"edge-{router_id}-end", "source": router_id, "target": "end", "type": "evaluate", "condition": "approved"})
                
                # if rejected -> back to student
                edges.append({"id": f"edge-{router_id}-{student.id}", "source": router_id, "target": str(student.id), "type": "evaluate", "condition": "rejected"})
            else:
                # If only one agent or none
                nodes.append({"id": "end", "type": "end", "position": {"x": 750, "y": 200}})
                if student and not teacher:
                    edges.append({"id": f"edge-{student.id}-end", "source": str(student.id), "target": "end", "type": "forward"})
                elif teacher and not student:
                    edges.append({"id": f"edge-{teacher.id}-end", "source": str(teacher.id), "target": "end", "type": "forward"})
                else:
                    edges.append({"id": "edge-start-end", "source": "start", "target": "end", "type": "forward"})
            
            graph_data = {"nodes": nodes, "edges": edges}
            
            # Create RoomWorkflow
            workflow = RoomWorkflow(
                id=uuid.uuid4(),
                room_id=room.id,
                graph_data=graph_data,
                is_active=True
            )
            session.add(workflow)
            migrated_count += 1
            
        await session.commit()
        logger.info(f"Successfully migrated {migrated_count} rooms to v2_graph.")

if __name__ == "__main__":
    asyncio.run(migrate_rooms())
