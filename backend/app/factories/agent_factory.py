from typing import Dict, List, Optional
from uuid import UUID

from app.core.agent_core import AgentCore
from app.services.agents.std_agents import (
    StudentAgent,
    TeacherAgent,
)
from app.models.agent_config import AgentConfig, AgentType


class AgentFactory:
    """
    Factory to create Agent instances based on AgentConfig.
    Enables Polymorphism and easy extension.
    """

    @staticmethod
    def create_agent(config: AgentConfig, api_keys: Optional[List[str]] = None) -> Optional[AgentCore]:
        # Fallback to legacy single key if no list provided
        # But if list provided, it takes precedence or complements?
        # Logic: If api_keys provided, pass it. If config.encrypted_api_key exists, pass it too.
        # AgentCore handles merging.
        
        legacy_key = config.encrypted_api_key
        
        # If neither exist, return None
        if not legacy_key and not api_keys:
             return None
        
        # Determine provider parameters
        if config.type == AgentType.TEACHER:
            return TeacherAgent(
                provider=config.model_provider,
                api_key=legacy_key,
                api_keys=api_keys,
                system_prompt=config.system_prompt,
                model=config.model,
            )
        elif config.type == AgentType.STUDENT:
            return StudentAgent(
                provider=config.model_provider,
                api_key=legacy_key,
                api_keys=api_keys,
                system_prompt=config.system_prompt,
                model=config.model,
            )

        # DesignAgent / AnalyticsAgent could be added here

        return None

    @staticmethod
    def create_agents_map(
        teacher_config: Optional[AgentConfig], 
        student_config: Optional[AgentConfig],
        keys_map: Optional[Dict[UUID, List[str]]] = None
    ) -> Dict[AgentType, AgentCore]:
        """
        Helper to create a map of available agents.
        keys_map: Mapping from AgentConfig.id to list of decrypted keys.
        """
        agents: Dict[AgentType, AgentCore] = {}
        keys_map = keys_map or {}

        if teacher_config:
            t_keys = keys_map.get(teacher_config.id)
            agent = AgentFactory.create_agent(teacher_config, api_keys=t_keys)
            if agent:
                agents[AgentType.TEACHER] = agent

        if student_config:
            s_keys = keys_map.get(student_config.id)
            agent = AgentFactory.create_agent(student_config, api_keys=s_keys)
            if agent:
                agents[AgentType.STUDENT] = agent

        return agents
