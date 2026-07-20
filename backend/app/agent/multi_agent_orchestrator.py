"""
多 Agent 编排器 — 基于 LangGraph 的协作框架

职责：
  - 整合所有专业 Agent 和 Supervisor
  - 提供统一的对话接口
  - 支持流式输出
"""

import json
from typing import AsyncGenerator

from app.core.logger import get_logger
from app.agent.supervisor_agent import supervisor_agent
from app.agent.detection_agent import detection_agent
from app.agent.analysis_agent import analysis_agent
from app.agent.knowledge_agent import knowledge_agent
from app.agent.model_agent import model_agent

logger = get_logger(__name__)


class MultiAgentOrchestrator:
    """多 Agent 编排器 — 统一协调所有专业 Agent"""

    def __init__(self):
        self.agent_map = {
            "detection": detection_agent,
            "analysis": analysis_agent,
            "knowledge": knowledge_agent,
            "model": model_agent,
        }
        logger.info("MultiAgentOrchestrator 初始化完成，注册 %d 个专业 Agent", len(self.agent_map))

    async def route_and_execute(self, message: str, image_path: str = None, 
                                user_id: int = None, session_id: str = None) -> dict:
        """路由到对应 Agent 并执行"""
        route = await supervisor_agent.route(message)
        agent = self.agent_map.get(route)
        
        if not agent:
            logger.error(f"未找到路由 {route} 对应的 Agent")
            return {
                "route": route,
                "output": f"路由错误：未找到 {route} 对应的 Agent",
                "intermediate_steps": [],
            }

        logger.info(f"路由到 {route} Agent: {message[:50]}")

        try:
            if route == "detection" and image_path:
                result = await agent.chat(
                    message=message,
                    image_path=image_path,
                    user_id=user_id,
                    session_id=session_id,
                )
            else:
                result = await agent.chat(
                    message=message,
                    session_id=session_id,
                )

            return {
                "route": route,
                "output": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        except Exception as e:
            logger.error(f"{route} Agent 执行失败: {e}")
            return {
                "route": route,
                "output": f"{route} 智能体执行失败：{str(e)}",
                "intermediate_steps": [],
            }

    async def chat_stream(self, message: str, image_path: str = None,
                          user_id: int = None, session_id: str = None) -> AsyncGenerator[dict, None]:
        """流式对话 — 路由到对应 Agent 并返回流式结果"""
        route = await supervisor_agent.route(message)
        agent = self.agent_map.get(route)
        
        if not agent:
            yield {"type": "error", "content": f"路由错误：未找到 {route} 对应的 Agent"}
            return

        logger.info(f"流式路由到 {route} Agent: {message[:50]}")
        yield {"type": "route", "content": route}

        try:
            if route == "detection":
                async for event in agent.chat_stream(
                    message=message,
                    image_path=image_path,
                    user_id=user_id,
                    session_id=session_id,
                ):
                    yield event
            else:
                result = await agent.chat(
                    message=message,
                    session_id=session_id,
                )
                yield {"type": "text_chunk", "content": result.get("output", "")}

        except Exception as e:
            logger.error(f"{route} Agent 流式执行失败: {e}")
            yield {"type": "error", "content": f"{route} 智能体执行失败：{str(e)}"}


multi_agent_orchestrator = MultiAgentOrchestrator()