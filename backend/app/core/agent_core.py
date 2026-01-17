from typing import Any, Dict, List, Optional, Union

from app.core.llm_service import LLMFactory, ToolCall


class AgentCore:
    def __init__(
        self, provider: str, api_key: str, system_prompt: str, model: Optional[str] = None
    ):
        self.provider = provider
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.model = model
        self.llm_service = LLMFactory.get_service(provider)

    async def run(
        self, input_text: str, tools: Optional[List[Dict[str, Any]]] = None
    ) -> Union[str, List[ToolCall]]:
        response = await self.llm_service.generate_response(
            prompt=input_text,
            system_prompt=self.system_prompt,
            api_key=self.api_key,
            model=self.model,
            tools=tools,
        )

        # If tools were requested and returned, pass them up
        if tools and response.tool_calls:
            return response.tool_calls

        # Otherwise behave like a standard chat agent
        return response.content or ""
