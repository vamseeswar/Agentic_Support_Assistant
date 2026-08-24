from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
from app.repositories.order_repository import order_repository
from app.services.order_service import order_service
from app.models import Order

router = APIRouter(prefix="/api/orders", tags=["Orders"])

@router.get("", response_model=List[Order])
async def list_orders(customer_id: Optional[str] = Query(None, description="Filter orders by customer ID")):
    """List all orders in the evaluation dataset, optionally filtered by customer ID."""
    if customer_id:
        return order_repository.get_orders_for_customer(customer_id)
    return order_repository.get_all_orders()

@router.get("/{order_id}")
async def get_order_details(order_id: str = Path(..., description="The Trendly order ID")):
    """Get single order details along with plain-language status explanation."""
    order = order_repository.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found.")
    
    explanation = order_service.explain_status(order)
    return {
        "order": order.model_dump(),
        "status_explanation": explanation
    }
