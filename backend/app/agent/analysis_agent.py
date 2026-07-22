"""
分析智能体 — 统计分析、缺陷分析、任务查询

绑定工具：ANALYSIS_TOOLS（统计/缺陷/任务/良品率/用户查询）
集成对话记忆 + SSE 流式 + LLM 降级
"""

import json
from typing import AsyncGenerator

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agent.shared import create_llm
from app.agent.tools import ANALYSIS_TOOLS
from app.agent.memory import conversation_memory
from app.core.logger import get_logger

logger = get_logger(__name__)


class AnalysisAgent:
    """分析智能体 — 数据查询 + 缺陷分析 + 良品率"""

    def __init__(self):
        self.llm = create_llm()
        self.use_simulated_mode = self.llm is None

        if self.use_simulated_mode:
            logger.info("AnalysisAgent 初始化完成（模拟模式），绑定 %d 个工具", len(ANALYSIS_TOOLS))
            return

        system_prompt = """你是一个专业的数据分析助手，帮助用户分析PCB检测数据、查询统计信息和生成分析报告。

工具调用规则：
1. 查询数据概览 → 调用 get_statistics_overview
2. 查询统计（"今天检测了多少"）→ 调用 query_detection_stats
3. 查询缺陷类型 → 调用 get_defect_types
4. 查询任务列表 → 调用 get_task_list
5. 查询任务详情 → 调用 get_task_detail
6. 查询历史记录 → 调用 get_history_records
7. 分析缺陷分布 → 调用 analyze_defects
8. 计算良品率 → 调用 calculate_pass_rate
9. 查询用户 → 调用 query_user_list
10. 无需工具时直接回答

回复要求：统计数据用数字说话、适当给出趋势判断、简洁专业中文回复"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(llm=self.llm, tools=ANALYSIS_TOOLS, prompt=prompt)
        self.executor = AgentExecutor(
            agent=agent, tools=ANALYSIS_TOOLS, verbose=True,
            max_iterations=5, return_intermediate_steps=True,
        )
        logger.info("AnalysisAgent 初始化完成，绑定 %d 个工具", len(ANALYSIS_TOOLS))

    async def chat(self, message: str, session_id: str = None, user_id: int = 1) -> dict:
        chat_history = self._load_history(user_id, session_id) if session_id else []

        if self.use_simulated_mode:
            result = _simulate_analysis_chat(message)
        else:
            try:
                result = await self.executor.ainvoke({
                    "input": message, "chat_history": chat_history,
                })
                result = {"output": result.get("output", ""),
                          "intermediate_steps": result.get("intermediate_steps", [])}
            except Exception as e:
                logger.error("AnalysisAgent 执行异常: %s", str(e), exc_info=True)
                result = _simulate_analysis_chat(message)

        if session_id:
            conversation_memory.save_message(user_id, session_id, "user", message)
            conversation_memory.save_message(user_id, session_id, "ai", result["output"])
        return result

    async def chat_stream(self, message: str, image_path: str = None,
                          user_id: int = 1, session_id: str = None) -> AsyncGenerator:
        chat_history = self._load_history(user_id, session_id) if session_id else []

        if self.use_simulated_mode:
            full_output = ""
            async for event in _simulate_analysis_stream(message):
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
                    yield {"type": "thinking", "content": "分析中…"}
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
            logger.warning("AnalysisAgent LLM 失败，降级: %s", str(e))
            yield {"type": "thinking", "content": "降级模式处理中…"}
            async for event in _simulate_analysis_stream(message):
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


def _simulate_analysis_chat(message: str) -> dict:
    """模拟模式：按关键词直接调用工具"""
    import json as _json
    from app.agent.tools.analysis_tool import (
        get_statistics_overview, get_defect_types, get_task_list,
        get_history_records, get_task_detail, analyze_defects, query_detection_stats,
    )
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in ["概览", "统计", "overview"]):
        result = get_statistics_overview.invoke({})
    elif any(kw in msg_lower for kw in ["缺陷类型", "defect"]):
        result = get_defect_types.invoke({})
    elif any(kw in msg_lower for kw in ["今天", "最近", "统计", "stats"]):
        result = query_detection_stats.invoke({"days": 30})
    elif any(kw in msg_lower for kw in ["任务", "task"]):
        result = get_task_list.invoke({"page": 1, "page_size": 5})
    elif any(kw in msg_lower for kw in ["历史", "记录", "history"]):
        result = get_history_records.invoke({"page": 1, "page_size": 5})
    elif any(kw in msg_lower for kw in ["良品率", "pass rate"]):
        return {"output": "请提供 PCB 批次 ID 以计算良品率。", "intermediate_steps": []}
    else:
        return {"output": "数据分析助手已就绪！我可以帮您查询统计信息、分析缺陷分布、计算良品率等。", "intermediate_steps": []}

    try:
        data = _json.loads(result)
        if "error" in data:
            output = f"查询失败：{data['error']}"
        else:
            total = data.get("total", data.get("total_tasks", "N/A"))
            output = f"查询完成，共 {total} 条记录。"
    except Exception:
        output = "查询完成。"
    return {"output": output, "intermediate_steps": []}


async def _simulate_analysis_stream(message: str):
    """模拟模式流式输出"""
    result = _simulate_analysis_chat(message)
    output = result["output"]
    yield {"type": "thinking", "content": "分析请求，准备查询数据…"}
    for i in range(0, len(output), 3):
        yield {"type": "text_chunk", "content": output[i:i + 3]}
        import asyncio
        await asyncio.sleep(0.01)


analysis_agent = AnalysisAgent()
