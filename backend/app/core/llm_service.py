import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, cast

from google import genai
from google.genai import types
from openai import NOT_GIVEN, AsyncOpenAI, RateLimitError, AuthenticationError
from openai.types.chat import ChatCompletionToolParam

from app.core.a2a.resilience import with_resilience

logger = logging.getLogger(__name__)

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
        api_keys: Optional[List[str]] = None,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        pass


class BaseLLMService(LLMService):
    """Base implementation handling fallback logic."""
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
        api_keys: Optional[List[str]] = None,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        # Build key chain
        keys = []
        if api_key:
            keys.append(api_key)
        if api_keys:
            keys.extend(api_keys)
        
        # Deduplicate while preserving order
        keys = list(dict.fromkeys(keys))
        
        if not keys:
            return LLMResponse(content=f"Error: No API Key provided")

        last_error = None
        for i, key in enumerate(keys):
            try:
                return await self._generate_with_single_key(
                    prompt, system_prompt, key, model, tools
                )
            except (RateLimitError, AuthenticationError) as e:
                # Catch strictly 429/401 related errors for fallback
                logger.warning(f"Connection failed with key {i+1}/{len(keys)}: {str(e)}")
                last_error = e
                continue
            except Exception as e:
                # For non-fallback errors (like bad request), fail immediately?
                # Actually, Gemini might throw different errors.
                # Let's catch generic for now but log warning.
                # If we want to be robust, we treat almost any "call failed" as a reason to try next key?
                # But if prompt is invalid, next key won't help.
                # For safety, let's catch robustly.
                logger.warning(f"Error with key {i+1}: {str(e)}")
                last_error = e
                continue
        
        return LLMResponse(content=f"All API keys failed. Last error: {str(last_error)}")

    @abstractmethod
    async def _generate_with_single_key(
        self,
        prompt: str,
        system_prompt: Optional[str],
        api_key: str,
        model: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
    ) -> LLMResponse:
        pass


class GeminiService(BaseLLMService):
    def __init__(self):
        pass

    @with_resilience(breaker_name="gemini_api")
    async def _generate_with_single_key(
        self,
        prompt: str,
        system_prompt: Optional[str],
        api_key: str,
        model: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
    ) -> LLMResponse:
        model_name = model or "gemini-1.5-pro"

        gemini_tools = None
        if tools:
            gemini_tools = []
            for t in tools:
                converted = self._convert_to_gemini_tool(t)
                if converted:
                    gemini_tools.append(converted)

        config = types.GenerateContentConfig(tools=gemini_tools, system_instruction=system_prompt)

        # Gemini SDK doesn't use the standard OpenAI exceptions naturally, 
        # but resilient wrapper might normalize or we catch raw exceptions.
        # We allow exceptions to propagate to BaseLLMService loop.
        
        async with genai.Client(api_key=api_key) as client:
            response = await client.aio.models.generate_content(
                model=model_name, contents=prompt, config=config
            )

        tool_calls = []
        content = ""

        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.function_call:
                            args = part.function_call.args
                            tool_calls.append(
                                ToolCall(
                                    id="call_" + (part.function_call.name or "unknown"),
                                    name=part.function_call.name or "unknown",
                                    arguments=args if args else {},
                                )
                            )
                        if part.text:
                            content += part.text

        return LLMResponse(content=content if content else None, tool_calls=tool_calls)

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


class OpenAIService(BaseLLMService):
    @with_resilience(breaker_name="openai_api")
    async def _generate_with_single_key(
        self,
        prompt: str,
        system_prompt: Optional[str],
        api_key: str,
        model: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model_name = model or "gpt-4o"

        openai_tools = None
        if tools:
            openai_tools = [cast(ChatCompletionToolParam, t) for t in tools]

        async with AsyncOpenAI(api_key=api_key) as client:
            response = await client.chat.completions.create(
                model=model_name,
                messages=cast(Any, messages),
                tools=openai_tools or NOT_GIVEN,
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


class LLMFactory:
    @staticmethod
    def get_service(provider: str) -> LLMService:
        if provider == "gemini":
            return GeminiService()
        elif provider == "openai":
            return OpenAIService()
        else:
            raise ValueError(f"Unknown provider: {provider}")
