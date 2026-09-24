import logging
from flask import current_app
import razorpay
from app import db
from app.razorpay_client import client

logger = logging.getLogger(__name__)


def cancel_and_refund_order(order, reason="Customer or Admin cancellation"):
    """
    Cancels an order, restores product inventory, and triggers payment refund via Razorpay.
    Returns: (success: bool, message: str)
    """
    if order.status == "cancelled":
        return False, "Order is already cancelled."

    previous_status = order.status

    # 1. Restore product inventory if order was paid or shipped
    if previous_status in ["paid", "shipped"]:
        for item in order.items:
            item.product.stock += item.quantity

    # 2. Process Razorpay Refund if payment was captured
    if order.razorpay_payment_id and previous_status in ["paid", "shipped"]:
        is_test = current_app.config.get("TESTING", False)
        is_mock = is_test or order.razorpay_payment_id.startswith("pay_sim_") or order.razorpay_payment_id.startswith("mock_pay_") or (order.razorpay_order_id and order.razorpay_order_id.startswith("mock_order_"))

        if not is_mock:
            try:
                amount_paise = int(order.total_amount * 100)
                refund_response = client.payment.refund(order.razorpay_payment_id, {
                    "amount": amount_paise,
                    "notes": {
                        "reason": reason,
                        "order_id": str(order.id)
                    }
                })
                order.refund_id = refund_response.get("id", f"rfnd_{order.id}")
                order.refund_status = "processed"
            except Exception as e:
                logger.error(f"Razorpay Refund failed for Order #{order.id}: {e}")
                order.refund_status = "failed"
                order.status = "cancelled"
                db.session.commit()
                return False, f"Order marked as cancelled, but automated payment refund encountered an error: {str(e)}"
        else:
            # Simulated refund in dev / test mode
            order.refund_id = f"rfnd_sim_{order.id}"
            order.refund_status = "processed"
    else:
        order.refund_status = "none"

    order.status = "cancelled"
    db.session.commit()

    amt_str = f"{float(order.total_amount):.2f}"
    if order.refund_status == "processed":
        return True, f"Order #{order.id} has been cancelled and ₹{amt_str} refund was processed successfully (Refund Ref: {order.refund_id}). Items have been restored to inventory."
    return True, f"Order #{order.id} has been cancelled and items restored to inventory."
