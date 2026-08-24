import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime


class ConversationState:
    """Encapsulates the state of a customer conversation across turns.
    Messages are stored as raw dicts for direct LLM compatibility.
    """

    def __init__(self, conversation_id: str, customer_id: Optional[str] = None):
        self.conversation_id = conversation_id
        self.customer_id = customer_id
        self.current_order_id: Optional[str] = None
        self.current_item_sku: Optional[str] = None
        self.escalated: bool = False
        self.escalation_id: Optional[str] = None
        # Raw dict messages: {"role": "user/assistant/tool", "content": "...", ...}
        self.messages: List[Dict[str, Any]] = []
        self.created_at: str = datetime.utcnow().isoformat()
        self.updated_at: str = datetime.utcnow().isoformat()

    def add_message(self, role: str, content: str):
        """Append a simple user or assistant message."""
        self.messages.append({"role": role, "content": content})
        self.updated_at = datetime.utcnow().isoformat()

    def get_history_for_llm(self) -> List[Dict[str, Any]]:
        """Return messages in a format compatible with the Groq/OpenAI multi-turn API."""
        result = []
        for msg in self.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role in ("user", "assistant"):
                m: Dict[str, Any] = {"role": role, "content": content}
                # Include raw tool_calls if this was an assistant turn with tool calls
                if role == "assistant" and msg.get("tool_calls_raw"):
                    m["tool_calls"] = msg["tool_calls_raw"]
                result.append(m)
            elif role == "tool":
                result.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", "call_0"),
                    "content": content if isinstance(content, str) else str(content)
                })
            # Skip system messages — they're passed separately as system_instruction
        return result


class StateStore:
    """In-memory store for conversation states."""

    def __init__(self):
        self._store: Dict[str, ConversationState] = {}

    def get_or_create(self, conversation_id: str, customer_id: Optional[str] = None) -> ConversationState:
        if conversation_id not in self._store:
            self._store[conversation_id] = ConversationState(
                conversation_id=conversation_id,
                customer_id=customer_id
            )
        else:
            state = self._store[conversation_id]
            if customer_id and not state.customer_id:
                state.customer_id = customer_id
        return self._store[conversation_id]

    def get(self, conversation_id: str) -> Optional[ConversationState]:
        return self._store.get(conversation_id)

    def delete(self, conversation_id: str) -> bool:
        if conversation_id in self._store:
            del self._store[conversation_id]
            return True
        return False

    def clear(self):
        self._store.clear()


state_store = StateStore()
