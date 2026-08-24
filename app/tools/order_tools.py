from typing import Dict, Any, Optional
from app.tools.base import BaseTool
from app.services.order_service import order_service
from app.repositories.order_repository import order_repository

class GetOrderTool(BaseTool):
    """Tool to retrieve and inspect an order from orders.json."""

    name = "get_order"
    description = "Retrieve detailed information about a customer order by its order ID (e.g., 'TR-4521'). Returns order status, items, tracking info, delivery dates, and plain-language explanation."
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The exact Trendly order ID, e.g., 'TR-4521' or 'TR-4522'."
            }
        },
        "required": ["order_id"]
    }

    def execute(self, order_id: str, **kwargs) -> Dict[str, Any]:
        if not order_id or not str(order_id).strip():
            return {
                "success": False,
                "error": "Missing order_id. Please provide a valid Trendly order ID (e.g., TR-4521)."
            }

        order = order_repository.get_order(order_id)
        if not order:
            return {
                "success": False,
                "error": f"Order '{order_id}' was not found in Trendly's records. Please ask the customer to check the order ID."
            }

        explanation = order_service.explain_status(order)

        return {
            "success": True,
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "status": order.status,
            "placed_at": order.placed_at,
            "delivered_at": order.delivered_at,
            "expected_delivery": order.expected_delivery,
            "carrier": order.carrier,
            "tracking_number": order.tracking_number,
            "payment_method": order.payment_method,
            "shipping_city": order.shipping_city,
            "total": order.total,
            "items": [i.model_dump() for i in order.items],
            "explanation": explanation
        }

get_order_tool = GetOrderTool()
