from typing import List, Optional

from app.models.agent_config import AgentType
from app.models.message import Message


class AgentOrchestrator:
    """
    Pure logic component to decide the next action based on state.
    """

    @staticmethod
    async def decide_turn(
        room,
        agents: dict,  # Map[AgentType, AgentCore]
        configs: dict,  # Map[AgentType, AgentConfig]
        history: List[Message],
        msg_gap: int,
    ) -> Optional[dict]:
        """
        Decide who speaks next.
        """

        # 1. Teacher Turn
        teacher_agent = agents.get(AgentType.TEACHER)
        teacher_config = configs.get(AgentType.TEACHER)

        can_teacher = room.ai_mode in ["teacher_only", "both"]

        if can_teacher and teacher_agent and teacher_config:
            # Logic: Check Trigger Config OR Agent Internal Logic
            should_run = False
            trigger = teacher_config.trigger_config or {}

            if trigger.get("type") == "message_count":
                should_run = msg_gap >= trigger.get("value", 10)
            elif not trigger:
                # Default probability check
                should_run = teacher_agent.should_reply(history, room.ai_frequency)

            if should_run:
                return {"role": AgentType.TEACHER, "action": "reply", "agent": teacher_agent}

        # 2. Student Turn
        student_agent = agents.get(AgentType.STUDENT)
        student_config = configs.get(AgentType.STUDENT)
        can_student = room.ai_mode == "both"

        if can_student and student_agent and student_config and teacher_agent:
            # Student needs teacher to exist
            should_run = False
            trigger = student_config.trigger_config or {}

            if trigger.get("type") == "message_count":
                should_run = msg_gap >= trigger.get("value", 10)
            elif not trigger:
                should_run = student_agent.should_reply(history, room.ai_frequency)

            if should_run:
                return {"role": AgentType.STUDENT, "action": "propose", "agent": student_agent}

        return None
