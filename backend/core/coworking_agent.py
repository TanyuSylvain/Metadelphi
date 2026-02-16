"""
Coworking Agent Implementation

LangGraph-based agent with tool calling for workspace file operations,
code execution, and document generation. Uses bind_tools for native
tool calling with SSE streaming for fine-grained progress updates.
"""

import os
import json
import logging
from typing import Optional, AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from backend.providers import ProviderFactory
from backend.storage import ConversationStorage, MemoryStorage
from backend.utils import TextProcessor
from backend.tools.workspace_tools import create_workspace_tools
from backend.tools.web_search import get_web_search_tools
from backend.core.coworking_prompts import COWORKING_SYSTEM_PROMPT, COWORKING_PLANNING_PROMPT

logger = logging.getLogger(__name__)


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
                        file_created, response_chunk, done, error
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

        # Load or initialize file tracking from conversation metadata
        conv_metadata = (conversation or {}).get("metadata", {})
        initial_workspace_files = conv_metadata.get("initial_workspace_files", None)
        conversation_generated_files = conv_metadata.get("conversation_generated_files", [])

        if initial_workspace_files is None:
            # New conversation or first run — snapshot current workspace files
            initial_workspace_files = self._list_all_files(workspace_path)
            await self.storage.update_conversation_metadata(conversation_id, {
                "initial_workspace_files": initial_workspace_files,
                "conversation_generated_files": []
            })

        # known_files = initial files + files generated in previous messages
        known_files = set(initial_workspace_files + conversation_generated_files)

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

        # Build message list: system + history + current question
        chat_messages = [system_message]
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
        generated_files = list(conversation_generated_files)
        final_response = ""

        # Emit previous_files event so frontend can restore the file list
        if conversation_generated_files:
            previous_files_data = []
            for f in conversation_generated_files:
                try:
                    fsize = os.path.getsize(os.path.join(workspace_path, f))
                except Exception:
                    fsize = 0
                previous_files_data.append({"path": f, "size": fsize})
            yield {"type": "previous_files", "files": previous_files_data}

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

                # Execute each tool call
                for tc in parsed_tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["args"]
                    tool_call_id = tc["id"]

                    yield {
                        "type": "tool_start",
                        "tool_name": tool_name,
                        "tool_input": tool_args
                    }

                    # Execute the tool
                    try:
                        tool_func = tool_map.get(tool_name)
                        if tool_func:
                            result = await tool_func.ainvoke(tool_args)
                        else:
                            result = f"Error: Unknown tool '{tool_name}'"
                    except Exception as e:
                        result = f"Error executing {tool_name}: {str(e)}"

                    # Truncate very long results for display
                    display_result = str(result)
                    if len(display_result) > 2000:
                        display_result = display_result[:2000] + "\n[... truncated]"

                    yield {
                        "type": "tool_result",
                        "tool_name": tool_name,
                        "output": display_result,
                        "success": not str(result).startswith("Error")
                    }

                    # Check for file creation events
                    if tool_name == "write_file" and not str(result).startswith("Error"):
                        file_path = tool_args.get("file_path", "")
                        try:
                            full_path = os.path.join(workspace_path, file_path)
                            file_size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
                        except Exception:
                            file_size = 0
                        if file_path not in known_files:
                            generated_files.append(file_path)
                            known_files.add(file_path)
                        yield {
                            "type": "file_created",
                            "file_path": file_path,
                            "file_size": file_size
                        }

                    # Check python_execute/bash_execute for file creation hints
                    if tool_name in ("python_execute", "bash_execute") and not str(result).startswith("Error"):
                        # Scan workspace for new files after execution
                        new_files = self._scan_for_new_files(workspace_path, known_files)
                        for nf in new_files:
                            generated_files.append(nf)
                            known_files.add(nf)
                            try:
                                file_size = os.path.getsize(os.path.join(workspace_path, nf))
                            except Exception:
                                file_size = 0
                            yield {
                                "type": "file_created",
                                "file_path": nf,
                                "file_size": file_size
                            }

                    # Add tool result to message history
                    tool_message = ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call_id
                    )
                    chat_messages.append(tool_message)

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

            # Persist generated files to conversation metadata
            await self.storage.update_conversation_metadata(conversation_id, {
                "conversation_generated_files": generated_files
            })

            # Only emit newly generated files (exclude those from previous messages)
            new_generated_files = [f for f in generated_files if f not in conversation_generated_files]

            yield {
                "type": "done",
                "final_answer": final_response,
                "generated_files": new_generated_files
            }

        except Exception as e:
            logger.error(f"Coworking agent error: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }

    def _scan_for_new_files(self, workspace_path: str, known_files: set) -> list:
        """Scan workspace for files not in known_files set."""
        new_files = []
        try:
            for root, dirs, files in os.walk(workspace_path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for f in files:
                    rel_path = os.path.relpath(os.path.join(root, f), workspace_path)
                    if rel_path not in known_files and not f.startswith('.'):
                        new_files.append(rel_path)
        except Exception:
            pass
        return new_files

    def _list_all_files(self, workspace_path: str) -> list:
        """List all non-hidden files in workspace as relative paths."""
        all_files = []
        try:
            for root, dirs, files in os.walk(workspace_path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for f in files:
                    if not f.startswith('.'):
                        rel_path = os.path.relpath(os.path.join(root, f), workspace_path)
                        all_files.append(rel_path)
        except Exception:
            pass
        return all_files

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
            Dict with final_answer and generated_files
        """
        result = {"final_answer": "", "generated_files": []}
        async for event in self.stream(question, conversation_id, workspace_path, max_iterations, web_search):
            if event["type"] == "done":
                result["final_answer"] = event.get("final_answer", "")
                result["generated_files"] = event.get("generated_files", [])
            elif event["type"] == "error":
                result["final_answer"] = f"Error: {event.get('error', 'Unknown error')}"
        return result
