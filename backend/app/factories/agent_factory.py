from typing import Dict, Optional

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
    def create_agent(config: AgentConfig) -> Optional[AgentCore]:
        if not config or not config.is_active or not config.encrypted_api_key:
            return None

        if config.type == AgentType.TEACHER:
            return TeacherAgent(
                provider=config.model_provider,
                api_key=config.encrypted_api_key,
                system_prompt=config.system_prompt,
                model=config.model,
            )
        elif config.type == AgentType.STUDENT:
            return StudentAgent(
                provider=config.model_provider,
                api_key=config.encrypted_api_key,
                system_prompt=config.system_prompt,
                model=config.model,
            )

        # DesignAgent / AnalyticsAgent could be added here

        return None

    @staticmethod
    def create_agents_map(
        teacher_config: Optional[AgentConfig], student_config: Optional[AgentConfig]
    ) -> Dict[AgentType, AgentCore]:
        """
        Helper to create a map of available agents.
        """
        agents: Dict[AgentType, AgentCore] = {}

        if teacher_config:
            agent = AgentFactory.create_agent(teacher_config)
            if agent:
                agents[AgentType.TEACHER] = agent

        if student_config:
            agent = AgentFactory.create_agent(student_config)
            if agent:
                agents[AgentType.STUDENT] = agent

        return agents
