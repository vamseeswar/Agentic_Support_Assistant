from typing import Dict, Any, Optional, List
from app.tools.base import BaseTool
from app.services.escalation_service import escalation_service


class EscalateToHumanTool(BaseTool):
    name = "escalate_to_human"
    description = (
        "Escalate the conversation to a human support agent. Use this when: "
        "(1) the policy does not cover the situation, "
        "(2) the customer has a lost-in-transit order (§1.6), "
        "(3) a COD refund requiring bank details is needed (§3.3), "
        "(4) a second exchange needs manager approval (§4.4), "
        "(5) the customer is distressed or requests a human agent, "
        "(6) a damaged/defective item needs replacement (§6.2). "
        "ALWAYS include a full conversation summary and all actions already attempted."
    )
    parameters = {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "The internal reason for escalation (e.g., 'lost_in_transit', 'second_exchange_approval', 'cod_refund_bank_details', 'policy_gap', 'customer_request', 'damaged_defective')."
            },
            "customer_issue": {
                "type": "string",
                "description": "A clear, concise description of the customer's issue in customer-friendly language."
            },
            "order_id": {
                "type": "string",
                "description": "The order ID involved, if applicable."
            },
            "customer_id": {
                "type": "string",
                "description": "The customer ID, if known."
            },
            "conversation_summary": {
                "type": "string",
                "description": "Concise summary of the conversation so far, including what was checked and what actions were attempted."
            },
            "actions_attempted": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of actions already attempted by this assistant (e.g., ['checked_eligibility', 'created_return_RET-XXXXX'])."
            },
            "policy_checked": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Policy sections that were consulted (e.g., ['Section 1.6: Lost parcels', 'Section 3.3: COD refunds'])."
            },
            "requested_resolution": {
                "type": "string",
                "description": "What the customer is requesting as resolution."
            },
            "missing_information": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Any information still needed from the customer or team."
            },
            "priority": {
                "type": "string",
                "enum": ["standard", "urgent"],
                "description": "Priority level — use 'urgent' for lost parcels, payment failures, or highly distressed customers."
            }
        },
        "required": ["reason", "customer_issue"]
    }

    def execute(
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
        priority: str = "standard",
        **kwargs
    ) -> Dict[str, Any]:
        result = escalation_service.escalate(
            reason=reason,
            customer_issue=customer_issue,
            order_id=order_id,
            customer_id=customer_id,
            conversation_summary=conversation_summary,
            actions_attempted=actions_attempted or [],
            policy_checked=policy_checked or [],
            requested_resolution=requested_resolution,
            missing_information=missing_information or [],
            priority=priority
        )
        return result.model_dump()


escalate_to_human_tool = EscalateToHumanTool()
