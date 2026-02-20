"""
Agent Registry Service.

Provides centralized management for agent types and instances.
Supports both internal and external agents with caching.
"""

import structlog
from typing import Dict, List, Optional
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.agent_config import AgentConfig, AgentCategory
from app.models.agent_type_metadata import AgentTypeMetadata, AgentTypeMetadataRead, AgentTypeMetadataCreate

logger = structlog.get_logger()


class AgentRegistry:
    """
    Centralized registry for agent types and configurations.
    
    Responsibilities:
    - List available agent types (system + custom)
    - CRUD for custom agent types
    - Lookup agent configs by type or ID
    - Cache frequently accessed metadata
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
        self._type_cache: Dict[str, AgentTypeMetadata] = {}
    
    # === Agent Type Management ===
    
    async def list_agent_types(
        self,
        category: Optional[str] = None,
        include_system: bool = True,
    ) -> List[AgentTypeMetadataRead]:
        """
        List all available agent types.
        
        Args:
            category: Filter by category (instructor, participant, utility, external)
            include_system: Whether to include system-defined types
        """
        query = select(AgentTypeMetadata)
        
        if category:
            query = query.where(AgentTypeMetadata.category == category)
        
        if not include_system:
            query = query.where(AgentTypeMetadata.is_system == False)
        
        query = query.order_by(AgentTypeMetadata.is_system.desc(), AgentTypeMetadata.display_name)
        
        result = await self._session.exec(query)
        types = result.all()
        
        return [AgentTypeMetadataRead.model_validate(t) for t in types]
    
    async def get_agent_type(self, type_name: str) -> Optional[AgentTypeMetadata]:
        """Get metadata for a specific agent type."""
        # Check cache first
        if type_name in self._type_cache:
            return self._type_cache[type_name]
        
        query = select(AgentTypeMetadata).where(AgentTypeMetadata.type_name == type_name)
        result = await self._session.exec(query)
        type_meta = result.first()
        
        if type_meta:
            self._type_cache[type_name] = type_meta
        
        return type_meta
    
    async def create_agent_type(
        self,
        data: AgentTypeMetadataCreate,
        created_by: UUID,
    ) -> AgentTypeMetadata:
        """Create a new custom agent type."""
        # Check for duplicate
        existing = await self.get_agent_type(data.type_name)
        if existing:
            raise ValueError(f"Agent type '{data.type_name}' already exists")
        
        type_meta = AgentTypeMetadata(
            type_name=data.type_name,
            display_name=data.display_name,
            description=data.description,
            category=data.category,
            icon=data.icon,
            color=data.color,
            default_system_prompt=data.default_system_prompt,
            default_model_provider=data.default_model_provider,
            default_model=data.default_model,
            default_settings=data.default_settings,
            default_capabilities=data.default_capabilities,
            created_by=created_by,
            is_system=False,
        )
        
        self._session.add(type_meta)
        await self._session.commit()
        await self._session.refresh(type_meta)
        
        # Update cache
        self._type_cache[data.type_name] = type_meta
        
        logger.info("agent_type_created", type_name=data.type_name, category=data.category)
        return type_meta
    
    async def delete_agent_type(self, type_name: str) -> bool:
        """
        Delete a custom agent type.
        System types cannot be deleted.
        """
        type_meta = await self.get_agent_type(type_name)
        
        if not type_meta:
            return False
        
        if type_meta.is_system:
            raise ValueError(f"Cannot delete system type '{type_name}'")
        
        await self._session.delete(type_meta)
        await self._session.commit()
        
        # Clear from cache
        self._type_cache.pop(type_name, None)
        
        logger.info("agent_type_deleted", type_name=type_name)
        return True
    
    # === Agent Config Helpers ===
    
    async def get_agents_by_type(
        self,
        type_name: str,
        project_id: Optional[UUID] = None,
    ) -> List[AgentConfig]:
        """Get all agent configs of a specific type."""
        query = select(AgentConfig).where(AgentConfig.type == type_name)
        
        if project_id:
            query = query.where(AgentConfig.project_id == project_id)
        
        result = await self._session.exec(query)
        return list(result.all())
    
    async def get_external_agents(
        self,
        project_id: Optional[UUID] = None,
    ) -> List[AgentConfig]:
        """Get all external agents (for A2A routing)."""
        query = select(AgentConfig).where(AgentConfig.is_external == True)
        
        if project_id:
            query = query.where(AgentConfig.project_id == project_id)
        
        result = await self._session.exec(query)
        return list(result.all())
    
    def invalidate_cache(self, type_name: Optional[str] = None):
        """Clear type metadata cache."""
        if type_name:
            self._type_cache.pop(type_name, None)
        else:
            self._type_cache.clear()
