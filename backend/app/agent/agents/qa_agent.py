"""QA agent — answers general questions about PCB defect detection and the platform."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import QA_AGENT_PROMPT
from app.agent.state import AgentState


def qa_agent_node(state: AgentState, llm: BaseChatModel, tools: list) -> dict:
    """Answer user questions about PCB defect detection, YOLO models, or the platform."""

    prompt = f"""User request: {state.user_input}

Provide a helpful, concise, and technically accurate answer. Use the search_knowledge tool if you need to look up specific domain knowledge."""

    messages = [
        SystemMessage(content=QA_AGENT_PROMPT),
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
