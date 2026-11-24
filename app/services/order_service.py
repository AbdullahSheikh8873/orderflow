"""
Core order-processing business logic.

Order creation follows the workflow described in the project spec:

    Customer -> FastAPI -> PostgreSQL (PENDING) -> ORDER_CREATED event -> SQS

The actual "processing" (stock validation done a second time, moving the
order to PROCESSING/CONFIRMED, publishing SNS notifications, writing S3
audit files) happens asynchronously in the Lambda order-processor
(lambda/order_processor/handler.py) once it picks the message up off SQS.
This service is only responsible for the synchronous, user-facing half of
the workflow plus admin-triggered status changes/cancellations.
"""
import random
import string
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.aws import s3 as aws_s3
from app.aws import sns as aws_sns
from app.aws import sqs as aws_sqs
from app.core.logging_config import get_logger
from app.models.order import ALLOWED_TRANSITIONS, Order, OrderStatus
from app.models.order_event import EventStatus, EventType, OrderEvent
from app.models.order_item import OrderItem
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import OrderCreate

logger = get_logger("services.order")


def _generate_order_number() -> str:
    year = datetime.now(timezone.utc).year
    suffix = "".join(random.choices(string.digits, k=6))
    return f"ORD-{year}-{suffix}"


class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderRepository(db)
        self.products = ProductRepository(db)

    # ------------------------------------------------------------------
    def create_order(self, user_id: int, payload: OrderCreate) -> Order:
        if not payload.items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must contain at least one item")

        line_items = []
        total = Decimal("0")
        for item in payload.items:
            product = self.products.get_by_id(item.product_id)
            if not product or not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {item.product_id} not found"
                )
            if product.stock_quantity < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for '{product.name}' (available: {product.stock_quantity})",
                )
            subtotal = Decimal(product.price) * item.quantity
            total += subtotal
            line_items.append((product, item.quantity, subtotal))

        order_number = _generate_order_number()
        order = Order(
            user_id=user_id,
            order_number=order_number,
            total_amount=total,
            status=OrderStatus.PENDING,
            shipping_address=payload.shipping_address,
        )
        order = self.orders.create(order)

        for product, quantity, subtotal in line_items:
            self.orders.add_item(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=product.price,
                    subtotal=subtotal,
                )
            )
            # Reserve stock immediately so two customers can't oversell the
            # same units while the order is queued for async processing.
            self.products.decrement_stock(product, quantity)
        self.orders.commit_refresh(order)

        # 1. Create the ORDER_CREATED audit event row.
        idempotency_key = f"create-{uuid.uuid4()}"
        event = self.orders.add_event(
            OrderEvent(
                order_id=order.id,
                event_type=EventType.ORDER_CREATED,
                event_data={"total_amount": str(total), "item_count": len(line_items)},
                status=EventStatus.PENDING,
                idempotency_key=idempotency_key,
            )
        )

        # 2. Store an initial invoice document in S3 (key only is persisted).
        invoice_key = aws_s3.store_invoice(
            order_number,
            {
                "order_number": order_number,
                "user_id": user_id,
                "total_amount": str(total),
                "shipping_address": payload.shipping_address,
                "items": [
                    {"product_id": p.id, "name": p.name, "quantity": q, "subtotal": str(s)}
                    for p, q, s in line_items
                ],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        # 3. Publish the order-processing message to SQS. The Lambda worker
        #    picks this up, validates stock again, advances the order to
        #    PROCESSING/CONFIRMED, publishes SNS notifications and writes the
        #    processing-log / order-event audit files to S3.
        message_id = aws_sqs.send_order_event(
            event_type=EventType.ORDER_CREATED.value,
            order_id=order.id,
            user_id=user_id,
            order_number=order_number,
            extra={"invoice_key": invoice_key, "idempotency_key": idempotency_key},
        )

        event.status = EventStatus.PUBLISHED if message_id or True else EventStatus.ERROR
        event.processed_at = datetime.now(timezone.utc)
        self.db.commit()

        logger.info(
            "Order created and queued for processing",
            extra={"data": {"order_id": order.id, "order_number": order_number, "sqs_message_id": message_id}},
        )
        return self.orders.get_by_id(order.id)

    # ------------------------------------------------------------------
    def get_order(self, order_id: int) -> Order:
        order = self.orders.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    def get_order_for_user(self, order_id: int, user_id: int) -> Order:
        order = self.get_order(order_id)
        if order.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this order")
        return order

    def list_for_user(self, user_id: int, skip: int = 0, limit: int = 50):
        return self.orders.list_for_user(user_id, skip, limit)

    def list_all(self, skip: int = 0, limit: int = 100, status_filter: Optional[OrderStatus] = None):
        return self.orders.list_all(skip, limit, status_filter)

    def list_events(self, order_id: int):
        self.get_order(order_id)
        return self.orders.list_events_for_order(order_id)

    def list_all_events(self, skip: int = 0, limit: int = 100):
        return self.orders.list_all_events(skip, limit)

    # ------------------------------------------------------------------
    def _transition(self, order: Order, new_status: OrderStatus) -> None:
        allowed = ALLOWED_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition order from {order.status.value} to {new_status.value}",
            )

    def update_status(self, order_id: int, new_status: OrderStatus) -> Order:
        order = self.get_order(order_id)
        self._transition(order, new_status)

        previous_status = order.status
        order.status = new_status
        self.db.commit()
        self.db.refresh(order)

        event_type_map = {
            OrderStatus.PROCESSING: EventType.ORDER_PROCESSING,
            OrderStatus.CONFIRMED: EventType.ORDER_CONFIRMED,
            OrderStatus.COMPLETED: EventType.ORDER_COMPLETED,
            OrderStatus.CANCELLED: EventType.ORDER_CANCELLED,
            OrderStatus.FAILED: EventType.ORDER_FAILED,
        }
        event_type = event_type_map.get(new_status, EventType.ORDER_PROCESSING)

        self.orders.add_event(
            OrderEvent(
                order_id=order.id,
                event_type=event_type,
                event_data={"previous_status": previous_status.value, "new_status": new_status.value},
                status=EventStatus.PROCESSED,
                idempotency_key=f"status-{order.id}-{new_status.value}-{uuid.uuid4()}",
                processed_at=datetime.now(timezone.utc),
            )
        )

        aws_sns.publish_order_event(
            event_type=event_type.value,
            order_id=order.id,
            order_number=order.order_number,
            status=new_status.value,
        )

        logger.info(
            "Order status updated",
            extra={"data": {"order_id": order.id, "from": previous_status.value, "to": new_status.value}},
        )
        return order

    def dashboard_stats(self) -> dict:
        return {
            "total_orders": self.orders.count_all(),
            "pending_orders": self.orders.count_by_status(OrderStatus.PENDING),
            "processing_orders": self.orders.count_by_status(OrderStatus.PROCESSING),
            "confirmed_orders": self.orders.count_by_status(OrderStatus.CONFIRMED),
            "completed_orders": self.orders.count_by_status(OrderStatus.COMPLETED),
            "cancelled_orders": self.orders.count_by_status(OrderStatus.CANCELLED),
            "total_revenue": self.orders.total_revenue(),
            "recent_orders": self.orders.recent(5),
        }

    def cancel_order(self, order_id: int, user_id: Optional[int] = None) -> Order:
        order = self.get_order(order_id)
        if user_id is not None and order.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to cancel this order")

        # Restock reserved items when a pending order is cancelled.
        if order.status == OrderStatus.PENDING:
            for item in order.items:
                product = self.products.get_by_id(item.product_id)
                if product:
                    product.stock_quantity += item.quantity
            self.db.commit()

        return self.update_status(order_id, OrderStatus.CANCELLED)
