from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple


class LLMResponse:
    """Represents a response from the LLM, which may include text and/or tool calls."""
    def __init__(
        self,
        text: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        finish_reason: str = "stop"
    ):
        self.text = text
        self.tool_calls = tool_calls or []
        self.finish_reason = finish_reason

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseLLMClient(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_instruction: Optional[str] = None,
    ) -> LLMResponse:
        """Send messages to the LLM and get a response (possibly with tool calls)."""
        pass
