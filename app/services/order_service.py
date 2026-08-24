from typing import Optional
from app.models import Order
from app.repositories.order_repository import order_repository


class OrderService:
    """Plain-language order status explanations with edge-case handling."""

    STATUS_EXPLANATIONS = {
        "in_transit": "Your order is currently on its way to you.",
        "delivered": "Your order has been delivered.",
        "partially_shipped": "Part of your order has been shipped; the remaining item(s) are backordered.",
        "delayed": "Your order has been delayed beyond its expected delivery date.",
        "lost_in_transit": "Your order has been reported as lost by the carrier.",
        "cancelled": "Your order has been cancelled.",
    }

    def get_order(self, order_id: str) -> Optional[Order]:
        return order_repository.get_order(order_id)

    def explain_status(self, order: Order) -> str:
        base = self.STATUS_EXPLANATIONS.get(
            order.status, f"The order status is '{order.status}'."
        )

        parts = [f"**Order {order.order_id}** — {base}"]

        if order.status == "in_transit":
            parts.append(f"Carrier: {order.carrier} | Tracking: {order.tracking_number}")
            if order.expected_delivery:
                parts.append(f"Expected delivery: **{order.expected_delivery}**")

        elif order.status == "delivered":
            parts.append(f"Delivered on: **{order.delivered_at[:10] if order.delivered_at else 'N/A'}**")

        elif order.status == "partially_shipped":
            shipped = [i.name for i in order.items if i.shipped]
            backordered = [
                f"{i.name} (ETA: {i.backorder_eta or 'TBD'})"
                for i in order.items if not i.shipped
            ]
            if shipped:
                parts.append(f"Already shipped: {', '.join(shipped)}")
            if backordered:
                parts.append(f"Pending shipment: {', '.join(backordered)}")

        elif order.status == "delayed":
            parts.append(
                f"Original expected delivery was **{order.expected_delivery}**. "
                "Per our policy, you are eligible for a ₹250 store credit — just ask if you'd like that applied."
            )
            if order.carrier and order.tracking_number:
                parts.append(f"Carrier: {order.carrier} | Tracking: {order.tracking_number}")

        elif order.status == "lost_in_transit":
            parts.append(
                "I'm sorry to hear this! Per Trendly policy (§1.6), a lost parcel is handled as a "
                "lost-parcel claim by our human support team — not as a standard return. "
                "I'll escalate this to a human agent who will resolve it within 5 business days "
                "with either a free replacement or a full refund."
            )

        elif order.status == "cancelled":
            if order.refund_status:
                parts.append(f"Refund status: **{order.refund_status}**")
            parts.append("Since the order is cancelled, no return can be raised against it (§2.6).")

        # Item summary
        item_lines = [
            f"  • {i.name} (Size: {i.size}, Qty: {i.qty}) — ₹{i.price:,}"
            + (" ⚠️ Final Sale" if i.final_sale else "")
            for i in order.items
        ]
        parts.append("\n**Items:**\n" + "\n".join(item_lines))
        parts.append(f"\n**Total:** ₹{order.total:,} | Payment: {order.payment_method.replace('_', ' ').title()}")

        return "\n".join(parts)


order_service = OrderService()
