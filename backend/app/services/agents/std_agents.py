import random
from typing import Optional, Union

from app.core.agent_core import AgentCore
from app.core.a2a.models import A2AMessage, MessageType
from app.core.a2a.base import A2AAgentMixin, AgentId

if False: # TYPE_CHECKING
    from app.core.a2a.workflow import WorkflowContext


class TeacherAgent(AgentCore, A2AAgentMixin):
    """
    Teacher Agent with A2A protocol support.
    
    Handles:
    - Direct replies to chat
    - Evaluation of student proposals via A2A messages
    """

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

    async def generate_reply(
        self, message_history: list, tools: Optional[list] = None
    ) -> Union[str, list]:
        # Construct context
        context = "\n".join([f"{m.sender_id}: {m.content}" for m in message_history[-10:]])
        prompt = f"""
        Chat History:
        {context}

        System Instruction: {self.system_prompt}

        Task: You are the teacher. Provide guidance, answer questions, or facilitate discussion.
        Response:
        """
        return await self.run(prompt, tools=tools)

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
        return "YES" in str(response).upper()

    async def receive_message(self, msg: A2AMessage) -> Optional[A2AMessage]:
        """
        A2A Protocol: Handle incoming messages from other agents.
        
        Supported message types:
        - EVALUATION_REQUEST: Evaluate a student's proposal
        """
        if msg.type == MessageType.EVALUATION_REQUEST:
            proposal = msg.content
            context = msg.metadata.get("context", "")
            approved = await self.evaluate_student_proposal(proposal, context)
            
            return msg.reply(
                type=MessageType.EVALUATION_RESULT,
                content={"approved": approved, "proposal": proposal},
                sender_id=AgentId.TEACHER,
            )
        
        return None
    
    async def handle_workflow_step(self, context: "WorkflowContext") -> Optional[A2AMessage]:
        """
        Adapter method for GraphExecutor.
        Takes full WorkflowContext, returns A2AMessage.
        """
        from app.core.a2a.models import MessageType
        
        # Check previous message in context history effectively?
        # GraphExecutor passes context.last_result usually.
        # But for Teacher, we expect an EVALUATION_REQUEST.
        
        last_msg = context.last_result
        if not last_msg or last_msg.type != MessageType.EVALUATION_REQUEST:
            # Teacher might be the start? No, usually after Student.
            # If start, last_msg is None.
            return None
            
        return await self.receive_message(last_msg)


class StudentAgent(AgentCore, A2AAgentMixin):
    """
    Student Agent with A2A protocol support.
    
    Handles:
    - Generating proposals for the chat
    - Processing evaluation results via A2A messages
    """

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
        return str(await self.run(prompt))

    async def receive_message(self, msg: A2AMessage) -> Optional[A2AMessage]:
        """
        A2A Protocol: Handle incoming messages from other agents.
        
        Supported message types:
        - EVALUATION_RESULT: Process teacher's approval/rejection
        """
        if msg.type == MessageType.EVALUATION_RESULT:
            content = msg.content
            if isinstance(content, dict) and content.get("approved"):
                # Approved: broadcast the proposal
                return msg.reply(
                    type=MessageType.BROADCAST,
                    content=content.get("proposal", ""),
                    sender_id=AgentId.STUDENT,
                    recipient_id=AgentId.BROADCAST,
                )
            # Rejected: return None (no broadcast)
        
        return None

    async def handle_workflow_step(self, context: "WorkflowContext") -> Optional[A2AMessage]:
        """
        Adapter method for GraphExecutor.
        """
        from app.core.a2a.models import MessageType, A2AMessage
        from app.core.a2a.base import AgentId
        
        last_msg = context.last_result
        
        # CASE 1: Student is generating proposal (Start of flow)
        if not last_msg:
            # We need to construct a message
            # Context data might have 'proposal_prompt' or similar
            # Or we look at chat history if passed in context.data
            
            # Use 'message_history' from context.data if available, else empty
            history = context.data.get("message_history", [])
            
            # Check for override (e.g. from user retry or direct input)
            if context.data.get("proposal_override"):
                proposal_text = context.data.get("proposal_override")
            else:
                proposal_text = await self.generate_proposal(history)
            
            return A2AMessage(
                type=MessageType.EVALUATION_REQUEST,
                sender_id=AgentId.STUDENT,
                recipient_id=AgentId.TEACHER,
                content=proposal_text, 
                metadata=context.data
            )
            
        # CASE 2: Student receiving evaluation result
        if last_msg.type == MessageType.EVALUATION_RESULT:
            return await self.receive_message(last_msg)
            
        return None
