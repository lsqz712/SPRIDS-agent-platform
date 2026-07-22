"""
知识智能体 — RAG 检索、领域知识问答

绑定工具：KNOWLEDGE_TOOLS（search_knowledge）
集成对话记忆 + SSE 流式 + LLM 降级
"""

import json
from typing import AsyncGenerator

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agent.shared import create_llm
from app.agent.tools import KNOWLEDGE_TOOLS
from app.agent.memory import conversation_memory
from app.core.logger import get_logger

logger = get_logger(__name__)


class KnowledgeAgent:
    """知识智能体 — RAG 检索 + 领域知识问答"""

    def __init__(self):
        self.llm = create_llm()
        self.use_simulated_mode = self.llm is None

        if self.use_simulated_mode:
            logger.info("KnowledgeAgent 初始化完成（模拟模式），绑定 %d 个工具", len(KNOWLEDGE_TOOLS))
            return

        system_prompt = """你是一个专业的PCB检测领域知识助手，帮助用户解答关于目标检测、YOLO算法、PCB检测等专业知识问题。

工具调用规则：
1. 询问专业知识（IoU、YOLO、PCB检测原理、mAP、NMS等）→ 调用 search_knowledge
2. 询问概念定义、算法原理、技术参数 → 调用 search_knowledge
3. 无需工具时直接回答

回复要求：简洁定义+关键细节（≤200字）、基于检索结果回答不编造、知识库无内容时诚实告知、中文回复"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(llm=self.llm, tools=KNOWLEDGE_TOOLS, prompt=prompt)
        self.executor = AgentExecutor(
            agent=agent, tools=KNOWLEDGE_TOOLS, verbose=True,
            max_iterations=3, return_intermediate_steps=True,
        )
        logger.info("KnowledgeAgent 初始化完成，绑定 %d 个工具", len(KNOWLEDGE_TOOLS))

    async def chat(self, message: str, session_id: str = None, user_id: int = 1) -> dict:
        chat_history = self._load_history(user_id, session_id) if session_id else []

        if self.use_simulated_mode:
            result = _simulate_knowledge_chat(message)
        else:
            try:
                result = await self.executor.ainvoke({
                    "input": message, "chat_history": chat_history,
                })
                result = {"output": result.get("output", ""),
                          "intermediate_steps": result.get("intermediate_steps", [])}
            except Exception as e:
                logger.error("KnowledgeAgent 执行异常: %s", str(e), exc_info=True)
                result = _simulate_knowledge_chat(message)

        if session_id:
            conversation_memory.save_message(user_id, session_id, "user", message)
            conversation_memory.save_message(user_id, session_id, "ai", result["output"])
        return result

    async def chat_stream(self, message: str, image_path: str = None,
                          user_id: int = 1, session_id: str = None) -> AsyncGenerator:
        chat_history = self._load_history(user_id, session_id) if session_id else []

        if self.use_simulated_mode:
            full_output = ""
            async for event in _simulate_knowledge_stream(message):
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
                    yield {"type": "thinking", "content": "检索知识库…"}
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
            logger.warning("KnowledgeAgent LLM 失败，降级: %s", str(e))
            yield {"type": "thinking", "content": "降级模式处理中…"}
            async for event in _simulate_knowledge_stream(message):
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


def _simulate_knowledge_chat(message: str) -> dict:
    """模拟模式：直接调用 RAG 检索"""
    from app.agent.tools.knowledge_tool import search_knowledge
    try:
        result = search_knowledge.invoke({"query": message, "top_k": 3})
        result_data = json.loads(result)
        if "error" in result_data:
            output = f"知识库检索失败：{result_data['error']}"
        elif result_data.get("sources"):
            parts = [f"根据知识库检索，找到 {len(result_data['sources'])} 条相关内容："]
            for i, src in enumerate(result_data["sources"][:3], 1):
                parts.append(f"\n{i}. {src.get('filename', '未知来源')}")
            output = "\n".join(parts)
        else:
            output = result_data.get("answer", "知识库中暂无相关内容，请尝试换个问法。")
        return {"output": output, "intermediate_steps": []}
    except Exception as e:
        return {"output": f"知识助手已就绪！\n（检索出错：{str(e)}）", "intermediate_steps": []}


async def _simulate_knowledge_stream(message: str):
    """模拟模式流式输出"""
    yield {"type": "thinking", "content": "检索知识库…"}
    yield {"type": "tool_start", "tool": "search_knowledge", "input": {"query": message}}
    result = _simulate_knowledge_chat(message)
    output = result["output"]
    for i in range(0, len(output), 3):
        yield {"type": "text_chunk", "content": output[i:i + 3]}
        import asyncio
        await asyncio.sleep(0.01)


knowledge_agent = KnowledgeAgent()
