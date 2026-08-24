import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from app.config import settings
from app.models import (
    Order, OrderItem, ReturnEligibilityResult, ReturnActionResult, ExchangeActionResult
)
from app.repositories.order_repository import order_repository

logger = logging.getLogger(__name__)

NON_RETURNABLE_CATEGORIES = {
    "innerwear", "socks", "jewellery", "jewelry", "beauty", "fragrance", "face masks", "gift cards"
}

REFUND_TIMELINES = {
    "credit_card": "5–7 business days to original card after warehouse inspection",
    "prepaid_card": "5–7 business days to original card after warehouse inspection",
    "upi": "3–5 business days to original UPI ID after warehouse inspection",
    "cash_on_delivery": "7–10 business days via bank transfer (link sent by human agent) or store credit",
    "store_credit": "Immediate upon warehouse receipt and inspection"
}

class ReturnService:
    """Deterministic return and exchange eligibility evaluation and mock transaction engine."""

    def __init__(self):
        # In-memory transaction stores for returns and exchanges
        self._created_returns: Dict[str, Dict[str, Any]] = {}
        self._created_exchanges: Dict[str, Dict[str, Any]] = {}
        self._exchange_counts_by_sku: Dict[str, int] = {}

    def _get_reference_date(self) -> datetime:
        """Returns the system reference date (default: 2026-08-01 for evaluation dataset)."""
        try:
            return datetime.strptime(settings.REFERENCE_DATE, "%Y-%m-%d")
        except Exception:
            return datetime(2026, 8, 1)

    def check_eligibility(
        self,
        order_id: str,
        item_sku: Optional[str] = None,
        return_reason: Optional[str] = None,
        is_exchange: bool = False
    ) -> ReturnEligibilityResult:
        """
        Determines eligibility deterministically by combining order data and policy rules.
        """
        order = order_repository.get_order(order_id)
        if not order:
            return ReturnEligibilityResult(
                eligible=False,
                order_id=order_id,
                reasons=[f"Order {order_id} was not found in our records."],
                policy_clauses=[],
                allowed_actions=["none"],
                required_next_steps=["Please verify the order ID with the customer."]
            )

        # Target item selection (if single item order or SKU specified)
        target_item: Optional[OrderItem] = None
        if item_sku:
            for it in order.items:
                if it.sku.upper() == item_sku.strip().upper():
                    target_item = it
                    break
        elif len(order.items) == 1:
            target_item = order.items[0]

        # 1. Order Status Checks
        if order.status == "cancelled":
            return ReturnEligibilityResult(
                eligible=False,
                order_id=order.order_id,
                item_sku=target_item.sku if target_item else None,
                item_name=target_item.name if target_item else None,
                reasons=["This order was cancelled. No return or exchange can be raised against a cancelled order."],
                policy_clauses=["Section 2.6: Cancelled orders"],
                allowed_actions=["none"]
            )

        if order.status == "lost_in_transit":
            return ReturnEligibilityResult(
                eligible=False,
                order_id=order.order_id,
                item_sku=target_item.sku if target_item else None,
                item_name=target_item.name if target_item else None,
                reasons=["This order is marked as lost in transit. Per policy, this is handled as a lost-parcel claim by a human support agent, not as a standard return."],
                policy_clauses=["Section 1.6: Lost parcels"],
                allowed_actions=["none"],
                required_next_steps=["Escalate to human support for lost-parcel claim resolution (free replacement or full refund)."]
            )

        if order.status in ("in_transit", "partially_shipped", "delayed"):
            return ReturnEligibilityResult(
                eligible=False,
                order_id=order.order_id,
                item_sku=target_item.sku if target_item else None,
                item_name=target_item.name if target_item else None,
                reasons=[f"Order is currently '{order.status.replace('_', ' ')}' and has not yet been delivered. Returns and exchanges can only be initiated after delivery."],
                policy_clauses=["Section 2.1: Return window (counted from delivery date)"],
                allowed_actions=["none"],
                required_next_steps=["Ask customer to await delivery before raising a return."]
            )

        if order.status != "delivered" or not order.delivered_at:
            return ReturnEligibilityResult(
                eligible=False,
                order_id=order.order_id,
                item_sku=target_item.sku if target_item else None,
                item_name=target_item.name if target_item else None,
                reasons=[f"Order status '{order.status}' is not eligible for return."],
                policy_clauses=["Section 2.1: Return window"],
                allowed_actions=["none"]
            )

        # 2. Return Window Check (30 calendar days from delivery date)
        try:
            delivered_date = datetime.fromisoformat(order.delivered_at.replace("Z", "+00:00")).replace(tzinfo=None)
            ref_date = self._get_reference_date()
            days_since_delivery = (ref_date - delivered_date).days
        except Exception as e:
            logger.error(f"Error parsing delivery date {order.delivered_at}: {e}")
            days_since_delivery = 0

        if days_since_delivery > 30:
            return ReturnEligibilityResult(
                eligible=False,
                order_id=order.order_id,
                item_sku=target_item.sku if target_item else None,
                item_name=target_item.name if target_item else None,
                reasons=[f"The return window has expired. The order was delivered {days_since_delivery} days ago (on {order.delivered_at[:10]}), which exceeds our 30-calendar-day limit."],
                policy_clauses=["Section 2.1: Return window (30 calendar days of delivery date)"],
                allowed_actions=["none"]
            )

        # 3. Item-Specific Category & Final Sale Checks
        if target_item:
            # Check non-returnable category
            cat = target_item.category.lower()
            if cat in NON_RETURNABLE_CATEGORIES or "sock" in target_item.name.lower() or "earring" in target_item.name.lower():
                return ReturnEligibilityResult(
                    eligible=False,
                    order_id=order.order_id,
                    item_sku=target_item.sku,
                    item_name=target_item.name,
                    reasons=[f"'{target_item.name}' belongs to the '{target_item.category}' category, which cannot be returned or exchanged for hygiene and safety reasons."],
                    policy_clauses=["Section 2.3: Non-returnable categories"],
                    allowed_actions=["none"],
                    special_conditions=["Exceptions only apply if the item arrived damaged or defective within 48 hours of delivery (§6.1)."]
                )

            # Check final sale
            if target_item.final_sale:
                if not is_exchange:
                    return ReturnEligibilityResult(
                        eligible=False,
                        order_id=order.order_id,
                        item_sku=target_item.sku,
                        item_name=target_item.name,
                        reasons=[f"'{target_item.name}' was purchased as a FINAL SALE item. It is not eligible for returns, refunds, or store credit."],
                        policy_clauses=["Section 2.4: Final sale items"],
                        allowed_actions=["size_exchange"],
                        required_next_steps=["Offer the customer a size exchange instead, which is permitted for final sale items."]
                    )
                else:
                    return ReturnEligibilityResult(
                        eligible=True,
                        order_id=order.order_id,
                        item_sku=target_item.sku,
                        item_name=target_item.name,
                        reasons=[f"'{target_item.name}' is eligible for a SIZE EXCHANGE within the 30-day window."],
                        policy_clauses=["Section 2.4: Final sale items (size exchange only)", "Section 4.1: Size exchanges"],
                        allowed_actions=["size_exchange"],
                        required_next_steps=["Confirm desired replacement size with customer."]
                    )

            # Footwear special packaging notice
            special_conditions = []
            if cat == "footwear" or "shoe" in target_item.name.lower() or "sneaker" in target_item.name.lower():
                special_conditions.append("Footwear must be returned in the original shoe box. Returns without the box incur a ₹300 deduction (§2.5).")

            # Check exchange limit
            sku_key = f"{order.order_id}_{target_item.sku}"
            if is_exchange and self._exchange_counts_by_sku.get(sku_key, 0) >= 1:
                return ReturnEligibilityResult(
                    eligible=False,
                    order_id=order.order_id,
                    item_sku=target_item.sku,
                    item_name=target_item.name,
                    reasons=["An exchange has already been processed for this item. A second exchange requires human manager approval."],
                    policy_clauses=["Section 4.4: Exchange limit (One exchange per item)"],
                    allowed_actions=["none"],
                    required_next_steps=["Escalate to human support for second exchange approval."]
                )

            # Eligible!
            allowed = ["size_exchange"] if is_exchange else ["return_for_refund", "size_exchange"]
            return ReturnEligibilityResult(
                eligible=True,
                order_id=order.order_id,
                item_sku=target_item.sku,
                item_name=target_item.name,
                reasons=[f"'{target_item.name}' is eligible for return/exchange within the 30-day delivery window."],
                policy_clauses=["Section 2.1: Return window", "Section 2.2: Condition guidelines"],
                allowed_actions=allowed,
                special_conditions=special_conditions,
                required_next_steps=["Ensure items are unworn, unwashed, with original tags and packaging (§2.2).", "Select a convenient reverse pickup window."]
            )

        # If multiple items and none selected yet
        return ReturnEligibilityResult(
            eligible=True,
            order_id=order.order_id,
            reasons=["Order is within the 30-day return window. Please select which item you would like to return/exchange."],
            policy_clauses=["Section 2.1: Return window"],
            allowed_actions=["return_for_refund", "size_exchange"],
            required_next_steps=[f"Specify item SKU or name from order: {', '.join([i.name for i in order.items])}"]
        )

    def create_return(
        self,
        order_id: str,
        item_sku: str,
        reason: str,
        pickup_address: Optional[str] = None
    ) -> ReturnActionResult:
        """
        Creates a mock return transaction if and only if deterministic eligibility passes.
        Idempotent: returns existing return reference if already raised.
        """
        if not reason or len(reason.strip()) < 3:
            return ReturnActionResult(
                success=False,
                order_id=order_id,
                item_sku=item_sku,
                item_name="",
                refund_estimate=0,
                payment_method="",
                refund_timeline="",
                pickup_window="",
                instructions=[],
                message="Return creation failed: A valid return reason must be provided by the customer."
            )

        # Validate eligibility
        eligibility = self.check_eligibility(order_id, item_sku=item_sku, return_reason=reason, is_exchange=False)
        if not eligibility.eligible:
            return ReturnActionResult(
                success=False,
                order_id=order_id,
                item_sku=item_sku,
                item_name=eligibility.item_name or "",
                refund_estimate=0,
                payment_method="",
                refund_timeline="",
                pickup_window="",
                instructions=[],
                message=f"Cannot create return: {'; '.join(eligibility.reasons)}"
            )

        order = order_repository.get_order(order_id)
        target_item = next((i for i in order.items if i.sku.upper() == item_sku.strip().upper()), order.items[0])

        # Idempotency check
        key = f"{order_id}_{target_item.sku}"
        if key in self._created_returns:
            existing = self._created_returns[key]
            return ReturnActionResult(
                success=True,
                return_reference_id=existing["reference_id"],
                order_id=order_id,
                item_sku=target_item.sku,
                item_name=target_item.name,
                refund_estimate=existing["refund_amount"],
                payment_method=order.payment_method,
                refund_timeline=REFUND_TIMELINES.get(order.payment_method, "5-7 business days"),
                pickup_window=existing["pickup_window"],
                instructions=[
                    "Keep item unworn and unwashed with original tags attached.",
                    "Hand the package to the courier during the scheduled pickup window.",
                    "If footwear, include the original shoe box to avoid the ₹300 deduction."
                ],
                message=f"A return request has already been registered (ID: {existing['reference_id']})."
            )

        # Create new return transaction
        ret_id = f"RET-{uuid.uuid4().hex[:6].upper()}"
        refund_amount = target_item.price * target_item.qty
        pickup_window = "Next 1-2 business days (10:00 AM - 6:00 PM IST)"

        self._created_returns[key] = {
            "reference_id": ret_id,
            "order_id": order_id,
            "sku": target_item.sku,
            "item_name": target_item.name,
            "refund_amount": refund_amount,
            "reason": reason,
            "pickup_address": pickup_address or f"{order.shipping_city} address on file",
            "pickup_window": pickup_window,
            "created_at": datetime.utcnow().isoformat()
        }

        timeline = REFUND_TIMELINES.get(order.payment_method, "5-7 business days")
        instructions = [
            "Keep the item unworn and unwashed with original tags attached (§2.2).",
            "Free reverse pickup has been scheduled for your address (§5.1).",
            "Courier will make up to 2 pickup attempts.",
            f"Refund of ₹{refund_amount:,} will be issued via {timeline}."
        ]
        if target_item.category.lower() == "footwear":
            instructions.append("Ensure shoes are packed in their original shoe box to avoid ₹300 box deduction (§2.5).")

        return ReturnActionResult(
            success=True,
            return_reference_id=ret_id,
            order_id=order_id,
            item_sku=target_item.sku,
            item_name=target_item.name,
            refund_estimate=refund_amount,
            payment_method=order.payment_method,
            refund_timeline=timeline,
            pickup_window=pickup_window,
            instructions=instructions,
            message=f"Return request {ret_id} created successfully for {target_item.name}."
        )

    def create_exchange(
        self,
        order_id: str,
        item_sku: str,
        target_size: str
    ) -> ExchangeActionResult:
        """
        Creates a mock size exchange transaction if and only if deterministic eligibility passes.
        """
        if not target_size or len(target_size.strip()) == 0:
            return ExchangeActionResult(
                success=False,
                order_id=order_id,
                item_sku=item_sku,
                item_name="",
                requested_size="",
                pickup_window="",
                instructions=[],
                message="Exchange creation failed: Please specify the requested replacement size."
            )

        eligibility = self.check_eligibility(order_id, item_sku=item_sku, is_exchange=True)
        if not eligibility.eligible:
            return ExchangeActionResult(
                success=False,
                order_id=order_id,
                item_sku=item_sku,
                item_name=eligibility.item_name or "",
                requested_size=target_size,
                pickup_window="",
                instructions=[],
                message=f"Cannot create exchange: {'; '.join(eligibility.reasons)}"
            )

        order = order_repository.get_order(order_id)
        target_item = next((i for i in order.items if i.sku.upper() == item_sku.strip().upper()), order.items[0])

        key = f"{order_id}_{target_item.sku}"
        exc_id = f"EXC-{uuid.uuid4().hex[:6].upper()}"
        pickup_window = "Next 1-2 business days (10:00 AM - 6:00 PM IST)"

        self._created_exchanges[key] = {
            "reference_id": exc_id,
            "order_id": order_id,
            "sku": target_item.sku,
            "item_name": target_item.name,
            "target_size": target_size,
            "pickup_window": pickup_window,
            "created_at": datetime.utcnow().isoformat()
        }
        self._exchange_counts_by_sku[key] = self._exchange_counts_by_sku.get(key, 0) + 1

        return ExchangeActionResult(
            success=True,
            exchange_reference_id=exc_id,
            order_id=order_id,
            item_sku=target_item.sku,
            item_name=target_item.name,
            requested_size=target_size.upper(),
            pickup_window=pickup_window,
            instructions=[
                f"Your size exchange for size {target_size.upper()} has been booked.",
                "Keep the original item unworn, unwashed with original tags attached.",
                "Courier will collect the original item and deliver the new size simultaneously."
            ],
            message=f"Exchange request {exc_id} created successfully for {target_item.name} in size {target_size.upper()}."
        )

return_service = ReturnService()
