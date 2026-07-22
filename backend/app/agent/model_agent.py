"""
模型智能体 — 模型管理、训练任务、场景配置、批次管理

绑定工具：MODEL_TOOLS（模型/场景/批次/训练查询）
集成对话记忆 + SSE 流式 + LLM 降级
"""

import json
from typing import AsyncGenerator

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agent.shared import create_llm
from app.agent.tools import MODEL_TOOLS
from app.agent.memory import conversation_memory
from app.core.logger import get_logger

logger = get_logger(__name__)


class ModelAgent:
    """模型智能体 — 模型/场景/批次/训练查询"""

    def __init__(self):
        self.llm = create_llm()
        self.use_simulated_mode = self.llm is None

        if self.use_simulated_mode:
            logger.info("ModelAgent 初始化完成（模拟模式），绑定 %d 个工具", len(MODEL_TOOLS))
            return

        system_prompt = """你是一个专业的模型管理助手，帮助用户查询模型版本信息、检测场景配置、PCB批次和训练任务。

工具调用规则：
1. 查询模型信息 → 调用 get_model_info
2. 查询检测场景 → 调用 get_scenes
3. 查询PCB批次 → 调用 get_batches
4. 查询训练任务 → 调用 get_training_tasks
5. 无需工具时直接回答

回复要求：模型→版本号+性能指标、场景→名称+状态、训练→状态+进度+参数、简洁专业中文回复"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(llm=self.llm, tools=MODEL_TOOLS, prompt=prompt)
        self.executor = AgentExecutor(
            agent=agent, tools=MODEL_TOOLS, verbose=True,
            max_iterations=3, return_intermediate_steps=True,
        )
        logger.info("ModelAgent 初始化完成，绑定 %d 个工具", len(MODEL_TOOLS))

    async def chat(self, message: str, session_id: str = None, user_id: int = 1) -> dict:
        chat_history = self._load_history(user_id, session_id) if session_id else []

        if self.use_simulated_mode:
            result = _simulate_model_chat(message)
        else:
            try:
                result = await self.executor.ainvoke({
                    "input": message, "chat_history": chat_history,
                })
                result = {"output": result.get("output", ""),
                          "intermediate_steps": result.get("intermediate_steps", [])}
            except Exception as e:
                logger.error("ModelAgent 执行异常: %s", str(e), exc_info=True)
                result = _simulate_model_chat(message)

        if session_id:
            conversation_memory.save_message(user_id, session_id, "user", message)
            conversation_memory.save_message(user_id, session_id, "ai", result["output"])
        return result

    async def chat_stream(self, message: str, image_path: str = None,
                          user_id: int = 1, session_id: str = None) -> AsyncGenerator:
        chat_history = self._load_history(user_id, session_id) if session_id else []

        if self.use_simulated_mode:
            full_output = ""
            async for event in _simulate_model_stream(message):
                if event.get("type") == "text_chunk":
                    full_output += event.get("content", "")
                yield event
            yield {"type": "done", "full_text": full_output}
            if session_id:
                conversation_memory.save_message(user_id, session_id, "user", message)
                if full_output:
                    conversation_memory.save_message(user_id, session_id, "ai", full_output)
            return

        full_output = ""
        try:
            async for event in self.executor.astream_events(
                {"input": message, "chat_history": chat_history}, version="v2",
            ):
                kind = event["event"]
                if kind == "on_chat_model_start":
                    yield {"type": "thinking", "content": "查询模型信息…"}
                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        full_output += chunk.content
                        yield {"type": "text_chunk", "content": chunk.content}
                elif kind == "on_tool_start":
                    yield {"type": "tool_start", "tool": event["name"],
                           "input": event["data"].get("input", {})}
                elif kind == "on_tool_end":
                    output = str(event.get("data", {}).get("output", ""))
                    yield {"type": "tool_end", "tool": event.get("name", ""), "result": output}
        except Exception as e:
            logger.warning("ModelAgent LLM 失败，降级: %s", str(e))
            yield {"type": "thinking", "content": "降级模式处理中…"}
            async for event in _simulate_model_stream(message):
                if event.get("type") == "text_chunk":
                    full_output += event.get("content", "")
                yield event
            yield {"type": "done", "full_text": full_output}
        else:
            yield {"type": "done", "full_text": full_output}
        finally:
            if session_id and full_output:
                conversation_memory.save_message(user_id, session_id, "user", message)
                conversation_memory.save_message(user_id, session_id, "ai", full_output)

    def _load_history(self, user_id: int, session_id: str) -> list:
        try:
            history = conversation_memory.load_history(user_id, session_id)
            chat_history = []
            for msg in history:
                role = "assistant" if msg["role"] == "ai" else msg["role"]
                chat_history.append({"role": role, "content": msg["content"]})
            return chat_history
        except Exception as e:
            logger.warning("加载对话历史失败: %s", str(e))
            return []


def _simulate_model_chat(message: str) -> dict:
    """模拟模式：按关键词直接调用工具"""
    from app.agent.tools.model_tool import (
        get_model_info, get_scenes, get_batches, get_training_tasks,
    )
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in ["模型", "model", "版本"]):
        result = get_model_info.invoke({})
    elif any(kw in msg_lower for kw in ["场景", "scene"]):
        result = get_scenes.invoke({})
    elif any(kw in msg_lower for kw in ["批次", "batch"]):
        result = get_batches.invoke({})
    elif any(kw in msg_lower for kw in ["训练", "training"]):
        result = get_training_tasks.invoke({})
    else:
        return {"output": "模型管理助手已就绪！我可以帮您查询模型版本、检测场景、PCB批次和训练任务。", "intermediate_steps": []}

    try:
        data = json.loads(result)
        if "error" in data:
            output = f"查询失败：{data['error']}"
        else:
            count = data.get("total", data.get("total_models", "N/A"))
            output = f"查询完成，共 {count} 条记录。"
    except Exception:
        output = "查询完成。"
    return {"output": output, "intermediate_steps": []}


async def _simulate_model_stream(message: str):
    """模拟模式流式输出"""
    yield {"type": "thinking", "content": "分析请求，准备查询…"}
    result = _simulate_model_chat(message)
    output = result["output"]
    for i in range(0, len(output), 3):
        yield {"type": "text_chunk", "content": output[i:i + 3]}
        import asyncio
        await asyncio.sleep(0.01)


model_agent = ModelAgent()
