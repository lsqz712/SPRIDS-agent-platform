"""QA agent — answers general questions about PCB defect detection and the platform."""

import asyncio

from langchain_core.language_models import BaseChatModel

from app.agent.state import AgentState
from app.core.logger import get_logger

logger = get_logger(__name__)


def qa_agent_node(state: AgentState, llm: BaseChatModel, tools: list) -> dict:
    """Answer user questions using the full KnowledgeAgent with RAG."""

    try:
        from app.agent.knowledge_agent import knowledge_agent

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                knowledge_agent.chat(
                    message=state.user_input,
                    user_id=state.user_id or 1,
                    session_id=state.session_id or "",
                )
            )
        finally:
            loop.close()

        output = result.get("output", "")
        return {
            "messages": [{"role": "assistant", "content": output}],
            "final_response": output,
            "iteration_count": state.iteration_count + 1,
        }
    except Exception as e:
        logger.error("QA agent node failed: %s", str(e))
        return {
            "messages": [{"role": "assistant", "content": f"问答失败：{str(e)}"}],
            "final_response": f"问答失败：{str(e)}",
            "iteration_count": state.iteration_count + 1,
        }
