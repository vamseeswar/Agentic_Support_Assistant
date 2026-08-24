import json
import logging
from typing import List, Dict, Any, Optional
from app.llm.base import BaseLLMClient, LLMResponse
from app.config import settings

logger = logging.getLogger(__name__)

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    Groq = None


class GroqClient(BaseLLMClient):
    """Groq API client with tool/function calling support (OpenAI-compatible)."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        if not HAS_GROQ:
            raise ImportError("groq package not installed. Run: pip install groq")

        self.api_key = api_key or settings.GROQ_API_KEY
        self.model_name = model_name or settings.LLM_MODEL

        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required. Set it in .env or environment variables.")

        self.client = Groq(api_key=self.api_key)
        logger.info(f"GroqClient initialized with model: {self.model_name}")

    def _build_tools(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict]]:
        """Convert tool declarations to OpenAI-compatible function format for Groq."""
        if not tools:
            return None
        result = []
        for tool in tools:
            result.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            })
        return result

    def _build_messages(
        self,
        messages: List[Dict[str, Any]],
        system_instruction: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Convert internal message format to OpenAI-compatible format for Groq."""
        result = []
        if system_instruction:
            result.append({"role": "system", "content": system_instruction})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                result.append({"role": "system", "content": content})
            elif role == "assistant":
                # Check if this assistant message had tool calls
                if msg.get("tool_calls_raw"):
                    result.append({
                        "role": "assistant",
                        "content": content or None,
                        "tool_calls": msg["tool_calls_raw"]
                    })
                else:
                    result.append({"role": "assistant", "content": content})
            elif role == "tool":
                result.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", "call_0"),
                    "content": content if isinstance(content, str) else json.dumps(content)
                })
            else:
                result.append({"role": "user", "content": content})

        return result

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
    ) -> LLMResponse:
        """Send messages to Groq and return response with possible tool calls."""
        try:
            groq_messages = self._build_messages(messages, system_instruction)
            groq_tools = self._build_tools(tools)

            kwargs = {
                "model": self.model_name,
                "messages": groq_messages,
                "temperature": 0.2,
                "max_tokens": 2048,
            }
            if groq_tools:
                kwargs["tools"] = groq_tools
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message

            text = message.content
            tool_calls = []
            tool_calls_raw = []

            if message.tool_calls:
                for tc in message.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append({
                        "name": tc.function.name,
                        "arguments": args,
                        "id": tc.id
                    })
                    tool_calls_raw.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}"
                        }
                    })

            finish_reason = "tool_calls" if tool_calls else "stop"
            resp = LLMResponse(text=text, tool_calls=tool_calls, finish_reason=finish_reason)
            resp.tool_calls_raw = tool_calls_raw  # Store raw format for multi-turn
            return resp

        except Exception as e:
            logger.error(f"Groq API error: {e}", exc_info=True)
            return LLMResponse(
                text=f"I'm experiencing a temporary issue. Please try again shortly. (Error: {str(e)[:100]})",
                finish_reason="error"
            )
