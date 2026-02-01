from typing import Optional

from app.core.agent_core import AgentCore


class DesignAgent(AgentCore):
    DEFAULT_SYSTEM_PROMPT = """You are an expert Prompt Engineer for an educational multi-agent system.
    Your goal is to write a System Prompt for a specific agent (Teacher or Student) based on the user's requirement.
    Refine the user's intent into a robust, instruction-heavy system prompt.
    Only output the generated prompt content. Do not output explanations.
    """

    def __init__(
        self,
        provider: str,
        api_key: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ):
        super().__init__(
            provider, api_key, system_prompt or self.DEFAULT_SYSTEM_PROMPT, model=model
        )

    async def generate_system_prompt(
        self, target_agent_type: str, context: str, requirement: str
    ) -> str:
        input_text = f"""
        Target Agent Role: {target_agent_type}
        Course Context: {context}
        User Requirement: {requirement}

        Generate a system prompt for this {target_agent_type} agent.
        """
        return str(await self.run(input_text))


class AnalyticsAgent(AgentCore):
    DEFAULT_SYSTEM_PROMPT = """You are an Educational Data Analyst AI.
    Your goal is to analyze chat logs from student discussions and generate insightful reports for teachers.
    Focus on:
    1. Participation levels (who is active, who is quiet).
    2. Quality of discussion (depth, critical thinking).
    3. Sentiment and collaboration atmosphere.
    """

    def __init__(
        self,
        provider: str,
        api_key: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ):
        super().__init__(
            provider, api_key, system_prompt or self.DEFAULT_SYSTEM_PROMPT, model=model
        )

    async def analyze_room(self, message_history: list) -> str:
        if not message_history:
            return "No messages to analyze."

        context = "\n".join([f"{m.sender_id}: {m.content}" for m in message_history])

        prompt = f"""
        Chat Log:
        {context}

        Task: Generate a concise markdown report summarizing the discussion in this room.
        Highlight key contributors, topics discussed, and any interventions needed.
        """
        return str(await self.run(prompt))
