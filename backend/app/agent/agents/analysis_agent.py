"""Analysis agent — analyses detection results and provides statistical insights."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import ANALYSIS_AGENT_PROMPT
from app.agent.state import AgentState


def analysis_agent_node(state: AgentState, llm: BaseChatModel, tools: list) -> dict:
    """Analyse PCB detection results and provide defect statistics."""

    detection_info = ""
    if state.detection_result:
        dr = state.detection_result
        detection_info = (
            f"Detection results available: {dr.get('total_objects', 0)} defects found.\n"
            f"Class distribution: {dr.get('class_counts', {})}\n"
            f"Inference time: {dr.get('total_inference_time', 0)}ms"
        )

    prompt = f"""User request: {state.user_input}
{detection_info}

Analyse the detection results and provide insights. Use analysis tools (get_statistics_overview, analyze_defects) if you need to compute statistics."""

    messages = [
        SystemMessage(content=ANALYSIS_AGENT_PROMPT),
        HumanMessage(content=prompt),
    ]

    llm_with_tools = llm.bind_tools(tools) if tools else llm
    response = llm_with_tools.invoke(messages)

    final_text = response.content if hasattr(response, "content") else str(response)

    return {
        "messages": [{"role": "assistant", "content": final_text}],
        "final_response": final_text,
        "iteration_count": state.iteration_count + 1,
    }
