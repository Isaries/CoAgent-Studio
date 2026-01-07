from typing import Optional
from app.core.llm_service import LLMFactory

class AgentCore:
    def __init__(self, provider: str, api_key: str, system_prompt: str):
        self.provider = provider
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.llm_service = LLMFactory.get_service(provider)

    async def run(self, input_text: str) -> str:
        return await self.llm_service.generate_response(
            prompt=input_text,
            system_prompt=self.system_prompt,
            api_key=self.api_key
        )
