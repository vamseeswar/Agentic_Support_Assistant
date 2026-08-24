import logging
from fastapi import APIRouter, HTTPException, Path
from typing import Dict, Any
from app.models import ChatRequest, ChatResponse
from app.agent import agent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])

@router.post("", response_model=ChatResponse)
async def handle_chat_message(request: ChatRequest) -> ChatResponse:
    """
    Main conversational endpoint: accepts a message, routes through agentic tool execution,
    and returns assistant response along with transparent tool call logs.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    try:
        response = agent.handle_message(request)
        return response
    except Exception as e:
        logger.error(f"Error handling chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal agent error: {str(e)}")

@router.get("/{conversation_id}/history")
async def get_conversation_history(conversation_id: str = Path(...)):
    """Retrieve full conversation history for a given conversation ID."""
    state = agent.state_store.get(conversation_id)
    if not state:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {
        "conversation_id": conversation_id,
        "customer_id": state.customer_id,
        "current_order_id": state.current_order_id,
        "messages": state.messages
    }

@router.delete("/{conversation_id}")
async def reset_conversation(conversation_id: str = Path(...)):
    """Reset / clear a conversation session."""
    deleted = agent.reset_conversation(conversation_id)
    return {"conversation_id": conversation_id, "deleted": deleted}
