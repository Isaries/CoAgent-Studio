import pytest

from app.core.agent_core import AgentCore
from app.core.llm_service import LLMResponse, ToolCall


@pytest.mark.asyncio()
async def test_agent_single_turn(mock_llm):
    """
    Test a simple chat where LLM replies directly without tools.
    """
    # 1. Setup Expectation
    mock_llm.add_response(LLMResponse(content="Hello! How can I help you?"))

    # 2. Run Agent
    agent = AgentCore(
        provider="openai", api_key="mock_key", system_prompt="You are a helpful assistant"
    )

    response = await agent.run(input_text="Hi there")

    # 3. Verify
    assert response == "Hello! How can I help you?"


@pytest.mark.asyncio()
async def test_agent_tool_use(mock_llm):
    """
    Test that the Agent correctly returns ToolCalls when the LLM requests them.
    """
    # 1. Setup Tool Definition
    search_tool_def = {
        "type": "function",
        "function": {
            "name": "search_course",
            "description": "Search for courses",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
        },
    }

    # 2. Setup Expectation: LLM returns a Tool Call
    expected_tool_call = ToolCall(
        id="call_123", name="search_course", arguments={"query": "python"}
    )
    mock_llm.add_response(LLMResponse(content=None, tool_calls=[expected_tool_call]))

    # 3. Run Agent
    agent = AgentCore(
        provider="openai", api_key="mock_key", system_prompt="You are a helpful assistant"
    )

    response = await agent.run(input_text="Find python courses", tools=[search_tool_def])

    # 4. Verify
    assert isinstance(response, list)
    assert len(response) == 1
    assert response[0].name == "search_course"
    assert response[0].arguments["query"] == "python"
