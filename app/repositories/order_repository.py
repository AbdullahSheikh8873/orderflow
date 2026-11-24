"""Data-access layer for Order, OrderItem and OrderEvent records."""
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderStatus
from app.models.order_event import OrderEvent
from app.models.order_item import OrderItem


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Orders -----------------------------------------------------
    def get_by_id(self, order_id: int) -> Optional[Order]:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.events))
        )
        return self.db.scalar(stmt)

    def get_by_order_number(self, order_number: str) -> Optional[Order]:
        stmt = select(Order).where(Order.order_number == order_number)
        return self.db.scalar(stmt)

    def list_for_user(self, user_id: int, skip: int = 0, limit: int = 50) -> Sequence[Order]:
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def list_all(self, skip: int = 0, limit: int = 100, status: Optional[OrderStatus] = None) -> Sequence[Order]:
        stmt = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
        if status is not None:
            stmt = stmt.where(Order.status == status)
        stmt = stmt.offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def add_item(self, item: OrderItem) -> None:
        self.db.add(item)

    def commit_refresh(self, order: Order) -> Order:
        self.db.commit()
        self.db.refresh(order)
        return order

    # --- Dashboard / stats -------------------------------------------
    def count_by_status(self, status: OrderStatus) -> int:
        stmt = select(func.count()).select_from(Order).where(Order.status == status)
        return self.db.scalar(stmt) or 0

    def count_all(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Order)) or 0

    def total_revenue(self) -> float:
        stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.COMPLETED])
        )
        return float(self.db.scalar(stmt) or 0)

    def recent(self, limit: int = 5) -> Sequence[Order]:
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    # --- Order events --------------------------------------------------
    def add_event(self, event: OrderEvent) -> OrderEvent:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_event_by_idempotency_key(self, idempotency_key: str) -> Optional[OrderEvent]:
        stmt = select(OrderEvent).where(OrderEvent.idempotency_key == idempotency_key)
        return self.db.scalar(stmt)

    def list_events_for_order(self, order_id: int) -> Sequence[OrderEvent]:
        stmt = (
            select(OrderEvent)
            .where(OrderEvent.order_id == order_id)
            .order_by(OrderEvent.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def list_all_events(self, skip: int = 0, limit: int = 100) -> Sequence[OrderEvent]:
        stmt = select(OrderEvent).order_by(OrderEvent.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))
