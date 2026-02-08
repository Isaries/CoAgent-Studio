from typing import Any, Dict, List, Optional, Union

from app.models.agent_config import AgentConfig, AgentType, AgentCategory
from app.models.message import Message


class AgentOrchestrator:
    """
    Pure logic component to decide the next action based on state.
    
    Supports dynamic agent list - not limited to Teacher/Student.
    Priority order: INSTRUCTOR > PARTICIPANT > EXTERNAL > UTILITY
    """

    # Priority order for agent categories
    CATEGORY_PRIORITY = [
        AgentCategory.INSTRUCTOR,
        AgentCategory.PARTICIPANT,
        AgentCategory.EXTERNAL,
        AgentCategory.UTILITY,
    ]

    @staticmethod
    async def decide_turn(
        room,
        agents: Dict[Union[AgentType, str], Any],  # Map[AgentType/id, AgentCore/Adapter]
        configs: Dict[Union[AgentType, str], AgentConfig],  # Map[AgentType/id, AgentConfig]
        history: List[Message],
        msg_gap: int,
    ) -> Optional[dict]:
        """
        Decide who speaks next from all available agents.
        
        Returns:
            dict with 'role', 'action', 'agent', 'config' or None
        """
        # Build list of (agent, config) sorted by priority
        candidates = []
        
        for key, agent in agents.items():
            config = configs.get(key)
            if not config:
                continue
            
            # Determine category
            category = AgentCategory(config.category) if config.category else AgentCategory.UTILITY
            priority = AgentOrchestrator.CATEGORY_PRIORITY.index(category) if category in AgentOrchestrator.CATEGORY_PRIORITY else 99
            
            candidates.append((priority, key, agent, config))
        
        # Sort by priority (lower = higher priority)
        candidates.sort(key=lambda x: x[0])
        
        # Evaluate each candidate
        for priority, key, agent, config in candidates:
            decision = await AgentOrchestrator._evaluate_agent(
                room, agent, config, history, msg_gap
            )
            if decision:
                return decision
        
        return None

    @staticmethod
    async def _evaluate_agent(
        room,
        agent: Any,
        config: AgentConfig,
        history: List[Message],
        msg_gap: int,
    ) -> Optional[dict]:
        """
        Evaluate if a specific agent should act.
        """
        # Check room mode compatibility
        agent_type = config.type
        
        # Legacy mode checks for teacher/student
        if agent_type == AgentType.TEACHER or agent_type == "teacher":
            if room.ai_mode not in ["teacher_only", "both"]:
                return None
        elif agent_type == AgentType.STUDENT or agent_type == "student":
            if room.ai_mode != "both":
                return None
        # External agents always allowed when room.ai_mode != "off"
        # (already checked at higher level)
        
        # Check trigger conditions
        should_run = False
        trigger = config.trigger_config or {}
        
        if trigger.get("type") == "message_count":
            should_run = msg_gap >= trigger.get("value", 10)
        elif trigger.get("type") == "time_based":
            # Time-based triggers handled by room_monitor
            pass
        elif not trigger:
            # Default: use agent's internal logic if available
            if hasattr(agent, "should_reply"):
                should_run = agent.should_reply(history, room.ai_frequency)
            else:
                # External agents: check every message
                should_run = config.is_external and len(history) > 0
        
        if should_run:
            # Determine action based on agent category
            category = config.category or "instructor"
            
            if category == AgentCategory.PARTICIPANT or category == "participant":
                action = "propose"
            elif config.is_external:
                action = "notify"  # External agents get notified
            else:
                action = "reply"
            
            return {
                "role": config.type,
                "action": action,
                "agent": agent,
                "config": config,
            }
        
        return None

    @staticmethod
    def get_action_for_category(category: str) -> str:
        """Get default action for agent category."""
        actions = {
            "instructor": "reply",
            "participant": "propose",
            "external": "notify",
            "utility": "execute",
        }
        return actions.get(category, "reply")

