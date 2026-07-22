"""Detection agent — runs PCB defect detection on uploaded images."""

import asyncio

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import DETECTION_AGENT_PROMPT
from app.agent.state import AgentState
from app.core.logger import get_logger

logger = get_logger(__name__)


def detection_agent_node(state: AgentState, llm: BaseChatModel, tools: list) -> dict:
    """Handle PCB defect detection requests using the full DetectionAgent."""

    # Use the full detection agent (with ReAct + memory) for robust tool execution
    try:
        from app.agent.detection_agent import detection_agent

        msg = state.user_input
        if state.attached_images:
            image_path = state.attached_images[0]
            msg = f"{msg}\n[附件图片路径: {image_path}]"

        # Run the agent synchronously via asyncio
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                detection_agent.chat(
                    message=msg,
                    user_id=state.user_id or 1,
                    session_id=state.session_id or "",
                )
            )
        finally:
            loop.close()

        output = result.get("output", "")
        detection_result = None
        for step in result.get("intermediate_steps", []):
            if isinstance(step, tuple) and len(step) == 2:
                tool_result = step[1]
                if isinstance(tool_result, str):
                    import json as _json
                    try:
                        parsed = _json.loads(tool_result)
                        if "total_objects" in parsed or "task_id" in parsed:
                            detection_result = parsed
                    except Exception:
                        pass

        return {
            "messages": [{"role": "assistant", "content": output}],
            "final_response": output,
            "detection_result": detection_result,
            "iteration_count": state.iteration_count + 1,
        }
    except Exception as e:
        logger.error("Detection agent node failed: %s", str(e))
        return {
            "messages": [{"role": "assistant", "content": f"检测失败：{str(e)}"}],
            "final_response": f"检测失败：{str(e)}",
            "iteration_count": state.iteration_count + 1,
        }
