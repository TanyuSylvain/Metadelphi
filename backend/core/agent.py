"""
Core LangGraph agent implementation with provider and storage abstractions.
"""

import asyncio
import json
import logging
from typing import TypedDict, Annotated, Optional, List
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import BaseTool

from backend.config import settings
from backend.providers import ProviderFactory
from backend.storage import ConversationStorage, MemoryStorage
from backend.tools.utils import format_tool_result, format_tool_start
from backend.utils import TextProcessor
from backend.utils.citation import (
    CITATION_SYSTEM_INSTRUCTION,
    extract_citations_from_result,
    format_citations_metadata,
    strip_citations_metadata,
)
from backend.utils.parallel_tools import (
    ToolCallSpec,
    execute_tools_parallel,
)
from backend.core.run_manager import RunCancelledError, RunContext, use_run_context

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State of the agent."""
    messages: Annotated[list, add_messages]


class LangGraphAgent:
    """LangGraph agent with multi-provider support and pluggable storage."""

    def __init__(
        self,
        model_id: str,
        provider_name: Optional[str] = None,
        storage: Optional[ConversationStorage] = None,
        temperature: float = None,
        thinking: bool = False,
        tools: Optional[List[BaseTool]] = None
    ):
        """
        Initialize the agent with specified model and storage.

        Args:
            model_id: Model ID to use (e.g., 'mistral-large-latest', 'qwen-max')
            provider_name: Optional provider name (auto-detected if not provided)
            storage: Storage backend (defaults to MemoryStorage)
            temperature: Sampling temperature (defaults to config setting)
            thinking: Enable thinking mode for models that support it
            tools: Optional list of tools to bind (enables ReAct loop)
        """
        self.model_id = model_id
        self.provider_name = provider_name
        self.thinking = thinking
        self.tools = tools or []

        # Initialize LLM using factory
        self.llm = ProviderFactory.create_llm(
            model_id=model_id,
            provider_name=provider_name,
            temperature=temperature,
            thinking=thinking
        )

        # Bind tools if provided
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            self.tool_map = {t.name: t for t in self.tools}
        else:
            self.llm_with_tools = None
            self.tool_map = {}

        # Initialize storage
        self.storage = storage or MemoryStorage()

        # Build the LangGraph workflow (only used for non-tool path)
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)

        # Add the agent node
        workflow.add_node("agent", self._agent_node)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add edge from agent to END
        workflow.add_edge("agent", END)

        return workflow.compile()

    def _agent_node(self, state: AgentState):
        """Process the user question and generate response."""
        messages = state["messages"]
        response = self.llm.invoke(messages)
        return {"messages": [response]}

    async def stream(
        self,
        question: str,
        conversation_id: str = None,
        run_context: Optional[RunContext] = None,
    ):
        """
        Stream the response to a user question.

        When tools are bound, runs a ReAct loop:
        stream LLM → check for tool calls → execute tools → loop.
        When no tools, streams directly from LLM.

        Args:
            question: The user's question
            conversation_id: Optional conversation ID for multi-turn conversations

        Yields:
            str: Chunks of the response text
        """
        # Get conversation history
        history = []
        is_new_conversation = False
        if conversation_id:
            conversation = await self.storage.get_conversation(conversation_id)
            is_new_conversation = conversation is None
            messages = await self.storage.get_messages(conversation_id)
            history = [{"role": msg["role"], "content": msg["content"]} for msg in messages]

        # Add current question to storage
        if conversation_id:
            await self.storage.add_message(
                conversation_id=conversation_id,
                role="user",
                content=question,
                model=self.model_id
            )
            # Set title from first message if this is a new conversation
            if is_new_conversation:
                # Truncate title to 50 characters max
                title = question[:50] + "..." if len(question) > 50 else question
                await self.storage.update_conversation_title(conversation_id, title)

        # Build messages with history
        messages = history.copy()
        messages.append({"role": "user", "content": question})

        # Choose path: with tools (ReAct loop) or without (simple streaming)
        if self.llm_with_tools and self.tools:
            full_response = ""
            try:
                async with use_run_context(run_context):
                    async for chunk in self._stream_with_tools(messages, run_context=run_context):
                        if run_context:
                            run_context.raise_if_cancelled()
                        full_response += chunk
                        yield chunk
            finally:
                if conversation_id and full_response:
                    clean_response = strip_citations_metadata(full_response)
                    converted_response = TextProcessor.convert_math_delimiters(clean_response)
                    await self.storage.add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=converted_response,
                        model=self.model_id
                    )
        else:
            # Original simple streaming path
            full_response = ""
            try:
                async with use_run_context(run_context):
                    async for chunk in self.llm.astream(messages):
                        if run_context:
                            run_context.raise_if_cancelled()
                        if hasattr(chunk, 'content'):
                            content = chunk.content
                            if content:
                                text_content = TextProcessor.extract_text_content(content)
                                if text_content:
                                    full_response += text_content
                                    yield text_content
            finally:
                if conversation_id and full_response:
                    converted_response = TextProcessor.convert_math_delimiters(full_response)
                    await self.storage.add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=converted_response,
                        model=self.model_id
                    )

    async def _stream_with_tools(
        self,
        messages: list,
        max_iterations: int = 10,
        run_context: Optional[RunContext] = None,
    ):
        """
        ReAct loop: stream LLM with tools, execute tool calls, repeat.

        Args:
            messages: Chat message list (mutated in-place)
            max_iterations: Safety limit for tool call rounds

        Yields:
            str: Text chunks from the LLM
        """
        citations = []

        # Prepend citation instruction so the LLM knows to use [N] markers
        messages.insert(0, SystemMessage(content=CITATION_SYSTEM_INSTRUCTION))

        for iteration in range(max_iterations):
            if run_context:
                run_context.raise_if_cancelled()
            full_content = ""
            tool_calls = []

            async for chunk in self.llm_with_tools.astream(messages):
                if run_context:
                    run_context.raise_if_cancelled()
                # Accumulate text content
                if hasattr(chunk, 'content') and chunk.content:
                    text = TextProcessor.extract_text_content(chunk.content)
                    if text:
                        full_content += text
                        yield text

                # Accumulate tool call chunks
                if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
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
                # No tool calls — final response, done
                messages.append(AIMessage(content=full_content))
                if citations:
                    if run_context:
                        run_context.raise_if_cancelled()
                    yield format_citations_metadata(citations)
                break

            # Parse tool calls
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
                messages.append(AIMessage(content=full_content))
                break

            # Append AI message with tool calls
            ai_msg = AIMessage(content=full_content, tool_calls=parsed_tool_calls)
            messages.append(ai_msg)

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
            tool_call_map = {tc["id"]: tc for tc in parsed_tool_calls}

            # Yield status markers for all tools upfront
            for spec in tool_specs:
                if run_context:
                    run_context.raise_if_cancelled()
                yield f"\n\n{format_tool_start(spec.name, spec.args)}\n\n"

            # Execute tools in parallel
            results = await execute_tools_parallel(
                tool_map=self.tool_map,
                tool_calls=tool_specs,
                max_concurrency=settings.max_tool_concurrency,
                timeout=60.0,
                run_context=run_context,
            )

            # Add tool messages to conversation and extract citations
            for result in results:
                if run_context:
                    run_context.raise_if_cancelled()
                original_tool = tool_call_map.get(result.tool_call_id)
                if original_tool:
                    yield f"\n\n{format_tool_result(original_tool['name'], original_tool['args'], result.content, result.success)}\n\n"

                tool_message = ToolMessage(
                    content=result.content,
                    tool_call_id=result.tool_call_id
                )
                messages.append(tool_message)

                # Extract citations from search tool results
                if "search" in result.content.lower() or any(
                    "search" in tc["name"].lower() for tc in parsed_tool_calls
                    if tc["id"] == result.tool_call_id
                ):
                    extract_citations_from_result(result.content, citations)

            # Continue loop — LLM will process tool results

    async def invoke(
        self,
        question: str,
        conversation_id: str = None,
        run_context: Optional[RunContext] = None,
    ) -> str:
        """
        Get the complete response to a user question.

        Args:
            question: The user's question
            conversation_id: Optional conversation ID for multi-turn conversations

        Returns:
            str: The complete response
        """
        # Collect from stream() to support tool-augmented path
        full_response = ""
        async for chunk in self.stream(question, conversation_id, run_context=run_context):
            full_response += chunk
        return full_response

    async def get_conversation_history(self, conversation_id: str):
        """
        Get the conversation history.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of messages
        """
        return await self.storage.get_messages(conversation_id)

    async def clear_conversation(self, conversation_id: str) -> bool:
        """
        Clear a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if deleted, False if not found
        """
        return await self.storage.delete_conversation(conversation_id)
