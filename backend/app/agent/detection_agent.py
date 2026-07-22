"""
检测智能体 — ReAct Agent + 全工具绑定 + RAG + 对话记忆

职责：
  - 创建 LangChain ReAct Agent，绑定全部工具（检测/分析/知识/模型）
  - 集成对话记忆（Redis），支持跨轮次上下文理解
  - SSE 流式输出（tool_start/tool_end/text_chunk/done/error）

架构：
  用户消息 → 对话记忆加载 → Agent（LLM 决策）→ 调用工具 → 返回结果 → 对话记忆保存
"""

import json
from typing import AsyncGenerator

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agent.shared import create_llm
from app.agent.tools import ALL_TOOLS
from app.agent.memory import conversation_memory
from app.core.logger import get_logger

logger = get_logger(__name__)

MAX_CONTEXT_TOKENS = 8000


class DetectionAgent:
    """检测智能体 — 封装 ReAct Agent 和对话逻辑，绑定全部工具"""

    def __init__(self):
        self.llm = create_llm()
        self.use_simulated_mode = self.llm is None

        if self.use_simulated_mode:
            logger.info("DetectionAgent 初始化完成（模拟模式），绑定 %d 个工具", len(ALL_TOOLS))
            return

        system_prompt = """你是一个专业的PCB检测智能助手，帮助用户检测PCB缺陷、查询检测数据和回答领域知识问题。

工具调用规则：
1. 消息含 [附件图片路径: xxx] → 调用检测工具（detect_single_image / detect_batch_images / detect_zip_images_file / detect_video_file）
2. 询问专业知识（IoU、YOLO等）→ 调用 search_knowledge
3. 询问统计信息、任务记录、缺陷类型等 → 调用对应数据查询工具
4. 询问模型、训练、场景、批次 → 调用模型管理工具
5. 无需工具时直接回答

回复要求：
- 检测结果：总数→类别数量→推理耗时
- 知识问答：简洁定义+关键细节（≤200字）
- 统计数据：数字+趋势判断
- 风格：简洁专业，中文回复"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(llm=self.llm, tools=ALL_TOOLS, prompt=prompt)

        self.executor = AgentExecutor(
            agent=agent, tools=ALL_TOOLS, verbose=True,
            max_iterations=8, return_intermediate_steps=True,
        )

        logger.info("DetectionAgent 初始化完成，绑定 %d 个工具", len(ALL_TOOLS))

    # ── 对话接口 ──────────────────────────────────────

    async def chat(self, message: str, image_path: str = None,
                   user_id: int = 1, session_id: str = None) -> dict:
        if image_path:
            message = f"{message}\n[附件图片路径: {image_path}]"

        chat_history = []
        if session_id:
            chat_history = self._load_history(user_id, session_id)

        if self.use_simulated_mode:
            result = _simulate_chat(message, image_path)
        else:
            try:
                result = await self.executor.ainvoke({
                    "input": message, "chat_history": chat_history,
                })
                result = {"output": result.get("output", ""),
                          "intermediate_steps": result.get("intermediate_steps", [])}
            except Exception as e:
                logger.error("Agent 执行异常: %s", str(e), exc_info=True)
                result = _simulate_chat(message, image_path)

        if session_id:
            conversation_memory.save_message(user_id, session_id, "user", message)
            conversation_memory.save_message(user_id, session_id, "ai", result["output"])
        return result

    async def chat_stream(self, message: str, image_path: str = None,
                          user_id: int = 1, session_id: str = None) -> AsyncGenerator:
        if image_path:
            message = f"{message}\n[附件图片路径: {image_path}]"

        chat_history = []
        if session_id:
            chat_history = self._load_history(user_id, session_id)

        if self.use_simulated_mode:
            full_output = ""
            async for event in _simulate_chat_stream(message, image_path):
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
                event_kind = event["event"]

                if event_kind == "on_chat_model_start":
                    yield {"type": "thinking", "content": "思考中…"}

                elif event_kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        full_output += chunk.content
                        yield {"type": "text_chunk", "content": chunk.content}

                elif event_kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    logger.info("工具调用: %s, 输入: %s", tool_name,
                                str(tool_input)[:200])
                    yield {"type": "tool_start", "tool": tool_name, "input": tool_input}

                elif event_kind == "on_tool_end":
                    tool_data = event.get("data", {})
                    tool_output = tool_data.get("output", "")
                    tool_name = event.get("name", "")
                    logger.info("工具完成: %s", tool_name)
                    yield {"type": "tool_end", "tool": tool_name,
                           "result": str(tool_output) if tool_output else ""}

        except Exception as e:
            logger.warning("LLM 调用失败，降级到模拟模式: %s", str(e))
            yield {"type": "thinking", "content": "降级模式处理中…"}
            async for event in _simulate_chat_stream(message, image_path):
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
                if msg["role"] == "user":
                    chat_history.append({"role": "user", "content": msg["content"]})
                elif msg["role"] == "ai":
                    chat_history.append({"role": "assistant", "content": msg["content"]})
            return chat_history
        except Exception as e:
            logger.warning("加载对话历史失败: %s", str(e))
            return []


# ── 全局辅助函数 ──────────────────────────────────────

def _simulate_chat(message: str, image_path: str = None) -> dict:
    """模拟模式：直接调用工具"""
    import re
    from app.agent.tools.detection_tool import detect_single_image, detect_zip_images_file

    zip_pattern = r'\.(zip|rar|7z)$'
    if image_path:
        if re.search(zip_pattern, image_path, re.IGNORECASE):
            result = detect_zip_images_file.invoke({"zip_path": image_path})
            tool_name = "detect_zip_images_file"
        else:
            result = detect_single_image.invoke({"image_path": image_path})
            tool_name = "detect_single_image"

        result_data = json.loads(result)
        if "error" in result_data:
            output = f"检测失败：{result_data['error']}"
        else:
            total = result_data.get("total_objects", 0)
            counts = result_data.get("class_counts", {})
            count_str = ", ".join([f"{k}: {v}" for k, v in counts.items()]) if counts else "无"
            output = f"检测完成！共检测到 {total} 个目标。类别统计：{count_str}。"
        return {"output": output, "intermediate_steps": [{"tool": tool_name, "result": result}]}

    return {"output": "请提供图片路径进行检测。支持单图检测、批量检测和 ZIP 文件检测。",
            "intermediate_steps": []}


async def _simulate_chat_stream(message: str, image_path: str = None):
    """模拟模式流式输出"""
    import re
    import asyncio
    from app.agent.tools.detection_tool import detect_single_image, detect_zip_images_file

    yield {"type": "thinking", "content": "分析请求，准备调用检测工具…"}
    zip_pattern = r'\.(zip|rar|7z)$'
    if image_path:
        if re.search(zip_pattern, image_path, re.IGNORECASE):
            tool_name = "detect_zip_images_file"
            yield {"type": "tool_start", "tool": tool_name, "input": {"zip_path": image_path}}
            result = detect_zip_images_file.invoke({"zip_path": image_path})
        else:
            tool_name = "detect_single_image"
            yield {"type": "tool_start", "tool": tool_name, "input": {"image_path": image_path}}
            result = detect_single_image.invoke({"image_path": image_path})

        yield {"type": "tool_end", "tool": tool_name, "result": result}
        result_data = json.loads(result)
        if "error" in result_data:
            yield {"type": "text_chunk", "content": f"检测失败：{result_data['error']}"}
        else:
            total = result_data.get("total_objects", 0)
            counts = result_data.get("class_counts", {})
            yield {"type": "text_chunk", "content": f"检测完成！共检测到 {total} 个目标。"}
            if counts:
                count_str = ", ".join([f"{k}: {v}" for k, v in counts.items()])
                yield {"type": "text_chunk", "content": f"类别统计：{count_str}。"}
    else:
        yield {"type": "text_chunk", "content": "请提供图片路径进行检测。"}
        yield {"type": "text_chunk", "content": "支持单图检测、批量检测和 ZIP 文件检测。"}


detection_agent = DetectionAgent()
