import json
import logging
from typing import List, Dict, Any, Optional
from app.llm.base import BaseLLMClient, LLMResponse

logger = logging.getLogger(__name__)


class FallbackClient(BaseLLMClient):
    """
    Deterministic mock LLM client for offline testing.
    Routes user messages to the correct tool calls based on keyword detection.
    This ensures tests can run without any API key or network connection.
    """

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
    ) -> LLMResponse:
        # Get the last user message
        user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "").lower()
                break

        # Check if this is a follow-up after tool results
        last_msg = messages[-1] if messages else {}
        if last_msg.get("role") == "tool":
            tool_result = last_msg.get("content", "")
            try:
                result_data = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
            except (json.JSONDecodeError, TypeError):
                result_data = {"content": tool_result}

            # Generate a summary response from tool results
            if isinstance(result_data, dict):
                if result_data.get("explanation"):
                    return LLMResponse(text=result_data["explanation"])
                elif result_data.get("content"):
                    return LLMResponse(text=f"Based on our policy: {result_data['content']}")
                elif result_data.get("message"):
                    return LLMResponse(text=result_data["message"])
                elif result_data.get("eligible") is not None:
                    if result_data["eligible"]:
                        return LLMResponse(text=f"Good news! {'; '.join(result_data.get('reasons', ['Item is eligible.']))}")
                    else:
                        return LLMResponse(text=f"I'm sorry, {'; '.join(result_data.get('reasons', ['Item is not eligible.']))}")
            return LLMResponse(text=f"Here's what I found: {json.dumps(result_data, indent=2)[:500]}")

        # Route to tools based on keywords
        if any(kw in user_msg for kw in ["order", "tr-", "status", "tracking", "where is"]):
            # Extract order ID
            import re
            order_match = re.search(r'tr-\d+', user_msg, re.IGNORECASE)
            order_id = order_match.group(0).upper() if order_match else "TR-4521"
            return LLMResponse(tool_calls=[{
                "name": "get_order",
                "arguments": {"order_id": order_id}
            }])

        if any(kw in user_msg for kw in ["return", "refund", "send back", "give back"]):
            order_match = __import__("re").search(r'tr-\d+', user_msg, re.IGNORECASE)
            if order_match:
                return LLMResponse(tool_calls=[{
                    "name": "check_return_eligibility",
                    "arguments": {"order_id": order_match.group(0).upper()}
                }])
            return LLMResponse(text="I'd be happy to help with a return! Could you please provide your order ID (e.g., TR-4521)?")

        if any(kw in user_msg for kw in ["exchange", "swap", "different size", "size exchange"]):
            order_match = __import__("re").search(r'tr-\d+', user_msg, re.IGNORECASE)
            if order_match:
                return LLMResponse(tool_calls=[{
                    "name": "check_return_eligibility",
                    "arguments": {"order_id": order_match.group(0).upper(), "is_exchange": True}
                }])
            return LLMResponse(text="I can help with a size exchange! Please provide your order ID.")

        if any(kw in user_msg for kw in ["policy", "shipping", "delivery time", "how long", "charge", "free shipping"]):
            return LLMResponse(tool_calls=[{
                "name": "search_policy",
                "arguments": {"query": user_msg}
            }])

        if any(kw in user_msg for kw in ["human", "agent", "manager", "escalate", "speak to someone"]):
            return LLMResponse(tool_calls=[{
                "name": "escalate_to_human",
                "arguments": {
                    "reason": "customer_request",
                    "customer_issue": "Customer requested to speak with a human agent."
                }
            }])

        if any(kw in user_msg for kw in ["hello", "hi", "hey", "good morning", "good afternoon"]):
            return LLMResponse(text="Hello! Welcome to Trendly support. I'm here to help you with order tracking, returns, exchanges, and any questions about our policies. How can I assist you today?")

        return LLMResponse(text="I'd be happy to help! I can assist you with:\n• **Order tracking** — just share your order ID (e.g., TR-4521)\n• **Returns & refunds**\n• **Size exchanges**\n• **Shipping & policy questions**\n\nWhat would you like help with?")
