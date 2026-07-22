"""
LLM 客户端封装层
支持 OpenAI API 和 Ollama 本地模型
提供统一的流式和非流式接口
"""
from typing import List, Dict, Any, Optional, Iterator
from fastapi import HTTPException
from app.config.settings import settings

class LLMClient:
    def __init__(self):
        self.use_ollama = bool(settings.OLLAMA_BASE_URL) and not bool(settings.effective_llm_api_key)
        self._client = None
        self._init_client()

    def _init_client(self):
        if self.use_ollama:
            try:
                from ollama import Client
                self._client = Client(host=settings.OLLAMA_BASE_URL)
            except ImportError:
                raise HTTPException(status_code=500, detail="ollama 库未安装")
        else:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=settings.effective_llm_api_key,
                    base_url=settings.effective_llm_base_url,
                    timeout=settings.LLM_TIMEOUT,
                )
            except ImportError:
                raise HTTPException(status_code=500, detail="openai 库未安装")

    def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        if self.use_ollama:
            model = kwargs.get("model", settings.OLLAMA_MODEL_NAME)
        else:
            model = kwargs.get("model", settings.effective_llm_model)
        temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", settings.LLM_MAX_TOKENS)

        try:
            if self.use_ollama:
                response = self._client.chat(
                    model=model,
                    messages=messages,
                    options={
                        "temperature": temperature,
                        "num_ctx": max_tokens,
                    },
                )
                return response["message"]["content"]
            else:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content or ""
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM 调用失败: {str(e)}")

    def generate_stream(self, messages: List[Dict[str, str]], **kwargs) -> Iterator[str]:
        if self.use_ollama:
            model = kwargs.get("model", settings.OLLAMA_MODEL_NAME)
        else:
            model = kwargs.get("model", settings.effective_llm_model)
        temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", settings.LLM_MAX_TOKENS)

        try:
            if self.use_ollama:
                stream = self._client.chat(
                    model=model,
                    messages=messages,
                    options={
                        "temperature": temperature,
                        "num_ctx": max_tokens,
                    },
                    stream=True,
                )
                for chunk in stream:
                    if chunk.get("message", {}).get("content"):
                        yield chunk["message"]["content"]
            else:
                stream = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )
                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM 流式调用失败: {str(e)}")

    def generate_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        if self.use_ollama:
            model = kwargs.get("model", settings.OLLAMA_MODEL_NAME)
        else:
            model = kwargs.get("model", settings.effective_llm_model)
        temperature = kwargs.get("temperature", settings.LLM_TEMPERATURE)

        try:
            if self.use_ollama:
                response = self._client.chat(
                    model=model,
                    messages=messages,
                    tools=tools,
                    options={"temperature": temperature},
                )
                return response
            else:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=temperature,
                )
                return response.choices[0].message
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM 工具调用失败: {str(e)}")

llm_client = LLMClient()