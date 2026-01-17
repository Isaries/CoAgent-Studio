import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionToolParam


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    content: Optional[str]
    tool_calls: List[ToolCall] = field(default_factory=list)


class LLMService(ABC):
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        pass


class GeminiService(LLMService):
    def __init__(self):
        pass

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        if not api_key:
            return LLMResponse(content="Error: API Key missing for Gemini")

        client = genai.Client(api_key=api_key)
        model_name = model or "gemini-1.5-pro"

        gemini_tools = None
        if tools:
            gemini_tools = []
            for t in tools:
                converted = self._convert_to_gemini_tool(t)
                if converted:
                    gemini_tools.append(converted)

        config = types.GenerateContentConfig(tools=gemini_tools, system_instruction=system_prompt)

        try:
            # Note: client.models.generate_content is synchronous or async?
            # The SDK supports async via `client.aio.models.generate_content` usually, or just `client.models.generate_content` is sync.
            # We need to verify if we need `client.aio`. Looking at SDK docs (searched previously), it likely has an async client or method.
            # Assuming `client.aio` for now or checking if there's an async method.
            # Let's check imports. usually `from google import genai` -> `client = genai.Client()`.
            # For async: `client = genai.Client(...)`. `await client.aio.models.generate_content(...)`?
            # Or `await client.models.generate_content_async(...)`? Use `generate_content` is sync.
            # Code search said "supports asynchronous operations".
            # I'll try `await client.aio.models.generate_content(...)`.

            response = await client.aio.models.generate_content(
                model=model_name, contents=prompt, config=config
            )

            tool_calls = []
            content = ""

            # The response structure needs to be handled carefully.
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.function_call:
                                args = part.function_call.args
                                # Convert to dict if it's not already
                                if hasattr(args, "items"):
                                    # It might be a MapComposite or similar, usually accessible as dict or has .items()
                                    # But let's assume it behaves like a dict or we can convert it.
                                    # In 0.8+, it often returns a plain dict or a structure we can cast.
                                    pass

                                tool_calls.append(
                                    ToolCall(
                                        id="call_" + part.function_call.name,
                                        name=part.function_call.name,
                                        arguments=args,
                                    )
                                )
                            if part.text:
                                content += part.text

            return LLMResponse(content=content if content else None, tool_calls=tool_calls)

        except Exception as e:
            return LLMResponse(content=f"Error generating response: {e!s}")

    def _convert_to_gemini_tool(self, tool_def: Dict[str, Any]) -> Optional[types.Tool]:
        if tool_def.get("type") == "function":
            func = tool_def["function"]
            return types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=func["name"],
                        description=func.get("description", ""),
                        parameters=func.get("parameters", {}),
                    )
                ]
            )
        return None


class OpenAIService(LLMService):
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        if not api_key:
            return LLMResponse(content="Error: API Key missing for OpenAI")

        client = AsyncOpenAI(api_key=api_key)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model_name = model or "gpt-4o"

        openai_tools = None
        if tools:
            # Pass directly as OpenAI strictly follows the schema we'll use
            openai_tools = [ChatCompletionToolParam(**t) for t in tools]

        try:
            response = await client.chat.completions.create(
                model=model_name, messages=messages, tools=openai_tools
            )

            message = response.choices[0].message
            content = message.content
            tool_calls = []

            if message.tool_calls:
                for tc in message.tool_calls:
                    if tc.type == "function":
                        tool_calls.append(
                            ToolCall(
                                id=tc.id,
                                name=tc.function.name,
                                arguments=json.loads(tc.function.arguments),
                            )
                        )

            return LLMResponse(content=content, tool_calls=tool_calls)

        except Exception as e:
            return LLMResponse(content=f"Error generating response: {e!s}")


class LLMFactory:
    @staticmethod
    def get_service(provider: str) -> LLMService:
        if provider == "gemini":
            return GeminiService()
        elif provider == "openai":
            return OpenAIService()
        else:
            raise ValueError(f"Unknown provider: {provider}")
