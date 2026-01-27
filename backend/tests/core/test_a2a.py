"""
Unit tests for A2A Protocol module.
"""

import pytest
from uuid import uuid4

from app.core.a2a import A2AMessage, MessageType, A2ADispatcher


class TestA2AMessage:
    """Tests for A2AMessage dataclass."""

    def test_create_message_with_defaults(self):
        msg = A2AMessage()
        assert msg.type == MessageType.USER_MESSAGE
        assert msg.sender_id == ""
        assert msg.recipient_id == "broadcast"
        assert msg.id is not None

    def test_create_message_with_values(self):
        msg = A2AMessage(
            type=MessageType.PROPOSAL,
            sender_id="student",
            recipient_id="teacher",
            content="Hello, Teacher!",
            metadata={"room_id": "123"},
        )
        assert msg.type == MessageType.PROPOSAL
        assert msg.sender_id == "student"
        assert msg.recipient_id == "teacher"
        assert msg.content == "Hello, Teacher!"
        assert msg.metadata["room_id"] == "123"

    def test_reply_creates_linked_message(self):
        original = A2AMessage(
            type=MessageType.EVALUATION_REQUEST,
            sender_id="student",
            recipient_id="teacher",
            content="Please evaluate this.",
        )
        
        reply = original.reply(
            type=MessageType.EVALUATION_RESULT,
            content={"approved": True},
            sender_id="teacher",
        )
        
        assert reply.correlation_id == original.id
        assert reply.sender_id == "teacher"
        assert reply.recipient_id == "student"  # Auto-set to original sender
        assert reply.content["approved"] is True


class TestA2ADispatcher:
    """Tests for A2ADispatcher."""

    @pytest.fixture
    def dispatcher(self):
        return A2ADispatcher()

    @pytest.mark.asyncio
    async def test_register_and_dispatch(self, dispatcher):
        received_messages = []

        async def mock_handler(msg: A2AMessage):
            received_messages.append(msg)
            return msg.reply(
                type=MessageType.EVALUATION_RESULT,
                content="OK",
                sender_id="teacher",
            )

        dispatcher.register("teacher", mock_handler)
        
        msg = A2AMessage(
            type=MessageType.EVALUATION_REQUEST,
            sender_id="student",
            recipient_id="teacher",
            content="Test",
        )
        
        response = await dispatcher.dispatch(msg)
        
        assert len(received_messages) == 1
        assert received_messages[0].content == "Test"
        assert response is not None
        assert response.content == "OK"

    @pytest.mark.asyncio
    async def test_dispatch_to_unknown_recipient(self, dispatcher):
        msg = A2AMessage(
            type=MessageType.PROPOSAL,
            sender_id="student",
            recipient_id="unknown_agent",
            content="Hello?",
        )
        
        response = await dispatcher.dispatch(msg)
        assert response is None

    @pytest.mark.asyncio
    async def test_broadcast_calls_broadcast_handler(self, dispatcher):
        broadcast_messages = []

        async def broadcast_handler(msg: A2AMessage):
            broadcast_messages.append(msg)

        dispatcher.set_broadcast_handler(broadcast_handler)
        
        msg = A2AMessage(
            type=MessageType.BROADCAST,
            sender_id="student",
            recipient_id="broadcast",
            content="Hello everyone!",
        )
        
        response = await dispatcher.dispatch(msg)
        
        assert response is None  # Broadcast returns None
        assert len(broadcast_messages) == 1
        assert broadcast_messages[0].content == "Hello everyone!"

    @pytest.mark.asyncio
    async def test_middleware_runs_for_every_message(self, dispatcher):
        logged_messages = []

        async def logging_middleware(msg: A2AMessage):
            logged_messages.append(msg.id)

        dispatcher.add_middleware(logging_middleware)
        
        msg1 = A2AMessage(sender_id="a", recipient_id="broadcast", content="1")
        msg2 = A2AMessage(sender_id="b", recipient_id="broadcast", content="2")
        
        await dispatcher.dispatch(msg1)
        await dispatcher.dispatch(msg2)
        
        assert len(logged_messages) == 2
        assert msg1.id in logged_messages
        assert msg2.id in logged_messages

    def test_registered_agents_property(self, dispatcher):
        async def handler(msg):
            return None

        dispatcher.register("teacher", handler)
        dispatcher.register("student", handler)
        
        agents = dispatcher.registered_agents
        assert "teacher" in agents
        assert "student" in agents

    def test_unregister_agent(self, dispatcher):
        async def handler(msg):
            return None

        dispatcher.register("teacher", handler)
        assert "teacher" in dispatcher.registered_agents
        
        dispatcher.unregister("teacher")
        assert "teacher" not in dispatcher.registered_agents
