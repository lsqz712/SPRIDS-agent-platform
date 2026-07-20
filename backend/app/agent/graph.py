"""LangGraph agent graph definition — the core orchestrator."""

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import AgentState
from app.agent.supervisor import supervisor_node
from app.agent.agents.detection_agent import detection_agent_node
from app.agent.agents.analysis_agent import analysis_agent_node
from app.agent.agents.qa_agent import qa_agent_node

MAX_AGENT_ITERATIONS = 5


def route_after_supervisor(state: AgentState) -> str:
    """Map supervisor decision to next node."""
    return state.next_agent


def route_after_agent(state: AgentState) -> str:
    """After a sub-agent finishes, either loop back or end."""
    if state.error:
        return "qa_agent"

    if state.iteration_count >= MAX_AGENT_ITERATIONS:
        return END

    if state.final_response:
        return END

    return "supervisor"


def build_agent_graph(llm, tools: list) -> StateGraph:
    """Construct and compile the LangGraph agent graph."""

    workflow = StateGraph(AgentState)

    # Add nodes — lambda wrappers pass llm/tools into the node functions
    workflow.add_node("supervisor", lambda s: supervisor_node(s, llm))
    workflow.add_node("detection_agent", lambda s: detection_agent_node(s, llm, tools))
    workflow.add_node("analysis_agent", lambda s: analysis_agent_node(s, llm, tools))
    workflow.add_node("qa_agent", lambda s: qa_agent_node(s, llm, tools))

    # Edges
    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges("supervisor", route_after_supervisor, {
        "detection_agent": "detection_agent",
        "analysis_agent": "analysis_agent",
        "qa_agent": "qa_agent",
    })

    for agent in ["detection_agent", "analysis_agent", "qa_agent"]:
        workflow.add_conditional_edges(agent, route_after_agent, {
            "supervisor": "supervisor",
            "qa_agent": "qa_agent",
            END: END,
        })

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
