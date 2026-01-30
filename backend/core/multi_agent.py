"""
Multi-Agent Debate Workflow Implementation

This module implements a three-role multi-agent collaboration system:
- Moderator: Assesses complexity, guides debate, synthesizes final answer
- Expert: Generates professional answers
- Critic: Reviews and provides feedback

Uses LangGraph for workflow orchestration with sliding window memory management.
"""

import json
import re
import logging
from datetime import datetime
from typing import Optional, AsyncGenerator, Literal

from langgraph.graph import StateGraph, END

from backend.providers import ProviderFactory
from backend.storage import ConversationStorage, MemoryStorage
from backend.utils import TextProcessor
from backend.core.multi_agent_state import MultiAgentState, create_initial_state
from backend.core.prompts import (
    MODERATOR_INIT_PROMPT,
    MODERATOR_SYNTHESIZE_PROMPT,
    MODERATOR_FINAL_SYNTHESIS_PROMPT,
    EXPERT_GENERATE_PROMPT,
    EXPERT_IMPROVEMENT_SECTION,
    EXPERT_FIRST_ITERATION_GUIDANCE,
    EXPERT_SUBSEQUENT_ITERATION_GUIDANCE,
    CRITIC_REVIEW_PROMPT,
)


logger = logging.getLogger(__name__)


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try to find JSON in code blocks first
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # Try to find raw JSON
        json_str = text.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON: {e}")
        # Return a default error structure
        return {"error": "Failed to parse response", "raw": text}


class MultiAgentDebateWorkflow:
    """
    Multi-agent debate workflow with Moderator-Expert-Critic roles.

    Each role can use a different LLM model for specialized behavior.
    Uses sliding window approach for memory management.
    """

    def __init__(
        self,
        moderator_model: str,
        expert_model: str,
        critic_model: str,
        storage: Optional[ConversationStorage] = None,
        max_iterations: int = 3,
        score_threshold: float = 80.0,
        temperature: float = None,
        thinking_moderator: bool = False,
        thinking_expert: bool = False,
        thinking_critic: bool = False
    ):
        """
        Initialize the multi-agent debate workflow.

        Args:
            moderator_model: Model ID for the moderator role
            expert_model: Model ID for the expert role
            critic_model: Model ID for the critic role
            storage: Storage backend (defaults to MemoryStorage)
            max_iterations: Maximum debate iterations (1-10)
            score_threshold: Score threshold for passing (0-100)
            temperature: LLM temperature (defaults to config)
            thinking_moderator: Enable thinking for moderator
            thinking_expert: Enable thinking for expert
            thinking_critic: Enable thinking for critic
        """
        self.moderator_model = moderator_model
        self.expert_model = expert_model
        self.critic_model = critic_model
        self.max_iterations = max_iterations
        self.score_threshold = score_threshold

        # Initialize LLMs for each role with thinking parameters
        self.moderator_llm = ProviderFactory.create_llm(
            model_id=moderator_model,
            temperature=temperature,
            thinking=thinking_moderator
        )
        self.expert_llm = ProviderFactory.create_llm(
            model_id=expert_model,
            temperature=temperature,
            thinking=thinking_expert
        )
        self.critic_llm = ProviderFactory.create_llm(
            model_id=critic_model,
            temperature=temperature,
            thinking=thinking_critic
        )

        # Initialize storage
        self.storage = storage or MemoryStorage()

        # Build the LangGraph workflow
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow with conditional branching."""
        workflow = StateGraph(MultiAgentState)

        # Add nodes
        workflow.add_node("moderator_init", self._moderator_init_node)
        workflow.add_node("expert_generate", self._expert_generate_node)
        workflow.add_node("critic_review", self._critic_review_node)
        workflow.add_node("moderator_synthesize", self._moderator_synthesize_node)

        # Set entry point
        workflow.set_entry_point("moderator_init")

        # Add conditional edges from moderator_init
        workflow.add_conditional_edges(
            "moderator_init",
            self._route_after_init,
            {
                "direct": END,
                "expert": "expert_generate"
            }
        )

        # Expert -> Critic
        workflow.add_edge("expert_generate", "critic_review")

        # Critic -> Moderator Synthesize
        workflow.add_edge("critic_review", "moderator_synthesize")

        # Conditional edges from moderator_synthesize
        workflow.add_conditional_edges(
            "moderator_synthesize",
            self._route_after_synthesize,
            {
                "continue": "expert_generate",
                "end": END
            }
        )

        return workflow.compile()

    def _route_after_init(self, state: MultiAgentState) -> Literal["direct", "expert"]:
        """Route based on moderator's complexity assessment."""
        if state["status"] == "direct_answer":
            return "direct"
        return "expert"

    def _route_after_synthesize(self, state: MultiAgentState) -> Literal["continue", "end"]:
        """Route based on moderator's synthesis decision."""
        if state["status"] == "completed":
            return "end"
        return "continue"

    def _moderator_init_node(self, state: MultiAgentState) -> dict:
        """
        Moderator analyzes question and decides on approach.

        Returns:
            Updated state with complexity assessment and routing decision
        """
        # Format conversation context if present
        conversation_context = ""
        if state.get("conversation_context"):
            conversation_context = f"## 对话上下文\n\n{state['conversation_context']}\n"

        prompt = MODERATOR_INIT_PROMPT.format(
            question=state["original_question"],
            conversation_context=conversation_context
        )

        response = self.moderator_llm.invoke([{"role": "user", "content": prompt}])
        text_content = TextProcessor.extract_text_content(response.content)
        result = extract_json_from_response(text_content)

        if "error" in result:
            # Fallback: treat as complex question
            return {
                "complexity": "complex",
                "current_task": f"请全面分析和回答以下问题: {state['original_question']}",
                "iteration": 1
            }

        complexity = result.get("complexity", "complex")
        decision = result.get("decision", "delegate_expert")

        if decision == "direct_answer" and result.get("direct_answer"):
            # Simple question - provide direct answer
            return {
                "complexity": complexity,
                "final_answer": result["direct_answer"],
                "status": "direct_answer",
                "termination_reason": "simple_question",
                "moderator_init_analysis": {
                    "intent": result.get("intent"),
                    "key_constraints": result.get("key_constraints"),
                    "complexity": complexity,
                    "complexity_reason": result.get("complexity_reason"),
                    "decision": decision
                }
            }
        else:
            # Complex question - delegate to expert
            return {
                "complexity": complexity,
                "current_task": result.get("task_for_expert", f"请全面分析和回答: {state['original_question']}"),
                "iteration": 1,
                "moderator_init_analysis": {
                    "intent": result.get("intent"),
                    "key_constraints": result.get("key_constraints"),
                    "complexity": complexity,
                    "complexity_reason": result.get("complexity_reason"),
                    "decision": decision
                }
            }

    def _expert_generate_node(self, state: MultiAgentState) -> dict:
        """
        Expert generates or refines answer based on moderator's guidance.

        Returns:
            Updated state with expert's answer
        """
        is_first = state["iteration"] == 1

        # Build improvement section for subsequent iterations
        if is_first:
            improvement_section = ""
            iteration_guidance = EXPERT_FIRST_ITERATION_GUIDANCE
        else:
            # Summarize previous answer for context
            prev_answer = state.get("current_answer", {})
            prev_answer_summary = f"""
核心观点: {', '.join(prev_answer.get('core_points', []))}
结论: {prev_answer.get('conclusion', 'N/A')}
置信度: {prev_answer.get('confidence', 'N/A')}
"""
            # Get critic feedback
            prev_review = state.get("current_review", {})
            critic_feedback = f"""
评分: {prev_review.get('overall_score', 'N/A')}
问题: {json.dumps(prev_review.get('issues', []), ensure_ascii=False)}
建议: {', '.join(prev_review.get('suggestions', []))}
"""
            improvement_section = EXPERT_IMPROVEMENT_SECTION.format(
                previous_answer_summary=prev_answer_summary,
                critic_feedback=critic_feedback,
                moderator_guidance=state.get("improvement_guidance", "")
            )
            iteration_guidance = EXPERT_SUBSEQUENT_ITERATION_GUIDANCE

        # Format conversation context if present
        conversation_context = ""
        if state.get("conversation_context"):
            conversation_context = f"## 对话上下文\n\n{state['conversation_context']}\n"

        prompt = EXPERT_GENERATE_PROMPT.format(
            original_question=state["original_question"],
            current_task=state["current_task"],
            iteration=state["iteration"],
            is_first_iteration="是" if is_first else "否",
            improvement_section=improvement_section,
            iteration_guidance=iteration_guidance,
            conversation_context=conversation_context
        )

        response = self.expert_llm.invoke([{"role": "user", "content": prompt}])
        text_content = TextProcessor.extract_text_content(response.content)
        result = extract_json_from_response(text_content)

        if "error" in result:
            # Fallback: create basic answer structure
            result = {
                "version": state["iteration"],
                "understanding": "问题理解",
                "core_points": ["核心观点"],
                "details": text_content,
                "conclusion": "结论",
                "confidence": 0.5,
                "limitations": [],
                "modification_log": []
            }

        return {"current_answer": result}

    def _critic_review_node(self, state: MultiAgentState) -> dict:
        """
        Critic reviews the expert's answer.

        Returns:
            Updated state with critic's review
        """
        prompt = CRITIC_REVIEW_PROMPT.format(
            original_question=state["original_question"],
            expert_answer=json.dumps(state["current_answer"], ensure_ascii=False, indent=2),
            score_threshold=self.score_threshold
        )

        response = self.critic_llm.invoke([{"role": "user", "content": prompt}])
        text_content = TextProcessor.extract_text_content(response.content)
        result = extract_json_from_response(text_content)

        if "error" in result:
            # Fallback: create basic review structure
            result = {
                "review_version": state["iteration"],
                "overall_score": 70,
                "passed": False,
                "issues": [],
                "strengths": [],
                "suggestions": ["请继续完善回答"],
                "confidence": 0.5
            }

        return {"current_review": result}

    def _moderator_synthesize_node(self, state: MultiAgentState) -> dict:
        """
        Moderator synthesizes results and decides whether to continue.

        Returns:
            Updated state with synthesis decision
        """
        # Prepare previous summary
        previous_summary = state.get("previous_summary", "这是第一轮迭代，无历史记录。")

        # Pre-check termination conditions BEFORE LLM call
        review = state.get("current_review", {})
        score = review.get("overall_score", 0)
        passed = review.get("passed", False)
        iteration = state["iteration"]

        # Determine if termination will be forced by rules
        forced_termination = False
        forced_reason = None
        termination_reason_display = None

        if passed or score >= self.score_threshold:
            forced_termination = True
            forced_reason = "score_threshold" if score >= self.score_threshold else "explicit_pass"
            termination_reason_display = f"评审通过，评分 {score} 达到阈值 {self.score_threshold}"
        elif iteration >= self.max_iterations:
            forced_termination = True
            forced_reason = "max_iterations"
            termination_reason_display = f"已达到最大迭代次数 ({iteration}/{self.max_iterations})"

        # Choose prompt based on whether termination is forced
        if forced_termination:
            # Use dedicated final synthesis prompt to ensure proper final_answer generation
            prompt = MODERATOR_FINAL_SYNTHESIS_PROMPT.format(
                original_question=state["original_question"],
                iteration=iteration,
                max_iterations=self.max_iterations,
                previous_summary=previous_summary,
                current_answer=json.dumps(state["current_answer"], ensure_ascii=False, indent=2),
                current_review=json.dumps(state["current_review"], ensure_ascii=False, indent=2),
                termination_reason=forced_reason,
                termination_reason_display=termination_reason_display
            )
        else:
            # Use standard prompt that allows LLM to decide
            prompt = MODERATOR_SYNTHESIZE_PROMPT.format(
                original_question=state["original_question"],
                iteration=iteration,
                max_iterations=self.max_iterations,
                previous_summary=previous_summary,
                current_answer=json.dumps(state["current_answer"], ensure_ascii=False, indent=2),
                current_review=json.dumps(state["current_review"], ensure_ascii=False, indent=2),
                score_threshold=self.score_threshold
            )

        response = self.moderator_llm.invoke([{"role": "user", "content": prompt}])
        text_content = TextProcessor.extract_text_content(response.content)
        result = extract_json_from_response(text_content)

        # Determine final termination status
        should_end = forced_termination or result.get("decision") == "end"
        termination_reason = forced_reason or result.get("termination_reason", "moderator_decision")

        if should_end:
            # Generate final answer
            final_answer = result.get("final_answer")
            if not final_answer:
                # Use current answer's conclusion as fallback
                answer = state.get("current_answer", {})
                final_answer = f"""## 回答

{answer.get('details', '')}

## 结论

{answer.get('conclusion', '')}
"""

            return {
                "status": "completed",
                "final_answer": final_answer,
                "termination_reason": termination_reason,
                "previous_summary": state.get("previous_summary", "") + "\n" + result.get("iteration_summary", ""),
                "moderator_synthesize_analysis": {
                    "feedback_validation": result.get("feedback_validation"),
                    "decision": result.get("decision"),
                    "improvement_guidance": result.get("improvement_guidance"),
                    "iteration_summary": result.get("iteration_summary"),
                    "termination_reason": termination_reason
                }
            }
        else:
            # Continue iteration
            # Update summary with current iteration info
            iteration_summary = result.get("iteration_summary", f"第{iteration}轮: 评分{score}, 继续改进。")
            new_summary = state.get("previous_summary", "") + "\n" + iteration_summary

            return {
                "iteration": iteration + 1,
                "improvement_guidance": result.get("improvement_guidance", "请继续改进回答。"),
                "previous_summary": new_summary.strip(),
                "current_task": result.get("improvement_guidance", state["current_task"]),
                "moderator_synthesize_analysis": {
                    "feedback_validation": result.get("feedback_validation"),
                    "decision": result.get("decision"),
                    "improvement_guidance": result.get("improvement_guidance"),
                    "iteration_summary": result.get("iteration_summary"),
                    "termination_reason": None
                }
            }

    async def _load_debate_state(
        self,
        conversation_id: str
    ) -> Optional[dict]:
        """
        Load previous debate state from storage.

        Args:
            conversation_id: Conversation ID

        Returns:
            Debate state dict or None
        """
        conversation = await self.storage.get_conversation(conversation_id)
        if not conversation:
            return None

        metadata = conversation.get("metadata", {})
        return metadata.get("debate_state")

    async def _save_debate_state(
        self,
        conversation_id: str,
        state: dict
    ) -> None:
        """
        Save debate state for next round.

        Args:
            conversation_id: Conversation ID
            state: Current debate state
        """
        debate_state = {
            "previous_summary": state.get("previous_summary", ""),
            "last_iteration": state.get("iteration", 0),
            "conversation_context": await self._build_conversation_context(conversation_id),
            "timestamp": datetime.now().isoformat()
        }

        await self.storage.update_debate_state(conversation_id, debate_state)

    async def _build_conversation_context(
        self,
        conversation_id: str,
        limit: int = 5
    ) -> str:
        """
        Build context summary from recent conversation history.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of message pairs to include

        Returns:
            Formatted context string
        """
        messages = await self.storage.get_messages(conversation_id)

        # Filter to user/assistant messages (exclude debate internals)
        user_assistant_messages = [
            msg for msg in messages
            if msg.get("role") in ("user", "assistant")
            and msg.get("message_type") in (None, "user_query", "final_answer")
        ]

        # Take last N message pairs
        recent_messages = user_assistant_messages[-(limit * 2):]

        if not recent_messages:
            return ""

        # Format as conversation context
        context_lines = []
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Truncate very long messages
            if len(content) > 500:
                content = content[:500] + "..."

            if role == "user":
                context_lines.append(f"User: {content}")
            elif role == "assistant":
                context_lines.append(f"Assistant: {content}")

        return "\n".join(context_lines) if context_lines else ""

    async def stream(
        self,
        question: str,
        conversation_id: str = None
    ) -> AsyncGenerator[dict, None]:
        """
        Stream the multi-agent debate process.

        Args:
            question: The user's question
            conversation_id: Optional conversation ID

        Yields:
            dict: Progress events with type and data
                - type: "phase_start" | "expert_answer" | "critic_review" |
                        "iteration_complete" | "done" | "error"
        """
        # Store user message
        is_new_conversation = False
        if conversation_id:
            conversation = await self.storage.get_conversation(conversation_id)
            is_new_conversation = conversation is None
            await self.storage.add_message(
                conversation_id=conversation_id,
                role="user",
                content=question,
                model=self.moderator_model,
                message_type="user_query"
            )
            if is_new_conversation:
                title = question[:50] + "..." if len(question) > 50 else question
                await self.storage.update_conversation_title(conversation_id, title)
                # Set mode to debate for new conversations in multi-agent workflow
                await self.storage.update_conversation_metadata(conversation_id, {"mode": "debate"})

        # Load previous debate state if exists
        debate_state = None
        if conversation_id and not is_new_conversation:
            debate_state = await self._load_debate_state(conversation_id)

        # Create initial state with context
        initial_state = create_initial_state(
            question=question,
            max_iterations=self.max_iterations,
            previous_summary=debate_state.get("previous_summary", "") if debate_state else "",
            conversation_context=debate_state.get("conversation_context", "") if debate_state else ""
        )

        try:
            # Yield initial phase
            yield {
                "type": "phase_start",
                "phase": "moderator_init",
                "iteration": 0,
                "message": "Moderator analyzing question complexity..."
            }

            # Run the graph step by step
            current_state = initial_state

            # Step 1: Moderator Init
            result = self.graph.nodes["moderator_init"].invoke(current_state)
            current_state = {**current_state, **result}

            # Emit moderator init analysis
            if "moderator_init_analysis" in current_state:
                analysis = current_state["moderator_init_analysis"]
                yield {
                    "type": "moderator_init",
                    "analysis": analysis
                }
                # Store analysis as message
                if conversation_id:
                    content_str = json.dumps(analysis, ensure_ascii=False)
                    print(f"[Debug] Storing moderator_init: content type={type(content_str).__name__}, content_len={len(content_str)}")
                    await self.storage.add_message(
                        conversation_id=conversation_id,
                        role="system",
                        content=content_str,
                        message_type="moderator_init",
                        metadata={"analysis": analysis}
                    )

            # Check if direct answer
            if current_state.get("status") == "direct_answer":
                # Convert math delimiters for streaming response
                converted_answer = TextProcessor.convert_math_delimiters(current_state["final_answer"])
                yield {
                    "type": "done",
                    "final_answer": converted_answer,
                    "was_direct_answer": True,
                    "termination_reason": "simple_question",
                    "total_iterations": 0
                }
                # Store final answer and save debate state
                if conversation_id:
                    await self.storage.add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=converted_answer,
                        model=self.moderator_model,
                        message_type="final_answer"
                    )
                    # Save debate state for next round (even for direct answers)
                    await self._save_debate_state(conversation_id, current_state)
                return

            # Expert-Critic loop
            while current_state.get("status") != "completed":
                iteration = current_state.get("iteration", 1)

                # Expert phase
                yield {
                    "type": "phase_start",
                    "phase": "expert_generate",
                    "iteration": iteration,
                    "message": f"Expert generating answer (iteration {iteration})..."
                }

                result = self.graph.nodes["expert_generate"].invoke(current_state)
                current_state = {**current_state, **result}

                yield {
                    "type": "expert_answer",
                    "iteration": iteration,
                    "answer": current_state["current_answer"]
                }

                # Critic phase
                yield {
                    "type": "phase_start",
                    "phase": "critic_review",
                    "iteration": iteration,
                    "message": f"Critic reviewing answer (iteration {iteration})..."
                }

                result = self.graph.nodes["critic_review"].invoke(current_state)
                current_state = {**current_state, **result}

                yield {
                    "type": "critic_review",
                    "iteration": iteration,
                    "review": current_state["current_review"]
                }

                # Moderator synthesize phase
                yield {
                    "type": "phase_start",
                    "phase": "moderator_synthesize",
                    "iteration": iteration,
                    "message": f"Moderator synthesizing results (iteration {iteration})..."
                }

                result = self.graph.nodes["moderator_synthesize"].invoke(current_state)
                current_state = {**current_state, **result}

                # Emit moderator synthesize analysis
                if "moderator_synthesize_analysis" in current_state:
                    yield {
                        "type": "moderator_synthesize",
                        "iteration": iteration,
                        "analysis": current_state["moderator_synthesize_analysis"]
                    }
                    # Store analysis as message
                    if conversation_id:
                        await self.storage.add_message(
                            conversation_id=conversation_id,
                            role="system",
                            content=json.dumps(current_state["moderator_synthesize_analysis"], ensure_ascii=False),
                            message_type="moderator_synthesize",
                            iteration=iteration,
                            metadata={"analysis": current_state["moderator_synthesize_analysis"]}
                        )

                yield {
                    "type": "iteration_complete",
                    "iteration": iteration,
                    "status": current_state.get("status"),
                    "score": current_state.get("current_review", {}).get("overall_score"),
                    "summary": current_state.get("previous_summary", "")
                }

            # Final result - convert math delimiters for streaming response
            converted_answer = TextProcessor.convert_math_delimiters(current_state["final_answer"])
            yield {
                "type": "done",
                "final_answer": converted_answer,
                "was_direct_answer": False,
                "termination_reason": current_state.get("termination_reason"),
                "total_iterations": current_state.get("iteration", 1)
            }

            # Store final answer and save debate state
            if conversation_id:
                await self.storage.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=converted_answer,
                    model=self.expert_model,
                    message_type="final_answer"
                )
                # Save debate state for next round
                await self._save_debate_state(conversation_id, current_state)

        except Exception as e:
            logger.error(f"Multi-agent workflow error: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }

    async def invoke(
        self,
        question: str,
        conversation_id: str = None
    ) -> dict:
        """
        Run the complete multi-agent debate and return final result.

        Args:
            question: The user's question
            conversation_id: Optional conversation ID

        Returns:
            dict with final_answer, termination_reason, total_iterations
        """
        result = None
        async for event in self.stream(question, conversation_id):
            if event["type"] == "done":
                result = event
            elif event["type"] == "error":
                raise RuntimeError(event["error"])

        return result
