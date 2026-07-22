"""LangGraph state definition for SPRIDS agent."""

from typing import Annotated, Any, Optional
import operator

from pydantic import BaseModel, Field


class AgentState(BaseModel):
    """Shared state flowing through the agent graph."""

    # Conversation
    messages: Annotated[list[dict[str, Any]], operator.add] = Field(default_factory=list)
    conversation_id: Optional[str] = None
    user_id: Optional[int] = None
    session_id: Optional[str] = None

    # Current request
    user_input: str = ""
    attached_images: list[str] = Field(default_factory=list)

    # Detection results
    detection_result: Optional[dict[str, Any]] = None
    detection_image_key: Optional[str] = None

    # Supervisor routing
    next_agent: str = "supervisor"
    iteration_count: int = 0

    # Final response to user
    final_response: str = ""

    # Error handling
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
