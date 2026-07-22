"""Detection agent — runs PCB defect detection on uploaded images."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import DETECTION_AGENT_PROMPT
from app.agent.state import AgentState


def detection_agent_node(state: AgentState, llm: BaseChatModel, tools: list) -> dict:
    """Handle PCB defect detection requests using detection tools."""

    prompt = f"""User request: {state.user_input}
Number of attached images: {len(state.attached_images)}
Current detection status: {'completed' if state.detection_result else 'not yet run'}

If an image is attached and detection hasn't been run yet, use the appropriate detection tool (detect_single_image / detect_batch_images / detect_zip_images_file / detect_video_file).
Otherwise, explain the existing detection results to the user in natural language."""

    messages = [
        SystemMessage(content=DETECTION_AGENT_PROMPT),
        HumanMessage(content=prompt),
    ]

    llm_with_tools = llm.bind_tools(tools) if tools else llm
    response = llm_with_tools.invoke(messages)

    final_text = response.content if hasattr(response, "content") else str(response)

    return {
        "messages": [{"role": "assistant", "content": final_text}],
        "final_response": final_text if not _has_tool_calls(response) else "",
        "iteration_count": state.iteration_count + 1,
    }


def _has_tool_calls(response) -> bool:
    return bool(getattr(response, "tool_calls", None)
                or getattr(response, "additional_kwargs", {}).get("tool_calls"))
