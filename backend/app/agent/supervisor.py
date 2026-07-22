"""Supervisor agent — routes incoming requests to the right sub-agent via LLM."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import SUPERVISOR_SYSTEM_PROMPT
from app.agent.state import AgentState

VALID_AGENTS = {"detection_agent", "analysis_agent", "qa_agent"}


def supervisor_node(state: AgentState, llm: BaseChatModel) -> dict:
    """Decide which agent should handle the current user request."""

    # Fallback: rule-based routing when LLM is unavailable
    if llm is None:
        return _rule_based_route(state)

    try:
        recent = state.messages[-6:] if state.messages else []
        context = "\n".join(
            f"[{m.get('role', 'user')}]: {str(m.get('content', ''))[:500]}" for m in recent
        )

        prompt = f"""Conversation history:
{context}

User's latest request: {state.user_input}
Attached images: {len(state.attached_images)}

Which agent should handle this? Respond with exactly ONE of: detection_agent, analysis_agent, qa_agent."""

        messages = [
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = llm.invoke(messages)
        next_agent = response.content.strip().lower() if hasattr(response, "content") else str(response).strip().lower()

        if next_agent not in VALID_AGENTS:
            next_agent = "qa_agent"

        return {
            "next_agent": next_agent,
            "messages": [{"role": "supervisor", "content": f"Routing to {next_agent}"}],
        }
    except Exception:
        return _rule_based_route(state)


def _rule_based_route(state: AgentState) -> dict:
    """Rule-based fallback routing when LLM unavailable."""
    msg = state.user_input.lower()

    if state.attached_images:
        return {"next_agent": "detection_agent", "messages": [{"role": "supervisor", "content": "Routing to detection_agent (image attached)"}]}

    detection_kw = {"检测", "识别", "缺陷", "图片", "照片", "摄像头", "视频", "camera", "video", "zip", "batch"}
    analysis_kw = {"统计", "分析", "趋势", "报表", "良品率", "任务", "历史", "概览", "分布", "多少"}
    knowledge_kw = {"知识", "原理", "定义", "什么是", "how", "what", "why", "iou", "yolo", "算法", "怎么", "如何"}

    # 优先级：detection > analysis > knowledge（默认 qa_agent）
    for kw in detection_kw:
        if kw in msg:
            return {"next_agent": "detection_agent", "messages": [{"role": "supervisor", "content": "Routing to detection_agent"}]}

    for kw in analysis_kw:
        if kw in msg:
            return {"next_agent": "analysis_agent", "messages": [{"role": "supervisor", "content": "Routing to analysis_agent"}]}

    for kw in knowledge_kw:
        if kw in msg:
            return {"next_agent": "qa_agent", "messages": [{"role": "supervisor", "content": "Routing to qa_agent"}]}

    return {"next_agent": "qa_agent", "messages": [{"role": "supervisor", "content": "Routing to qa_agent (default)"}]}
