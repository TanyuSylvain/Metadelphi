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
import asyncio
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
from backend.utils.metrics import MetricsCollector
from backend.utils.conversation_mode import record_used_mode
from backend.core.run_manager import RunCancelledError, RunContext, use_run_context

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


def _extract_plan_steps(text: str) -> List[Dict[str, Any]]:
    """Parse a numbered plan into display steps."""
    if not text:
        return []

    steps = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^(\d+)[\.\)、)]\s*(.+)$", stripped)
        if match:
            steps.append({
                "step_number": int(match.group(1)),
                "description": match.group(2).strip(),
            })

    if steps:
        return steps

    return [
        {"step_number": idx + 1, "description": line.strip()}
        for idx, line in enumerate(text.splitlines())
        if line.strip()
    ]


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
        max_iterations: Optional[int] = None,
        web_search: bool = False,
        run_context: Optional[RunContext] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream the coworking agent's response with SSE events.

        Args:
            question: User's message
            conversation_id: Conversation ID for storage
            workspace_path: Absolute path to workspace directory
            max_iterations: Maximum ReAct loop iterations. Defaults to
                settings.coworking_max_tool_iterations.
            web_search: Enable web search tools

        Yields:
            Dict events: plan_ready, round_start, reasoning_chunk, tool_start,
                        tool_result, round_complete, file_created, file_deleted,
                        session_notice, final_start, final_chunk, done, error
        """
        if max_iterations is None:
            max_iterations = settings.coworking_max_tool_iterations
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
            await self.storage.update_conversation_metadata(
                conversation_id,
                {"mode": "coworking"}
            )

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
        plan_emitted = False

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

        assistant_saved = False
        file_state_recomputed = False

        try:
            async with use_run_context(run_context):
                if run_context:
                    run_context.raise_if_cancelled()
            # === Planning + ReAct Loop ===
                metrics = None
                while iteration < max_iterations:
                    if run_context:
                        run_context.raise_if_cancelled()
                    iteration += 1

                    # Stream agent response token-by-token
                    full_content = ""
                    tool_calls = []
                    buffered_text = ""
                    saw_tool_call_chunks = False
                    round_started = False
                    # Create a fresh collector each iteration; only the final
                    # non-tool iteration's metrics will survive and be reported.
                    iteration_metrics = MetricsCollector()
                    iteration_metrics.start()

                    async for chunk in llm_with_tools.astream(chat_messages, stream_options={"include_usage": True}):
                        if run_context:
                            run_context.raise_if_cancelled()
                        # Accumulate content
                        text = ""
                        if hasattr(chunk, 'content') and chunk.content:
                            text = TextProcessor.extract_text_content(chunk.content)
                        iteration_metrics.on_chunk(text, chunk)
                        if text:
                            full_content += text
                            if saw_tool_call_chunks:
                                if not round_started:
                                    yield {"type": "round_start", "round": iteration}
                                    round_started = True
                                yield {
                                    "type": "reasoning_chunk",
                                    "round": iteration,
                                    "content": text,
                                }
                            else:
                                buffered_text += text

                        # Accumulate tool calls from streaming chunks
                        if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                            if not saw_tool_call_chunks:
                                saw_tool_call_chunks = True
                                if iteration == 1:
                                    plan_text = buffered_text.strip()
                                    if plan_text and not plan_emitted:
                                        yield {
                                            "type": "plan_ready",
                                            "steps": _extract_plan_steps(plan_text),
                                            "raw_text": plan_text,
                                        }
                                        plan_emitted = True
                                    buffered_text = ""
                                else:
                                    yield {"type": "round_start", "round": iteration}
                                    round_started = True
                                    if buffered_text:
                                        yield {
                                            "type": "reasoning_chunk",
                                            "round": iteration,
                                            "content": buffered_text,
                                        }
                                        buffered_text = ""

                            for tc_chunk in chunk.tool_call_chunks:
                                tc_idx = tc_chunk.get("index", 0)
                                while len(tool_calls) <= tc_idx:
                                    tool_calls.append({"id": "", "name": "", "args": ""})
                                if tc_chunk.get("id"):
                                    tool_calls[tc_idx]["id"] = tc_chunk["id"]
                                if tc_chunk.get("name"):
                                    tool_calls[tc_idx]["name"] = tc_chunk["name"]
                                if tc_chunk.get("args"):
                                    tool_calls[tc_idx]["args"] += tc_chunk["args"]

                    if not tool_calls:
                        # Final answer iteration — keep these metrics
                        metrics = iteration_metrics
                        if _looks_like_plan_only_response(full_content) and iteration < max_iterations:
                            if not plan_emitted and full_content.strip():
                                yield {
                                    "type": "plan_ready",
                                    "steps": _extract_plan_steps(full_content.strip()),
                                    "raw_text": full_content.strip(),
                                }
                                plan_emitted = True
                            chat_messages.append(AIMessage(content=full_content))
                            chat_messages.append(HumanMessage(
                                content=(
                                    "Continue by executing the plan now using the available tools. "
                                    "Do not restate the plan unless needed."
                                )
                            ))
                            continue

                        ai_msg = AIMessage(content=full_content)
                        chat_messages.append(ai_msg)
                        final_response = TextProcessor.convert_math_delimiters(full_content)
                        if final_response:
                            yield {"type": "final_start"}
                            yield {"type": "final_chunk", "content": final_response}
                        break

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
                        ai_msg = AIMessage(content=full_content)
                        chat_messages.append(ai_msg)
                        final_response = TextProcessor.convert_math_delimiters(full_content)
                        if final_response:
                            yield {"type": "final_start"}
                            yield {"type": "final_chunk", "content": final_response}
                        break

                    ai_msg = AIMessage(
                        content=full_content,
                        tool_calls=parsed_tool_calls
                    )
                    chat_messages.append(ai_msg)

                    tool_specs = [
                        ToolCallSpec(
                            id=tc["id"],
                            name=tc["name"],
                            args=tc["args"],
                            index=idx
                        )
                        for idx, tc in enumerate(parsed_tool_calls)
                    ]

                    tc_info_map: Dict[str, Dict[str, Any]] = {
                        tc["id"]: tc for tc in parsed_tool_calls
                    }

                    for spec in tool_specs:
                        if run_context:
                            run_context.raise_if_cancelled()
                        if not round_started:
                            yield {"type": "round_start", "round": iteration}
                            round_started = True
                        yield {
                            "type": "tool_start",
                            "round": iteration,
                            "tool_name": spec.name,
                            "tool_input": spec.args,
                            "tool_call_id": spec.id,
                        }

                    workspace_before = set(_list_workspace_files(workspace_path))

                    results: List[ToolResult] = await execute_tools_parallel(
                        tool_map=tool_map,
                        tool_calls=tool_specs,
                        max_concurrency=settings.max_tool_concurrency,
                        timeout=60.0,
                        run_context=run_context,
                    )

                    for result in results:
                        if run_context:
                            run_context.raise_if_cancelled()
                        tc_info = tc_info_map.get(result.tool_call_id, {})
                        tool_name = tc_info.get("name", "unknown")

                        display_result = result.content
                        if len(display_result) > 2000:
                            display_result = display_result[:2000] + "\n[... truncated]"

                        yield {
                            "type": "tool_result",
                            "round": iteration,
                            "tool_name": tool_name,
                            "output": display_result,
                            "success": result.success,
                            "tool_call_id": result.tool_call_id,
                        }

                        tool_message = ToolMessage(
                            content=result.content,
                            tool_call_id=result.tool_call_id
                        )
                        chat_messages.append(tool_message)

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

                    if round_started:
                        yield {"type": "round_complete", "round": iteration}

                else:
                    final_response = TextProcessor.convert_math_delimiters(
                        full_content or "Reached maximum iteration limit."
                    )
                    if final_response:
                        yield {"type": "final_start"}
                        yield {"type": "final_chunk", "content": final_response}
                    yield {
                        "type": "error",
                        "error": f"Reached maximum of {max_iterations} iterations"
                    }

                final_response = TextProcessor.convert_math_delimiters(final_response)
                metrics_dict = metrics.finish(model_id=self.model_id).to_dict() if metrics else None

                if final_response:
                    await self.storage.add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=final_response,
                        model=self.model_id,
                        metadata={"metrics": metrics_dict} if metrics_dict else {}
                    )
                    await record_used_mode(self.storage, conversation_id, "coworking")
                    assistant_saved = True

                final_file_state = await recompute_coworking_session_deltas(
                    storage=self.storage,
                    conversation_id=conversation_id,
                    workspace_path=workspace_path,
                    baseline_files=session_state["baseline_files"],
                )
                file_state_recomputed = True

                final_generated_files = []
                for file_path in final_file_state["generated_files"]:
                    try:
                        file_size = os.path.getsize(os.path.join(workspace_path, file_path))
                    except Exception:
                        file_size = 0
                    final_generated_files.append({"path": file_path, "size": file_size})

                if citations:
                    yield {"type": "citations", "citations": citations}

                yield {
                    "type": "done",
                    "final_answer": final_response,
                    "generated_files": final_generated_files,
                    "deleted_files": final_file_state["deleted_files"],
                    "metrics": metrics_dict,
                }
        except asyncio.CancelledError:
            raise
        except RunCancelledError:
            raise
        except Exception as e:
            logger.error(f"Coworking agent error: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }
        finally:
            if final_response and not assistant_saved:
                await self.storage.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=TextProcessor.convert_math_delimiters(final_response),
                    model=self.model_id
                )
                await record_used_mode(self.storage, conversation_id, "coworking")
            if not file_state_recomputed:
                await recompute_coworking_session_deltas(
                    storage=self.storage,
                    conversation_id=conversation_id,
                    workspace_path=workspace_path,
                    baseline_files=session_state["baseline_files"],
                )

    async def invoke(
        self,
        question: str,
        conversation_id: str,
        workspace_path: str,
        max_iterations: Optional[int] = None,
        web_search: bool = False,
        run_context: Optional[RunContext] = None,
    ) -> dict:
        """
        Run the coworking agent and return the final result.

        Args:
            question: User's message
            conversation_id: Conversation ID
            workspace_path: Workspace directory path
            max_iterations: Maximum iterations. Defaults to
                settings.coworking_max_tool_iterations.
            web_search: Enable web search tools

        Returns:
            Dict with final_answer, generated_files, and deleted_files
        """
        result = {"final_answer": "", "generated_files": [], "deleted_files": []}
        async for event in self.stream(
            question,
            conversation_id,
            workspace_path,
            max_iterations,
            web_search,
            run_context=run_context,
        ):
            if event["type"] == "done":
                result["final_answer"] = event.get("final_answer", "")
                result["generated_files"] = event.get("generated_files", [])
                result["deleted_files"] = event.get("deleted_files", [])
            elif event["type"] == "error":
                result["final_answer"] = f"Error: {event.get('error', 'Unknown error')}"
        return result
