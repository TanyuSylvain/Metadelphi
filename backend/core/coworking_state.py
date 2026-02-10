"""
Coworking Agent State Schema

TypedDict state for the coworking agent's LangGraph workflow.
"""

from typing import TypedDict, Annotated, Optional, List
from langgraph.graph.message import add_messages


class PlanStep(TypedDict):
    """A single step in the workflow plan."""
    step_number: int
    description: str
    status: str  # "pending" | "active" | "done" | "skipped"


class CoworkingState(TypedDict):
    """State for the coworking agent LangGraph workflow."""
    messages: Annotated[list, add_messages]  # Full message history (LangGraph managed)
    workspace_path: str                       # User's workspace directory
    plan: Optional[List[PlanStep]]            # Workflow plan steps
    iteration: int                            # Current ReAct loop count
    max_iterations: int                       # Safety limit (default 25)
    generated_files: List[str]                # Paths of created/modified files
    status: str                               # "planning" | "executing" | "completed" | "error"


def create_initial_state(
    workspace_path: str,
    max_iterations: int = 25
) -> CoworkingState:
    """
    Create initial state for a new coworking agent run.

    Args:
        workspace_path: User's workspace directory
        max_iterations: Safety limit for ReAct loop

    Returns:
        Initial CoworkingState
    """
    return CoworkingState(
        messages=[],
        workspace_path=workspace_path,
        plan=None,
        iteration=0,
        max_iterations=max_iterations,
        generated_files=[],
        status="planning"
    )
