from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# --- Order Domain Models ---

class OrderItem(BaseModel):
    sku: str
    name: str
    category: str  # apparel, innerwear, jewellery, accessories, footwear, etc.
    size: Optional[str] = None
    qty: int
    price: int
    final_sale: bool = False
    shipped: Optional[bool] = None
    backorder_eta: Optional[str] = None

class Customer(BaseModel):
    customer_id: str
    name: str
    email: str
    phone: str

class Order(BaseModel):
    order_id: str
    customer_id: str
    status: str  # in_transit, delivered, partially_shipped, delayed, lost_in_transit, cancelled
    placed_at: str
    delivered_at: Optional[str] = None
    expected_delivery: Optional[str] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    payment_method: str  # credit_card, prepaid_card, upi, cash_on_delivery, store_credit
    shipping_city: str
    items: List[OrderItem]
    total: int
    cancelled_at: Optional[str] = None
    refund_status: Optional[str] = None
    note_for_designers: Optional[str] = Field(None, alias="_note_for_designers")

# --- Policy Domain Models ---

class PolicyChunk(BaseModel):
    section_number: str
    section_title: str
    content: str
    keywords: List[str]

class PolicySearchResult(BaseModel):
    found: bool
    query: str
    matched_sections: List[Dict[str, Any]]
    snippet: str
    source: str = "trendly_policy.md"

# --- Return & Exchange Models ---

class ReturnEligibilityResult(BaseModel):
    eligible: bool
    order_id: str
    item_sku: Optional[str] = None
    item_name: Optional[str] = None
    reasons: List[str]
    policy_clauses: List[str]
    allowed_actions: List[str]  # return_for_refund, size_exchange, none
    special_conditions: List[str] = []
    required_next_steps: List[str] = []

class ReturnActionResult(BaseModel):
    success: bool
    return_reference_id: Optional[str] = None
    order_id: str
    item_sku: str
    item_name: str
    refund_estimate: int
    payment_method: str
    refund_timeline: str
    pickup_window: str
    instructions: List[str]
    message: str

class ExchangeActionResult(BaseModel):
    success: bool
    exchange_reference_id: Optional[str] = None
    order_id: str
    item_sku: str
    item_name: str
    requested_size: str
    pickup_window: str
    instructions: List[str]
    message: str

# --- Escalation Models ---

class EscalationPayload(BaseModel):
    escalation_id: str
    timestamp: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    order_id: Optional[str] = None
    reason: str
    customer_issue: str
    conversation_summary: str
    actions_attempted: List[str] = []
    policy_checked: List[str] = []
    requested_resolution: Optional[str] = None
    missing_information: List[str] = []
    priority: str = "standard"  # urgent, standard, low

class EscalationResult(BaseModel):
    success: bool
    escalation_id: str
    status: str = "escalated"
    message: str
    payload: EscalationPayload

# --- Chat API Models ---

class ToolCallSummary(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result_summary: str
    success: bool

class ChatMessage(BaseModel):
    role: str  # user, assistant, system, tool
    content: str
    timestamp: Optional[str] = None
    tool_calls: Optional[List[ToolCallSummary]] = None

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    customer_id: Optional[str] = None

class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    status: str = "resolved"  # resolved, needs_clarification, escalated, refused
    order_id: Optional[str] = None
    escalation_id: Optional[str] = None
    tool_calls: List[ToolCallSummary] = []
