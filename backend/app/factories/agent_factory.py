from typing import Any, Dict, List, Optional, Union
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
    Supports internal agents (Teacher, Student) and external agents via HTTP webhook.
    """

    @staticmethod
    def create_agent(config: AgentConfig, api_keys: Optional[List[str]] = None) -> Optional[Union[AgentCore, Any]]:
        """
        Create an agent based on the config.
        
        For external agents (is_external=True), returns an ExternalAgentAdapter.
        For internal agents, returns the appropriate AgentCore subclass.
        
        Returns None if agent cannot be created (missing keys for internal agents).
        """
        # Handle external agents first - they don't need API keys
        if config.is_external and config.external_config:
            from app.core.a2a.external_adapter import ExternalAgentAdapter
            return ExternalAgentAdapter(config)
        
        # For internal agents, check for API keys
        legacy_key = config.encrypted_api_key
        
        # If neither exist, return None
        if not legacy_key and not api_keys:
             return None
        
        # Normalize type to enum for consistent comparison
        agent_type = config.type
        if isinstance(agent_type, str):
            try:
                agent_type = AgentType(agent_type.lower())
            except ValueError:
                return None  # Unknown agent type
        
        # Create agent based on type
        if agent_type == AgentType.TEACHER:
            return TeacherAgent(
                provider=config.model_provider,
                api_key=legacy_key,
                api_keys=api_keys,
                system_prompt=config.system_prompt,
                model=config.model,
            )
        elif agent_type == AgentType.STUDENT:
            return StudentAgent(
                provider=config.model_provider,
                api_key=legacy_key,
                api_keys=api_keys,
                system_prompt=config.system_prompt,
                model=config.model,
            )

        # DesignAgent / AnalyticsAgent / Custom agents could be added here

        # v2 fallback: create a generic AgentCore for dynamically-typed agents
        # This enables the LangGraph workflow engine to use any agent config
        return AgentCore(
            provider=config.model_provider,
            api_key=legacy_key,
            api_keys=api_keys,
            system_prompt=config.system_prompt,
            model=config.model,
        )

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

    @staticmethod
    def create_all_agents_map(
        configs: List[AgentConfig],
        keys_map: Optional[Dict[UUID, List[str]]] = None,
    ) -> Dict[Union[AgentType, str], Any]:
        """
        Create a map of all agents from a list of configs.
        
        Returns a dict keyed by AgentType for standard agents,
        or by config.id (as string) for external/custom agents.
        
        Args:
            configs: List of all agent configs to instantiate
            keys_map: Mapping from AgentConfig.id to list of decrypted keys
            
        Returns:
            Dict mapping agent identifier to agent instance
        """
        agents: Dict[Union[AgentType, str], Any] = {}
        keys_map = keys_map or {}
        
        for config in configs:
            if not config:
                continue
                
            agent_keys = keys_map.get(config.id)
            agent = AgentFactory.create_agent(config, api_keys=agent_keys)
            
            if agent:
                # Use AgentType enum for standard types, string ID for others
                if config.type in [AgentType.TEACHER.value, AgentType.TEACHER]:
                    agents[AgentType.TEACHER] = agent
                elif config.type in [AgentType.STUDENT.value, AgentType.STUDENT]:
                    agents[AgentType.STUDENT] = agent
                else:
                    # External or custom agents keyed by ID
                    agents[str(config.id)] = agent
        
        return agents

