"""
Tests the Lambda order-processor's business logic directly (no real Lambda
runtime / SQS event envelope needed). `lambda` is a reserved Python keyword,
so lambda/order_processor is added to sys.path here and its `services`
module is imported as a top-level module, exactly the way it resolves once
deployed as a Lambda zip with handler.py at the package root.
"""
import os
import sys
from decimal import Decimal
from unittest.mock import patch

_LAMBDA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lambda", "order_processor"))
if _LAMBDA_DIR not in sys.path:
    sys.path.insert(0, _LAMBDA_DIR)

from services.processing import OrderProcessingError, process_order_message  # noqa: E402

from app.models.order import Order, OrderStatus  # noqa: E402
from app.models.order_item import OrderItem  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


def _seed_pending_order(db_session):
    user = User(name="Buyer", email="buyer@example.com", password_hash="x", role=UserRole.CUSTOMER)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    product = Product(name="Gadget", price=Decimal("15.00"), stock_quantity=10)
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    order = Order(
        user_id=user.id,
        order_number="ORD-2026-000999",
        total_amount=Decimal("30.00"),
        status=OrderStatus.PENDING,
        shipping_address="1 Test Way",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    db_session.add(OrderItem(order_id=order.id, product_id=product.id, quantity=2, unit_price=Decimal("15.00"), subtotal=Decimal("30.00")))
    db_session.commit()
    db_session.refresh(order)
    return order


def test_process_order_message_advances_pending_order_to_confirmed(db_session):
    order = _seed_pending_order(db_session)
    message_body = {"order_id": order.id, "idempotency_key": "test-key-1"}

    with patch("services.processing.aws_sns.publish_order_event") as mock_sns, \
         patch("services.processing.aws_s3.store_processing_log") as mock_s3:
        mock_s3.return_value = "orders/2026/09/ORD-2026-000999/processing-log.json"

        result = process_order_message(db_session, "sqs-msg-1", message_body)

    db_session.refresh(order)
    assert order.status == OrderStatus.CONFIRMED
    assert result["status"] == "processed"
    assert result["final_status"] == "CONFIRMED"
    assert mock_sns.call_count == 2  # PROCESSING then CONFIRMED
    mock_s3.assert_called_once()


def test_process_order_message_is_idempotent_for_duplicate_messages(db_session):
    order = _seed_pending_order(db_session)
    message_body = {"order_id": order.id, "idempotency_key": "duplicate-key"}

    with patch("services.processing.aws_sns.publish_order_event"), \
         patch("services.processing.aws_s3.store_processing_log", return_value="key"):
        process_order_message(db_session, "sqs-msg-1", message_body)
        # Simulate SQS redelivering the exact same message.
        second_result = process_order_message(db_session, "sqs-msg-1-retry", message_body)

    assert second_result["status"] == "skipped_duplicate"


def test_process_order_message_skips_non_pending_orders(db_session):
    order = _seed_pending_order(db_session)
    order.status = OrderStatus.CANCELLED
    db_session.commit()

    result = process_order_message(db_session, "sqs-msg-2", {"order_id": order.id, "idempotency_key": "k2"})
    assert result["status"] == "skipped_not_pending"


def test_process_order_message_raises_for_missing_order(db_session):
    import pytest

    with pytest.raises(OrderProcessingError):
        process_order_message(db_session, "sqs-msg-3", {"order_id": 999999, "idempotency_key": "k3"})


def test_process_order_message_raises_for_missing_order_id(db_session):
    import pytest

    with pytest.raises(OrderProcessingError):
        process_order_message(db_session, "sqs-msg-4", {"idempotency_key": "k4"})
