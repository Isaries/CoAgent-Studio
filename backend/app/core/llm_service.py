import google.generativeai as genai
from openai import AsyncOpenAI
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
import os
import asyncio

class LLMService(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None, api_key: str = None) -> str:
        pass

class GeminiService(LLMService):
    def __init__(self):
        self._lock = asyncio.Lock()

    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None, api_key: str = None) -> str:
        if not api_key:
             return "Error: API Key missing for Gemini"
        
        # Use lock to prevent race condition on global configuration
        async with self._lock:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            # Combine system prompt if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
                
            response = await model.generate_content_async(full_prompt)
        return response.text

class OpenAIService(LLMService):
    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None, api_key: str = None) -> str:
        if not api_key:
            return "Error: API Key missing for OpenAI"
            
        client = AsyncOpenAI(api_key=api_key)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        return response.choices[0].message.content

class LLMFactory:
    @staticmethod
    def get_service(provider: str) -> LLMService:
        if provider == "gemini":
            return GeminiService()
        elif provider == "openai":
            return OpenAIService()
        else:
            raise ValueError(f"Unknown provider: {provider}")
