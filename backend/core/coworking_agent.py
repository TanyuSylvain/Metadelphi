"""
Coworking Agent Implementation

LangGraph-based agent with tool calling for workspace file operations,
code execution, and document generation. Uses bind_tools for native
tool calling with SSE streaming for fine-grained progress updates.
"""

import os
import json
import logging
import re
from typing import Optional, AsyncGenerator, Dict, Any, List

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from backend.config import settings
from backend.providers import ProviderFactory
from backend.storage import ConversationStorage, MemoryStorage
from backend.utils import TextProcessor
from backend.utils.citation import (
    CITATION_SYSTEM_INSTRUCTION,
    extract_citations_from_result,
)
from backend.utils.parallel_tools import (
    ToolCallSpec,
    ToolResult,
    execute_tools_parallel,
)
from backend.tools.workspace_tools import create_workspace_tools
from backend.tools.web_search import get_web_search_tools
from backend.core.coworking_prompts import COWORKING_SYSTEM_PROMPT, COWORKING_PLANNING_PROMPT

logger = logging.getLogger(__name__)

COWORKING_WORKSPACE_PATH_KEY = "coworking_workspace_path"
COWORKING_BASELINE_FILES_KEY = "coworking_baseline_files"
COWORKING_GENERATED_FILES_KEY = "coworking_generated_files"
COWORKING_DELETED_FILES_KEY = "coworking_deleted_files"
LEGACY_INITIAL_WORKSPACE_FILES_KEY = "initial_workspace_files"
LEGACY_CONVERSATION_GENERATED_FILES_KEY = "conversation_generated_files"
FILE_TRACKING_RESET_NOTICE = (
    "Coworking file tracking was reset because the workspace changed outside tracked "
    "coworking actions. The baseline was rebuilt from the current workspace."
)


def _normalize_file_list(paths: Optional[List[str]]) -> List[str]:
    """Normalize a stored file list to unique, sorted relative paths."""
    if not paths:
        return []
    normalized = set()
    for path in paths:
        if not path:
            continue
        normalized.add(str(path).replace("\\", "/"))
    return sorted(normalized)


def _list_workspace_files(workspace_path: str) -> List[str]:
    """List all non-hidden files in workspace as relative paths."""
    all_files = []
    try:
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file_name in files:
                if file_name.startswith('.'):
                    continue
                rel_path = os.path.relpath(os.path.join(root, file_name), workspace_path)
                all_files.append(rel_path.replace("\\", "/"))
    except Exception:
        pass
    return sorted(all_files)


def _build_tracking_metadata(
    workspace_path: str,
    baseline_files: List[str],
    generated_files: List[str],
    deleted_files: List[str]
) -> Dict[str, Any]:
    """Build the coworking tracking payload persisted in conversation metadata."""
    baseline_files = _normalize_file_list(baseline_files)
    generated_files = _normalize_file_list(generated_files)
    deleted_files = _normalize_file_list(deleted_files)
    return {
        COWORKING_WORKSPACE_PATH_KEY: os.path.abspath(workspace_path),
        COWORKING_BASELINE_FILES_KEY: baseline_files,
        COWORKING_GENERATED_FILES_KEY: generated_files,
        COWORKING_DELETED_FILES_KEY: deleted_files,
        # Keep legacy keys aligned for older readers.
        LEGACY_INITIAL_WORKSPACE_FILES_KEY: baseline_files,
        LEGACY_CONVERSATION_GENERATED_FILES_KEY: generated_files,
    }


def _looks_like_plan_only_response(text: str) -> bool:
    """Heuristic for detecting a numbered planning response with no execution."""
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False

    numbered_lines = 0
    for line in stripped.splitlines():
        if re.match(r"^\s*\d+[\.\)、)]\s*", line):
            numbered_lines += 1

    has_plan_language = any(
        phrase in stripped.lower()
        for phrase in ("plan", "steps", "step-by-step", "first,", "first ", "execute", "tool")
    )
    return numbered_lines >= 2 or (numbered_lines >= 1 and has_plan_language)


def _extract_tracking_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Extract coworking tracking state from conversation metadata."""
    baseline_files = metadata.get(COWORKING_BASELINE_FILES_KEY)
    generated_files = metadata.get(COWORKING_GENERATED_FILES_KEY)
    deleted_files = metadata.get(COWORKING_DELETED_FILES_KEY)

    if baseline_files is None and metadata.get(LEGACY_INITIAL_WORKSPACE_FILES_KEY) is not None:
        baseline_files = metadata.get(LEGACY_INITIAL_WORKSPACE_FILES_KEY)
        generated_files = metadata.get(LEGACY_CONVERSATION_GENERATED_FILES_KEY, [])
        deleted_files = []

    return {
        "workspace_path": metadata.get(COWORKING_WORKSPACE_PATH_KEY),
        "baseline_files": _normalize_file_list(baseline_files),
        "generated_files": _normalize_file_list(generated_files),
        "deleted_files": _normalize_file_list(deleted_files),
        "initialized": baseline_files is not None,
    }


async def ensure_coworking_session_state(
    storage: ConversationStorage,
    conversation_id: str,
    workspace_path: str,
    add_reset_notice_message: bool = False,
) -> Dict[str, Any]:
    """
    Load, validate, and if needed reset the coworking session file state.

    The predicted workspace state is:
        baseline_files + generated_files - deleted_files

    If the real workspace differs, the baseline is rebuilt from the current workspace
    and the delta lists are cleared.
    """
    workspace_path = os.path.abspath(workspace_path)
    conversation = await storage.get_conversation(conversation_id)
    metadata = (conversation or {}).get("metadata", {})
    tracking = _extract_tracking_metadata(metadata)
    actual_files = _list_workspace_files(workspace_path)
    actual_set = set(actual_files)

    state_changed = False
    did_reset = False
    reset_notice = None

    stored_workspace_path = tracking["workspace_path"]
    if stored_workspace_path and os.path.abspath(stored_workspace_path) != workspace_path:
        tracking["baseline_files"] = actual_files
        tracking["generated_files"] = []
        tracking["deleted_files"] = []
        tracking["initialized"] = True
        state_changed = True
    elif not tracking["initialized"]:
        tracking["baseline_files"] = actual_files
        tracking["generated_files"] = []
        tracking["deleted_files"] = []
        tracking["initialized"] = True
        state_changed = True
    else:
        predicted_set = (
            set(tracking["baseline_files"])
            | set(tracking["generated_files"])
        ) - set(tracking["deleted_files"])
        if predicted_set != actual_set:
            tracking["baseline_files"] = actual_files
            tracking["generated_files"] = []
            tracking["deleted_files"] = []
            state_changed = True
            did_reset = True
            reset_notice = FILE_TRACKING_RESET_NOTICE
        else:
            # Re-normalize delta lists against the baseline when state is still valid.
            baseline_set = set(tracking["baseline_files"])
            generated_files = sorted(actual_set - baseline_set)
            deleted_files = sorted(baseline_set - actual_set)
            if (
                generated_files != tracking["generated_files"]
                or deleted_files != tracking["deleted_files"]
            ):
                tracking["generated_files"] = generated_files
                tracking["deleted_files"] = deleted_files
                state_changed = True

    if state_changed:
        await storage.update_conversation_metadata(
            conversation_id,
            _build_tracking_metadata(
                workspace_path=workspace_path,
                baseline_files=tracking["baseline_files"],
                generated_files=tracking["generated_files"],
                deleted_files=tracking["deleted_files"],
            ),
        )

    if did_reset and add_reset_notice_message:
        await storage.add_message(
            conversation_id=conversation_id,
            role="system",
            content=FILE_TRACKING_RESET_NOTICE,
            metadata={"event": "coworking_file_tracking_reset"},
        )

    return {
        "baseline_files": tracking["baseline_files"],
        "generated_files": tracking["generated_files"],
        "deleted_files": tracking["deleted_files"],
        "actual_files": actual_files,
        "did_reset": did_reset,
        "reset_notice": reset_notice,
    }


async def recompute_coworking_session_deltas(
    storage: ConversationStorage,
    conversation_id: str,
    workspace_path: str,
    baseline_files: List[str],
) -> Dict[str, Any]:
    """Recompute and persist the coworking generated/deleted lists for the session."""
    workspace_path = os.path.abspath(workspace_path)
    actual_files = _list_workspace_files(workspace_path)
    actual_set = set(actual_files)
    baseline_set = set(_normalize_file_list(baseline_files))
    generated_files = sorted(actual_set - baseline_set)
    deleted_files = sorted(baseline_set - actual_set)

    await storage.update_conversation_metadata(
        conversation_id,
        _build_tracking_metadata(
            workspace_path=workspace_path,
            baseline_files=list(baseline_set),
            generated_files=generated_files,
            deleted_files=deleted_files,
        ),
    )

    return {
        "baseline_files": sorted(baseline_set),
        "generated_files": generated_files,
        "deleted_files": deleted_files,
        "actual_files": actual_files,
    }


class CoworkingAgent:
    """Coworking agent with tool calling for workspace operations."""

    def __init__(
        self,
        model_id: str,
        provider_name: Optional[str] = None,
        storage: Optional[ConversationStorage] = None,
        temperature: float = None,
        thinking: bool = False
    ):
        self.model_id = model_id
        self.provider_name = provider_name
        self.thinking = thinking

        # Initialize base LLM (without tools — we bind tools per-invocation)
        self.llm = ProviderFactory.create_llm(
            model_id=model_id,
            provider_name=provider_name,
            temperature=temperature,
            thinking=thinking
        )

        self.storage = storage or MemoryStorage()

    async def stream(
        self,
        question: str,
        conversation_id: str,
        workspace_path: str,
        max_iterations: int = 25,
        web_search: bool = False
    ) -> AsyncGenerator[dict, None]:
        """
        Stream the coworking agent's response with SSE events.

        Args:
            question: User's message
            conversation_id: Conversation ID for storage
            workspace_path: Absolute path to workspace directory
            max_iterations: Maximum ReAct loop iterations
            web_search: Enable web search tools

        Yields:
            Dict events: plan, thinking_chunk, tool_start, tool_result,
                        file_created, file_deleted, session_notice,
                        response_chunk, done, error
        """
        # Ensure workspace exists
        os.makedirs(workspace_path, exist_ok=True)

        # Create workspace-bound tools
        tools = create_workspace_tools(workspace_path)
        if web_search:
            search_tools = await get_web_search_tools()
            tools.extend(search_tools)
        tool_map = {t.name: t for t in tools}

        # Bind tools to LLM
        llm_with_tools = self.llm.bind_tools(tools)

        # Build system message
        system_content = COWORKING_SYSTEM_PROMPT.format(workspace_path=workspace_path)
        system_message = SystemMessage(content=system_content)

        # Load conversation history
        history = []
        is_new_conversation = False
        conversation = await self.storage.get_conversation(conversation_id)
        is_new_conversation = conversation is None
        messages = await self.storage.get_messages(conversation_id)
        history = [{"role": msg["role"], "content": msg["content"]} for msg in messages]

        # Save user message to storage
        await self.storage.add_message(
            conversation_id=conversation_id,
            role="user",
            content=question,
            model=self.model_id
        )
        if is_new_conversation:
            title = question[:50] + "..." if len(question) > 50 else question
            await self.storage.update_conversation_title(conversation_id, title)

        session_state = await ensure_coworking_session_state(
            storage=self.storage,
            conversation_id=conversation_id,
            workspace_path=workspace_path,
            add_reset_notice_message=True,
        )

        # Build message list: system + history + current question
        chat_messages = [system_message]
        if web_search:
            chat_messages.append(SystemMessage(content=CITATION_SYSTEM_INSTRUCTION))
        for msg in history:
            if msg["role"] == "user":
                chat_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                chat_messages.append(AIMessage(content=msg["content"]))

        # Add planning instruction + user question
        user_content = f"{COWORKING_PLANNING_PROMPT}\n\nUser request: {question}"
        chat_messages.append(HumanMessage(content=user_content))

        # Track state
        iteration = 0
        final_response = ""
        citations = []

        previous_files_data = []
        for file_path in session_state["generated_files"]:
            try:
                file_size = os.path.getsize(os.path.join(workspace_path, file_path))
            except Exception:
                file_size = 0
            previous_files_data.append({"path": file_path, "size": file_size})
        yield {
            "type": "previous_files",
            "files": previous_files_data,
            "deleted_files": session_state["deleted_files"],
        }
        if session_state["did_reset"]:
            yield {
                "type": "session_notice",
                "message": session_state["reset_notice"],
            }

        try:
            # === Planning + ReAct Loop ===
            while iteration < max_iterations:
                iteration += 1

                # Stream agent response token-by-token
                full_content = ""
                tool_calls = []

                async for chunk in llm_with_tools.astream(chat_messages):
                    # Accumulate content
                    if hasattr(chunk, 'content') and chunk.content:
                        text = TextProcessor.extract_text_content(chunk.content)
                        if text:
                            full_content += text
                            if iteration == 1 and not tool_calls:
                                yield {"type": "thinking_chunk", "content": text}
                            else:
                                yield {"type": "response_chunk", "content": text}

                    # Accumulate tool calls from streaming chunks
                    if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                        for tc_chunk in chunk.tool_call_chunks:
                            # Find or create the tool call entry
                            tc_idx = tc_chunk.get("index", 0)
                            while len(tool_calls) <= tc_idx:
                                tool_calls.append({"id": "", "name": "", "args": ""})
                            if tc_chunk.get("id"):
                                tool_calls[tc_idx]["id"] = tc_chunk["id"]
                            if tc_chunk.get("name"):
                                tool_calls[tc_idx]["name"] = tc_chunk["name"]
                            if tc_chunk.get("args"):
                                tool_calls[tc_idx]["args"] += tc_chunk["args"]

                # If streaming didn't give us tool_calls via chunks, do a non-streaming
                # fallback to get the complete message with tool_calls
                if not tool_calls:
                    # Some models stop after producing a numbered plan on later turns.
                    # Reprompt once to continue with tool execution instead of ending early.
                    if _looks_like_plan_only_response(full_content) and iteration < max_iterations:
                        chat_messages.append(AIMessage(content=full_content))
                        chat_messages.append(HumanMessage(
                            content=(
                                "Continue by executing the plan now using the available tools. "
                                "Do not restate the plan unless needed."
                            )
                        ))
                        continue

                    # Check if there's an accumulated response with no tool calls = done
                    ai_msg = AIMessage(content=full_content)
                    chat_messages.append(ai_msg)
                    final_response = full_content
                    break

                # We have tool calls — build the proper AIMessage with tool_calls
                parsed_tool_calls = []
                for tc in tool_calls:
                    if tc["name"]:
                        try:
                            args = json.loads(tc["args"]) if tc["args"] else {}
                        except json.JSONDecodeError:
                            args = {"input": tc["args"]}
                        parsed_tool_calls.append({
                            "id": tc["id"] or f"call_{iteration}_{tc['name']}",
                            "name": tc["name"],
                            "args": args
                        })

                if not parsed_tool_calls:
                    # No valid tool calls found, treat as final response
                    ai_msg = AIMessage(content=full_content)
                    chat_messages.append(ai_msg)
                    final_response = full_content
                    break

                # Append AI message with tool calls to history
                ai_msg = AIMessage(
                    content=full_content,
                    tool_calls=parsed_tool_calls
                )
                chat_messages.append(ai_msg)

                # Build tool call specs for parallel execution
                tool_specs = [
                    ToolCallSpec(
                        id=tc["id"],
                        name=tc["name"],
                        args=tc["args"],
                        index=idx
                    )
                    for idx, tc in enumerate(parsed_tool_calls)
                ]

                # Build a mapping from tool_call_id to original tool call info
                tc_info_map: Dict[str, Dict[str, Any]] = {
                    tc["id"]: tc for tc in parsed_tool_calls
                }

                # Yield tool_start events for all tools upfront
                for spec in tool_specs:
                    yield {
                        "type": "tool_start",
                        "tool_name": spec.name,
                        "tool_input": spec.args
                    }

                workspace_before = set(_list_workspace_files(workspace_path))

                # Execute tools in parallel
                results: List[ToolResult] = await execute_tools_parallel(
                    tool_map=tool_map,
                    tool_calls=tool_specs,
                    max_concurrency=settings.max_tool_concurrency,
                    timeout=60.0
                )

                # Process results in original order
                for result in results:
                    tc_info = tc_info_map.get(result.tool_call_id, {})
                    tool_name = tc_info.get("name", "unknown")

                    # Truncate very long results for display
                    display_result = result.content
                    if len(display_result) > 2000:
                        display_result = display_result[:2000] + "\n[... truncated]"

                    yield {
                        "type": "tool_result",
                        "tool_name": tool_name,
                        "output": display_result,
                        "success": result.success
                    }

                    # Add tool result to message history
                    tool_message = ToolMessage(
                        content=result.content,
                        tool_call_id=result.tool_call_id
                    )
                    chat_messages.append(tool_message)

                    # Extract citations from search tool results
                    if "search" in tool_name.lower():
                        extract_citations_from_result(result.content, citations)

                workspace_after = set(_list_workspace_files(workspace_path))
                baseline_set = set(session_state["baseline_files"])
                added_files = sorted(workspace_after - workspace_before)
                removed_files = sorted(workspace_before - workspace_after)

                for file_path in added_files:
                    if file_path not in baseline_set:
                        try:
                            file_size = os.path.getsize(os.path.join(workspace_path, file_path))
                        except Exception:
                            file_size = 0
                        yield {
                            "type": "file_created",
                            "file_path": file_path,
                            "file_size": file_size,
                        }

                for file_path in removed_files:
                    if file_path in baseline_set:
                        yield {
                            "type": "file_deleted",
                            "file_path": file_path,
                        }

                # Continue the ReAct loop (agent will process tool results)

            else:
                # Hit max iterations
                final_response = full_content or "Reached maximum iteration limit."
                yield {
                    "type": "error",
                    "error": f"Reached maximum of {max_iterations} iterations"
                }

            # Convert math delimiters
            final_response = TextProcessor.convert_math_delimiters(final_response)

            # Save assistant response to storage
            if final_response:
                await self.storage.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=final_response,
                    model=self.model_id
                )

            final_file_state = await recompute_coworking_session_deltas(
                storage=self.storage,
                conversation_id=conversation_id,
                workspace_path=workspace_path,
                baseline_files=session_state["baseline_files"],
            )

            final_generated_files = []
            for file_path in final_file_state["generated_files"]:
                try:
                    file_size = os.path.getsize(os.path.join(workspace_path, file_path))
                except Exception:
                    file_size = 0
                final_generated_files.append({"path": file_path, "size": file_size})

            # Emit citations if any were collected
            if citations:
                yield {"type": "citations", "citations": citations}

            yield {
                "type": "done",
                "final_answer": final_response,
                "generated_files": final_generated_files,
                "deleted_files": final_file_state["deleted_files"],
            }

        except Exception as e:
            logger.error(f"Coworking agent error: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }

    async def invoke(
        self,
        question: str,
        conversation_id: str,
        workspace_path: str,
        max_iterations: int = 25,
        web_search: bool = False
    ) -> dict:
        """
        Run the coworking agent and return the final result.

        Args:
            question: User's message
            conversation_id: Conversation ID
            workspace_path: Workspace directory path
            max_iterations: Maximum iterations
            web_search: Enable web search tools

        Returns:
            Dict with final_answer, generated_files, and deleted_files
        """
        result = {"final_answer": "", "generated_files": [], "deleted_files": []}
        async for event in self.stream(question, conversation_id, workspace_path, max_iterations, web_search):
            if event["type"] == "done":
                result["final_answer"] = event.get("final_answer", "")
                result["generated_files"] = event.get("generated_files", [])
                result["deleted_files"] = event.get("deleted_files", [])
            elif event["type"] == "error":
                result["final_answer"] = f"Error: {event.get('error', 'Unknown error')}"
        return result
