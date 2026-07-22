"""Analysis agent — analyses detection results and provides statistical insights."""

import asyncio

from langchain_core.language_models import BaseChatModel

from app.agent.state import AgentState
from app.core.logger import get_logger

logger = get_logger(__name__)


def analysis_agent_node(state: AgentState, llm: BaseChatModel, tools: list) -> dict:
    """Analyse PCB detection results using the full AnalysisAgent."""

    try:
        from app.agent.analysis_agent import analysis_agent

        msg = state.user_input
        if state.detection_result:
            dr = state.detection_result
            msg = (
                f"{msg}\n[当前检测结果：{dr.get('total_objects', 0)} 个目标，"
                f"类别分布: {dr.get('class_counts', {})}]"
            )

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                analysis_agent.chat(
                    message=msg,
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
        logger.error("Analysis agent node failed: %s", str(e))
        return {
            "messages": [{"role": "assistant", "content": f"分析失败：{str(e)}"}],
            "final_response": f"分析失败：{str(e)}",
            "iteration_count": state.iteration_count + 1,
        }
