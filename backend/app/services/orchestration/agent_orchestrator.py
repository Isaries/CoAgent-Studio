from typing import Any, Dict, List, Optional, Union

from app.core.trigger_resolver import resolve_effective_trigger
from app.models.agent_config import AgentConfig, AgentType, AgentCategory
from app.models.agent_room_state import AgentRoomState
from app.models.message import Message
from app.models.room import RoomAgentLink


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
        agents: Dict[Union[AgentType, str], Any],
        configs: Dict[Union[AgentType, str], AgentConfig],
        history: List[Message],
        msg_gap: int,
        state_map: Optional[Dict] = None,
        link_map: Optional[Dict] = None,
    ) -> Optional[dict]:
        """
        Decide who speaks next from all available agents.

        Returns:
            dict with 'role', 'action', 'agent', 'config' or None
        """
        state_map = state_map or {}
        link_map = link_map or {}

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
            state = state_map.get(key)
            link = link_map.get(key)
            decision = await AgentOrchestrator._evaluate_agent(
                room, agent, config, history, msg_gap,
                state=state, link=link,
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
        state: Optional[AgentRoomState] = None,
        link: Optional[RoomAgentLink] = None,
    ) -> Optional[dict]:
        """
        Evaluate if a specific agent should act.
        Uses resolved effective trigger config with OR/AND logic.
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

        # Sleep check
        if state and state.is_sleeping:
            return None

        # Resolve effective trigger config
        effective = resolve_effective_trigger(config, link, state)
        trigger = effective.get("trigger", {})
        logic = effective.get("logic", "or")
        enabled = trigger.get("enabled_conditions", [])

        # Check trigger conditions
        should_run = False

        if enabled:
            results = []

            if "message_count" in enabled:
                threshold = trigger.get("message_count")
                if threshold:
                    count = state.message_count_since_last_reply if state else msg_gap
                    results.append(count >= threshold)

            # time_interval_mins and user_silent_mins are handled by time triggers
            # They are checked in check_and_process_time_triggers(), not here

            if results:
                if logic == "and":
                    should_run = all(results)
                else:  # "or"
                    should_run = any(results)
        elif not trigger.get("message_count") and not trigger.get("time_interval_mins") and not trigger.get("user_silent_mins"):
            # No trigger config at all — use agent's internal logic
            if hasattr(agent, "should_reply"):
                should_run = agent.should_reply(history, room.ai_frequency)
            else:
                should_run = config.is_external and len(history) > 0

        if should_run:
            # Determine action based on agent category
            category = config.category or "instructor"

            if category == AgentCategory.PARTICIPANT or category == "participant":
                action = "propose"
            elif config.is_external:
                action = "notify"
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

