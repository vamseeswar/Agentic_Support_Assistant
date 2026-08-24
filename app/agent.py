import json
import uuid
import logging
from typing import Optional, Dict, Any
from app.llm.factory import create_llm_client
from app.llm.base import BaseLLMClient, LLMResponse
from app.tools.registry import execute_tool, get_tool_declarations
from app.guardrails.safety import safety_guard
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.state import StateStore, ConversationState
from app.models import ChatRequest, ChatResponse, ToolCallSummary

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6  # Prevent infinite loops


class TrendlyAgent:
    """
    Core agentic loop: receives user message, runs safety guardrails,
    invokes the LLM with tool declarations, executes tool calls,
    feeds results back to the LLM, and returns final response.
    """

    def __init__(self):
        self.llm: BaseLLMClient = create_llm_client()
        self.state_store = StateStore()
        self.tool_declarations = get_tool_declarations()
        logger.info("TrendlyAgent initialized.")

    def handle_message(self, request: ChatRequest) -> ChatResponse:
        """Process a single user message through the full agent pipeline."""
        # 1. Get or create conversation
        conv_id = request.conversation_id or str(uuid.uuid4())
        state = self.state_store.get_or_create(conv_id)

        # Bind customer ID if provided
        if request.customer_id and not state.customer_id:
            state.customer_id = request.customer_id

        # 2. Input safety guardrails
        is_safe, refusal_reason, refusal_message = safety_guard.check_input_safety(
            request.message, state.customer_id
        )
        if not is_safe:
            state.add_message("user", request.message)
            state.add_message("assistant", refusal_message)
            return ChatResponse(
                conversation_id=conv_id,
                message=refusal_message,
                status="refused",
                tool_calls=[]
            )

        # 3. Add user message to conversation history
        state.add_message("user", request.message)

        # 4. Run agent loop (LLM → tool calls → LLM → ... → final text)
        all_tool_summaries = []
        detected_order_id = state.current_order_id
        detected_escalation_id = None

        for round_num in range(MAX_TOOL_ROUNDS):
            messages = state.get_history_for_llm()

            response = self.llm.chat(
                messages=messages,
                tools=self.tool_declarations,
                system_instruction=SYSTEM_PROMPT
            )

            if response.finish_reason == "error":
                state.add_message("assistant", response.text or "I encountered an error. Please try again.")
                return ChatResponse(
                    conversation_id=conv_id,
                    message=response.text or "I encountered an error. Please try again.",
                    status="resolved",
                    tool_calls=all_tool_summaries
                )

            if not response.has_tool_calls:
                # Final text response
                final_text = response.text or "I'm here to help! Could you please clarify your question?"
                state.add_message("assistant", final_text)
                status = "resolved"
                if detected_escalation_id:
                    status = "escalated"
                return ChatResponse(
                    conversation_id=conv_id,
                    message=final_text,
                    status=status,
                    order_id=detected_order_id,
                    escalation_id=detected_escalation_id,
                    tool_calls=all_tool_summaries
                )

            # Process tool calls
            # Add assistant message with tool calls marker
            assistant_msg = {
                "role": "assistant",
                "content": response.text or "",
                "tool_calls_raw": getattr(response, 'tool_calls_raw', None)
            }
            state.messages.append(assistant_msg)

            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_call_id = tc.get("id", f"call_{round_num}")

                logger.info(f"Executing tool: {tool_name}({json.dumps(tool_args)[:200]})")

                # Execute the deterministic tool
                tool_result = execute_tool(tool_name, tool_args)

                # Track order ID and escalation ID
                if tool_name == "get_order" and tool_result.get("success"):
                    detected_order_id = tool_result.get("order_id")
                    state.current_order_id = detected_order_id
                    # Bind customer ID from order
                    if tool_result.get("customer_id") and not state.customer_id:
                        state.customer_id = tool_result["customer_id"]

                if tool_name == "escalate_to_human" and tool_result.get("success"):
                    detected_escalation_id = tool_result.get("escalation_id")

                # Create tool call summary for response
                result_summary = ""
                if isinstance(tool_result, dict):
                    if tool_result.get("explanation"):
                        result_summary = tool_result["explanation"][:200]
                    elif tool_result.get("message"):
                        result_summary = tool_result["message"][:200]
                    elif tool_result.get("error"):
                        result_summary = f"Error: {tool_result['error'][:200]}"
                    else:
                        result_summary = json.dumps(tool_result, default=str)[:200]

                all_tool_summaries.append(ToolCallSummary(
                    tool_name=tool_name,
                    arguments=tool_args,
                    result_summary=result_summary,
                    success=tool_result.get("success", True) if isinstance(tool_result, dict) else True
                ))

                # Add tool result to conversation
                tool_content = json.dumps(tool_result, default=str)
                state.messages.append({
                    "role": "tool",
                    "content": tool_content,
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id
                })

        # If we exhausted all rounds, return what we have
        final_msg = "I've gathered the information. Let me summarize what I found for you."
        state.add_message("assistant", final_msg)
        return ChatResponse(
            conversation_id=conv_id,
            message=final_msg,
            status="resolved",
            order_id=detected_order_id,
            escalation_id=detected_escalation_id,
            tool_calls=all_tool_summaries
        )

    def reset_conversation(self, conversation_id: str) -> bool:
        if conversation_id in self.state_store._store:
            del self.state_store._store[conversation_id]
            return True
        return False


# Singleton agent instance
agent = TrendlyAgent()
