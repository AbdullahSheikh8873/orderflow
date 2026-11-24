"""
Order-processing business logic used by the Lambda handler.

Kept separate from handler.py so it can be unit tested without any Lambda
runtime / SQS event envelope involved, and so the FastAPI app's test suite
can import and exercise it directly with mocked AWS clients.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.aws import s3 as aws_s3
from app.aws import sns as aws_sns
from app.core.logging_config import get_logger
from app.models.order import Order, OrderStatus
from app.models.order_event import EventStatus, EventType, OrderEvent
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository

logger = get_logger("lambda.order_processor")


class OrderProcessingError(Exception):
    """Raised when a message cannot be processed and should go to the DLQ after max retries."""


def process_order_message(db: Session, message_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes a single ORDER_CREATED SQS message end to end:

      1. Idempotency check (message_id is unique per SQS delivery attempt
         group -- we key on it so redeliveries are safely ignored).
      2. Load the order from PostgreSQL.
      3. Re-validate stock / order integrity.
      4. Advance the order PENDING -> PROCESSING -> CONFIRMED.
      5. Write an audit OrderEvent row per transition.
      6. Publish SNS notifications for each transition.
      7. Write a processing-log JSON audit file to S3.

    Returns a small summary dict, mainly useful for tests/logging.
    """
    orders_repo = OrderRepository(db)
    products_repo = ProductRepository(db)

    # --- 1. Idempotency guard --------------------------------------
    idempotency_key = body.get("idempotency_key") or f"sqs-{message_id}"
    existing = orders_repo.get_event_by_idempotency_key(f"processed-{idempotency_key}")
    if existing is not None:
        logger.info("Duplicate SQS message ignored (already processed)", extra={"data": {"key": idempotency_key}})
        return {"status": "skipped_duplicate", "order_id": body.get("order_id")}

    order_id = body.get("order_id")
    if not order_id:
        raise OrderProcessingError("Message missing order_id")

    order: Order = orders_repo.get_by_id(order_id)
    if order is None:
        raise OrderProcessingError(f"Order {order_id} not found in database")

    if order.status != OrderStatus.PENDING:
        logger.info(
            "Order is not PENDING, nothing to process (likely already advanced or cancelled)",
            extra={"data": {"order_id": order.id, "status": order.status.value}},
        )
        return {"status": "skipped_not_pending", "order_id": order.id, "current_status": order.status.value}

    processing_steps = []

    # --- 2. Re-validate stock for every line item -------------------
    for item in order.items:
        product = products_repo.get_by_id(item.product_id)
        if product is None:
            order.status = OrderStatus.FAILED
            db.commit()
            _record_event(orders_repo, order, EventType.ORDER_FAILED, {"reason": "product_missing"}, idempotency_key)
            aws_sns.publish_order_event(EventType.ORDER_FAILED.value, order.id, order.order_number, "FAILED")
            raise OrderProcessingError(f"Product {item.product_id} missing for order {order.id}")

    # --- 3. PENDING -> PROCESSING ------------------------------------
    order.status = OrderStatus.PROCESSING
    db.commit()
    _record_event(
        orders_repo, order, EventType.ORDER_PROCESSING, {"step": "stock_validated"}, f"{idempotency_key}-processing"
    )
    aws_sns.publish_order_event(EventType.ORDER_PROCESSING.value, order.id, order.order_number, "PROCESSING")
    processing_steps.append("validated_stock")

    # --- 4. PROCESSING -> CONFIRMED ----------------------------------
    order.status = OrderStatus.CONFIRMED
    db.commit()
    db.refresh(order)
    _record_event(
        orders_repo, order, EventType.ORDER_CONFIRMED, {"step": "order_confirmed"}, f"{idempotency_key}-confirmed"
    )
    aws_sns.publish_order_event(EventType.ORDER_CONFIRMED.value, order.id, order.order_number, "CONFIRMED")
    processing_steps.append("confirmed_order")

    # --- 5. Mark the message processed (idempotency marker) ----------
    _record_event(
        orders_repo,
        order,
        EventType.ORDER_CONFIRMED,
        {"marker": "processing_complete"},
        f"processed-{idempotency_key}",
        status=EventStatus.PROCESSED,
    )

    # --- 6. Persist a processing-log audit file to S3 ----------------
    log_key = aws_s3.store_processing_log(
        order.order_number,
        {
            "order_id": order.id,
            "order_number": order.order_number,
            "sqs_message_id": message_id,
            "steps": processing_steps,
            "final_status": order.status.value,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    logger.info(
        "Order processed successfully",
        extra={"data": {"order_id": order.id, "order_number": order.order_number, "log_key": log_key}},
    )
    return {"status": "processed", "order_id": order.id, "final_status": order.status.value, "log_key": log_key}


def _record_event(
    orders_repo: OrderRepository,
    order: Order,
    event_type: EventType,
    event_data: Dict[str, Any],
    idempotency_key: str,
    status: EventStatus = EventStatus.PROCESSED,
) -> OrderEvent:
    return orders_repo.add_event(
        OrderEvent(
            order_id=order.id,
            event_type=event_type,
            event_data=event_data,
            status=status,
            idempotency_key=idempotency_key,
            processed_at=datetime.now(timezone.utc),
        )
    )
