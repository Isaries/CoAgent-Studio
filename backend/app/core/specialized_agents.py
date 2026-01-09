import random
from typing import Optional
from app.core.agent_core import AgentCore

class TeacherAgent(AgentCore):
    def should_reply(self, message_history: list, ai_frequency: float) -> bool:
        """
        Refined logic to decide if Teacher should reply.
        1. Always reply if specifically mentioned.
        2. Reply based on frequency probability.
        """
        last_msg = message_history[-1] if message_history else None
        
        # 1. Direct mention
        if last_msg and ("@teacher" in last_msg.content.lower() or "老師" in last_msg.content):
             return True
             
        # 2. Probability check
        return random.random() < ai_frequency

    async def generate_reply(self, message_history: list) -> str:
        # Construct context
        context = "\n".join([f"{m.sender_id}: {m.content}" for m in message_history[-10:]])
        prompt = f"""
        Chat History:
        {context}
        
        System Instruction: {self.system_prompt}
        
        Task: You are the teacher. Provide guidance, answer questions, or facilitate discussion.
        Response:
        """
        return await self.run(prompt)

    async def evaluate_student_proposal(self, student_proposal: str, context: str) -> bool:
        """
        Teacher decides if the Student Agent's proposed message is appropriate.
        """
        prompt = f"""
        System Instruction: {self.system_prompt}
        
        Current Context:
        {context}
        
        Student Agent Proposal: "{student_proposal}"
        
        Task: As the teacher, should this student response be allowed? It should be allowed if it helps the discussion and isn't off-topic or harmful.
        Reply with exactly "YES" or "NO".
        """
        response = await self.run(prompt)
        return "YES" in response.upper()

class StudentAgent(AgentCore):
    def should_reply(self, message_history: list, ai_frequency: float) -> bool:
        # Student speaks less frequently than teacher generally, or same config
        # Logic: If last message was from Teacher, Student might answer
        # For now, simple probability
        return random.random() < (ai_frequency * 0.8)

    async def generate_proposal(self, message_history: list) -> str:
        context = "\n".join([f"{m.sender_id}: {m.content}" for m in message_history[-10:]])
        prompt = f"""
        Chat History:
        {context}
        
        System Instruction: {self.system_prompt}
        
        Task: You are a student in this class. You want to contribute to the discussion. 
        Draft a short, helpful message. Do not be too formal.
        """
        return await self.run(prompt)

class DesignAgent(AgentCore):
    DEFAULT_SYSTEM_PROMPT = """You are an expert Prompt Engineer for an educational multi-agent system.
    Your goal is to write a System Prompt for a specific agent (Teacher or Student) based on the user's requirement.
    Refine the user's intent into a robust, instruction-heavy system prompt.
    Only output the generated prompt content. Do not output explanations.
    """

    def __init__(self, provider: str, api_key: str, system_prompt: Optional[str] = None, model: str = None):
        super().__init__(provider, api_key, system_prompt or self.DEFAULT_SYSTEM_PROMPT, model=model)

    async def generate_system_prompt(self, target_agent_type: str, context: str, requirement: str) -> str:
        input_text = f"""
        Target Agent Role: {target_agent_type}
        Course Context: {context}
        User Requirement: {requirement}
        
        Generate a system prompt for this {target_agent_type} agent.
        """
        return await self.run(input_text)

class AnalyticsAgent(AgentCore):
    DEFAULT_SYSTEM_PROMPT = """You are an Educational Data Analyst AI.
    Your goal is to analyze chat logs from student discussions and generate insightful reports for teachers.
    Focus on:
    1. Participation levels (who is active, who is quiet).
    2. Quality of discussion (depth, critical thinking).
    3. Sentiment and collaboration atmosphere.
    """

    def __init__(self, provider: str, api_key: str, system_prompt: Optional[str] = None, model: str = None):
        super().__init__(provider, api_key, system_prompt or self.DEFAULT_SYSTEM_PROMPT, model=model)

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
        return await self.run(prompt)
