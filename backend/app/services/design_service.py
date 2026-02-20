from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.agent_config import AgentType
from app.models.user import User
from app.services.agent_config_service import AgentConfigService
from app.services.agents.system_agents import DesignAgent


class DesignAgentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.config_service = AgentConfigService(session)

    async def generate_prompt(
        self,
        request: Any,  # Typed as DesignRequest in API, but Any here to avoid circular dep if needed, or better define DTO
        user: User
    ) -> str:
        # 1. Get System Prompt for Design Agent
        if request.custom_system_prompt:
            sys_prompt = request.custom_system_prompt
        else:
            configs = await self.config_service.get_system_agent_configs(user)
            sys_config = next((c for c in configs if c.type == AgentType.DESIGN), None)
            sys_prompt = sys_config.system_prompt if sys_config else None

        # 2. Determine API Key & Model Provider
        params = await self._resolve_agent_params(request, user)
        api_key, provider, model = params

        if not api_key:
             raise HTTPException(
                status_code=400,
                detail="API Key is required. Please set it in the Design Agent settings for this course.",
            )

        # 3. Initialize Agent and Generate
        agent = DesignAgent(
            provider=provider, 
            api_key=api_key, 
            system_prompt=sys_prompt,
            model=model
        )

        try:
            return await agent.generate_system_prompt(
                target_agent_type=request.target_agent_type,
                context=request.course_context,
                requirement=request.requirement,
            )
        except Exception as e:
            if "401" in str(e) or "invalid api key" in str(e).lower():
                raise HTTPException(status_code=400, detail="Invalid API Key provided.") from e
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def _resolve_agent_params(self, request: Any, user: User) -> tuple[Optional[str], str, Optional[str]]:
        """
        Resolve API Key, Provider, and Model based on request and configuration hierarchy.
        Returns: (api_key, provider, model)
        """
        if request.custom_api_key:
            return (
                request.custom_api_key,
                request.custom_provider or request.provider,
                request.custom_model
            )

        api_key = request.api_key
        provider = request.provider
        model = None

        if not api_key:
            if getattr(request, 'project_id', None):
                project_configs = await self.config_service.get_project_agent_configs(request.project_id, user)
                design_config = next((c for c in project_configs if c.type == AgentType.DESIGN), None)
                if design_config:
                    api_key = design_config.encrypted_api_key
                    if not provider and design_config.model_provider:
                        provider = design_config.model_provider
                    if not model and design_config.model:
                        model = design_config.model
            else:
                configs = await self.config_service.get_system_agent_configs(user)
                sys_config = next((c for c in configs if c.type == AgentType.DESIGN), None)
                if sys_config:
                    api_key = sys_config.encrypted_api_key
                    if not provider and sys_config.model_provider:
                        provider = sys_config.model_provider
                    if not model and sys_config.model:
                        model = sys_config.model
        
        return api_key, provider, model
