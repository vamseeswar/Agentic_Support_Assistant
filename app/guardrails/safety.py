import re
import logging
from typing import Optional, Tuple
from app.models import Order
from app.repositories.order_repository import order_repository

logger = logging.getLogger(__name__)

# Patterns for prompt injection / system prompt extraction
PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior) (instructions|prompts|rules)",
    r"you are now in (developer|dan|jailbreak|unrestricted) mode",
    r"(reveal|print|show|output|display|what is|tell me) (your|the) (system prompt|hidden prompt|instructions|raw prompt)",
    r"system prompt:",
    r"<script.*?>",
    r"execute arbitrary code",
]

# Patterns for unauthorized discount requests
DISCOUNT_BEGGING_PATTERNS = [
    r"(give|offer|grant|apply|provide|can i have|give me) (a )?(\d+%\s*(off|discount)|free coupon|unauthorized discount|special discount|discount code|promo code)",
    r"give me a discount",
    r"waive the fee for me",
    r"goodwill discount",
    r"free voucher",
]

# Patterns for financial detail collection in chat (prohibited)
FINANCIAL_DATA_PATTERNS = [
    r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b",  # 16-digit card
    r"\b\d{9,18}\b",                             # Long bank account numbers when sent with words like account
    r"\bcvv\s*[:=]?\s*\d{3,4}\b",
]

class SafetyGuard:
    """Deterministic security and safety guardrail engine."""

    def check_input_safety(self, message: str, customer_id: Optional[str] = None) -> Tuple[bool, Optional[str], str]:
        """
        Validates user input against safety, prompt injection, and unauthorized discount policies.
        Returns: (is_safe: bool, refusal_reason: Optional[str], refusal_message: str)
        """
        msg_lower = message.lower().strip()

        # 1. Check prompt injection & system prompt extraction
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                logger.warning(f"Safety guard triggered: Prompt injection pattern detected: '{pattern}'")
                return (
                    False,
                    "prompt_injection_refusal",
                    "I am Trendly's customer support assistant. I cannot modify my system instructions, execute external scripts, or disclose internal prompts. How can I assist you with your Trendly order today?"
                )

        # 2. Check unauthorized discounts / vouchers
        for pattern in DISCOUNT_BEGGING_PATTERNS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                logger.info(f"Safety guard triggered: Unauthorized discount request: '{pattern}'")
                return (
                    False,
                    "unauthorized_discount_refusal",
                    "Per Trendly company policy (Section 7), our support assistants are not authorized to issue discretionary discounts, custom promotional codes, or goodwill credits. (The only policy-defined credit is a ₹250 store credit for orders delayed more than 3 business days past expected delivery, as detailed in Section 1.5)."
                )

        # 3. Check sensitive financial data submission in chat
        if "bank" in msg_lower or "account" in msg_lower or "cvv" in msg_lower or "card" in msg_lower:
            for pattern in FINANCIAL_DATA_PATTERNS:
                if re.search(pattern, message, re.IGNORECASE):
                    logger.warning("Safety guard triggered: Customer attempted to send payment/bank details in chat.")
                    return (
                        False,
                        "sensitive_data_refusal",
                        "For your security, Trendly policy strictly prohibits collecting bank account numbers, card numbers, or CVVs directly in chat (§3.3 & §7). For Cash on Delivery refunds, a human support agent will send you a secure, encrypted link to securely provide your refund account details."
                    )

        return True, None, ""

    def validate_customer_order_access(self, requested_order_id: str, active_customer_id: Optional[str]) -> Tuple[bool, str]:
        """
        Enforces customer data isolation: prevents one customer from viewing another's order.
        """
        if not active_customer_id or not requested_order_id:
            return True, ""  # If customer ID is not bound to the session yet, allow lookup

        order = order_repository.get_order(requested_order_id)
        if not order:
            return False, f"Order {requested_order_id} not found."

        if order.customer_id.upper() != active_customer_id.upper():
            logger.warning(f"Data isolation violation: Customer {active_customer_id} tried to access Order {requested_order_id} belonging to {order.customer_id}")
            return (
                False,
                "For privacy and security reasons, I cannot disclose information for an order not associated with your account (§7)."
            )

        return True, ""

safety_guard = SafetyGuard()
