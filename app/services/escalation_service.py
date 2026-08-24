import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.models import EscalationPayload, EscalationResult
from app.repositories.order_repository import order_repository

logger = logging.getLogger(__name__)

class EscalationService:
    """Handles structured escalation of customer issues to human support representatives."""

    def __init__(self):
        self._escalation_log: Dict[str, EscalationPayload] = {}

    def escalate(
        self,
        reason: str,
        customer_issue: str,
        order_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        conversation_summary: Optional[str] = None,
        actions_attempted: Optional[List[str]] = None,
        policy_checked: Optional[List[str]] = None,
        requested_resolution: Optional[str] = None,
        missing_information: Optional[List[str]] = None,
        priority: str = "standard"
    ) -> EscalationResult:
        """
        Constructs and records a complete structured escalation ticket for human support.
        """
        esc_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
        
        # Enrich with customer name if available
        customer_name = None
        if order_id:
            order = order_repository.get_order(order_id)
            if order:
                if not customer_id:
                    customer_id = order.customer_id
                cust = order_repository.get_customer(order.customer_id)
                if cust:
                    customer_name = cust.name
        elif customer_id:
            cust = order_repository.get_customer(customer_id)
            if cust:
                customer_name = cust.name

        # Determine priority automatically if high-risk situation
        if "lost" in reason.lower() or "lost" in customer_issue.lower():
            priority = "urgent"
        elif "bank" in reason.lower() or "payment" in reason.lower():
            priority = "urgent"

        summary_text = conversation_summary or f"Customer reported: {customer_issue}. Escalated due to: {reason}."

        payload = EscalationPayload(
            escalation_id=esc_id,
            timestamp=datetime.utcnow().isoformat(),
            customer_id=customer_id,
            customer_name=customer_name,
            order_id=order_id,
            reason=reason,
            customer_issue=customer_issue,
            conversation_summary=summary_text,
            actions_attempted=actions_attempted or [],
            policy_checked=policy_checked or [],
            requested_resolution=requested_resolution,
            missing_information=missing_information or [],
            priority=priority
        )

        self._escalation_log[esc_id] = payload
        logger.info(f"Created escalation ticket {esc_id} (Priority: {priority}) for Order {order_id}: {reason}")

        message = (
            f"I have escalated your request to our human support team (Ticket ID: **{esc_id}**). "
            "A representative will review the complete summary of our conversation and reach out to assist you directly. "
            "Our support hours are 9:00 AM – 9:00 PM IST, 7 days a week."
        )

        return EscalationResult(
            success=True,
            escalation_id=esc_id,
            status="escalated",
            message=message,
            payload=payload
        )

    def get_escalation(self, escalation_id: str) -> Optional[EscalationPayload]:
        return self._escalation_log.get(escalation_id)

    def get_all_escalations(self) -> List[EscalationPayload]:
        return list(self._escalation_log.values())

escalation_service = EscalationService()
