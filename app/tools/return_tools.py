from typing import Dict, Any, Optional
from app.tools.base import BaseTool
from app.services.return_service import return_service


class CheckReturnEligibilityTool(BaseTool):
    name = "check_return_eligibility"
    description = (
        "Check whether a specific item in an order is eligible for a return or exchange. "
        "Call this BEFORE creating any return or exchange to confirm eligibility. "
        "Returns eligibility status, allowed actions, policy clauses, and any special conditions."
    )
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The Trendly order ID (e.g. TR-4521)."
            },
            "item_sku": {
                "type": "string",
                "description": "The SKU of the item to check (e.g. SKU-BLZ-01). If omitted and order has one item, that item is checked."
            },
            "is_exchange": {
                "type": "boolean",
                "description": "Set to true if checking eligibility for an exchange rather than a return. Default false."
            }
        },
        "required": ["order_id"]
    }

    def execute(self, order_id: str, item_sku: Optional[str] = None, is_exchange: bool = False, **kwargs) -> Dict[str, Any]:
        result = return_service.check_eligibility(order_id, item_sku=item_sku, is_exchange=is_exchange)
        return result.model_dump()


class CreateReturnTool(BaseTool):
    name = "create_return"
    description = (
        "Create a return request for a delivered item that is within the 30-day return window. "
        "Always call check_return_eligibility first. "
        "Schedules a free reverse pickup and calculates refund estimate based on order data and policy."
    )
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The Trendly order ID."
            },
            "item_sku": {
                "type": "string",
                "description": "The SKU of the item being returned."
            },
            "reason": {
                "type": "string",
                "description": "Customer-provided reason for the return (e.g., 'wrong size', 'changed my mind', 'product quality issue')."
            },
            "pickup_address": {
                "type": "string",
                "description": "Optional pickup address if different from address on file."
            }
        },
        "required": ["order_id", "item_sku", "reason"]
    }

    def execute(self, order_id: str, item_sku: str, reason: str, pickup_address: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        result = return_service.create_return(order_id, item_sku, reason, pickup_address)
        return result.model_dump()


class CreateExchangeTool(BaseTool):
    name = "create_exchange"
    description = (
        "Create a size exchange request for a delivered item within the 30-day exchange window. "
        "Only one exchange is permitted per item without human approval. "
        "Always call check_return_eligibility with is_exchange=true first."
    )
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The Trendly order ID."
            },
            "item_sku": {
                "type": "string",
                "description": "The SKU of the item to exchange."
            },
            "target_size": {
                "type": "string",
                "description": "The desired replacement size (e.g., 'L', 'XL', '42', 'UK8')."
            }
        },
        "required": ["order_id", "item_sku", "target_size"]
    }

    def execute(self, order_id: str, item_sku: str, target_size: str, **kwargs) -> Dict[str, Any]:
        result = return_service.create_exchange(order_id, item_sku, target_size)
        return result.model_dump()


check_return_eligibility_tool = CheckReturnEligibilityTool()
create_return_tool = CreateReturnTool()
create_exchange_tool = CreateExchangeTool()
