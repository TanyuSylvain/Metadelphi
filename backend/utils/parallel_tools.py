"""
Parallel Tool Execution Utility

Provides utilities for executing multiple tool calls in parallel with
concurrency control, timeout handling, and order preservation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from threading import Lock

from langchain_core.tools import BaseTool
from langchain_core.messages import ToolMessage

logger = logging.getLogger(__name__)


@dataclass
class ToolCallSpec:
    """Specification for a single tool call to execute."""
    id: str
    name: str
    args: Dict[str, Any]
    index: int = 0  # For order preservation


@dataclass
class ToolResult:
    """Result from executing a single tool."""
    tool_call_id: str
    content: str
    success: bool
    error: Optional[str] = None
    index: int = 0  # For order preservation


@dataclass
class ParallelExecutionProgress:
    """Thread-safe progress tracker for parallel execution."""
    completed: int = 0
    total: int = 0
    results: List[ToolResult] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def add_result(self, result: ToolResult):
        """Thread-safe addition of a result."""
        with self._lock:
            self.completed += 1
            self.results.append(result)

    def get_sorted_results(self) -> List[ToolResult]:
        """Get results sorted by original index."""
        with self._lock:
            return sorted(self.results, key=lambda r: r.index)


async def execute_single_tool(
    tool: BaseTool,
    spec: ToolCallSpec,
    timeout: float = 60.0
) -> ToolResult:
    """
    Execute a single tool with timeout and error handling.

    Args:
        tool: The LangChain tool to execute
        spec: Tool call specification with id, name, args, index
        timeout: Maximum execution time in seconds

    Returns:
        ToolResult with content, success status, and error if any
    """
    try:
        # Execute with timeout
        result = await asyncio.wait_for(
            tool.ainvoke(spec.args),
            timeout=timeout
        )
        return ToolResult(
            tool_call_id=spec.id,
            content=str(result),
            success=True,
            index=spec.index
        )
    except asyncio.TimeoutError:
        error_msg = f"Tool '{spec.name}' timed out after {timeout}s"
        logger.warning(error_msg)
        return ToolResult(
            tool_call_id=spec.id,
            content=error_msg,
            success=False,
            error="timeout",
            index=spec.index
        )
    except Exception as e:
        error_msg = f"Error executing {spec.name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ToolResult(
            tool_call_id=spec.id,
            content=error_msg,
            success=False,
            error=str(e),
            index=spec.index
        )


async def execute_tools_parallel(
    tool_map: Dict[str, BaseTool],
    tool_calls: List[ToolCallSpec],
    max_concurrency: int = 5,
    timeout: float = 60.0,
    on_tool_start: Optional[Callable[[ToolCallSpec], None]] = None,
    on_tool_complete: Optional[Callable[[ToolResult], None]] = None
) -> List[ToolResult]:
    """
    Execute multiple tool calls in parallel with concurrency control.

    Args:
        tool_map: Mapping of tool names to tool instances
        tool_calls: List of tool call specifications to execute
        max_concurrency: Maximum number of concurrent executions
        timeout: Maximum time per tool in seconds
        on_tool_start: Optional callback when a tool starts
        on_tool_complete: Optional callback when a tool completes

    Returns:
        List of ToolResults sorted by original call order
    """
    if not tool_calls:
        return []

    semaphore = asyncio.Semaphore(max_concurrency)
    progress = ParallelExecutionProgress(total=len(tool_calls))

    async def execute_with_semaphore(spec: ToolCallSpec) -> ToolResult:
        """Execute a tool call with semaphore for concurrency control."""
        async with semaphore:
            if on_tool_start:
                on_tool_start(spec)

            tool = tool_map.get(spec.name)
            if not tool:
                result = ToolResult(
                    tool_call_id=spec.id,
                    content=f"Error: Unknown tool '{spec.name}'",
                    success=False,
                    error="unknown_tool",
                    index=spec.index
                )
            else:
                result = await execute_single_tool(tool, spec, timeout)

            progress.add_result(result)

            if on_tool_complete:
                on_tool_complete(result)

            return result

    # Execute all tool calls concurrently
    tasks = [execute_with_semaphore(spec) for spec in tool_calls]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Return results in original order
    return progress.get_sorted_results()


def create_tool_messages(results: List[ToolResult]) -> List[ToolMessage]:
    """
    Convert ToolResults to LangChain ToolMessages.

    Args:
        results: List of tool execution results

    Returns:
        List of ToolMessage objects for conversation history
    """
    messages = []
    for result in results:
        messages.append(ToolMessage(
            content=result.content,
            tool_call_id=result.tool_call_id
        ))
    return messages
