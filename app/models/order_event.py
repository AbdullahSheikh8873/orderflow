import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EventType(str, enum.Enum):
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_PROCESSING = "ORDER_PROCESSING"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    ORDER_COMPLETED = "ORDER_COMPLETED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_FAILED = "ORDER_FAILED"


class EventStatus(str, enum.Enum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    PROCESSED = "PROCESSED"
    ERROR = "ERROR"


class OrderEvent(Base):
    """
    Audit / event-sourcing table. A row is written every time something
    happens to an order (created, queued, picked up by the Lambda worker,
    status changed, notification published, etc). This is the same data
    that gets mirrored into S3 as a JSON audit file.
    """

    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType, name="event_type"), nullable=False, index=True)
    event_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status"), default=EventStatus.PENDING, nullable=False
    )
    # Idempotency key: typically the SQS MessageId, used so the Lambda
    # worker never double-processes the same message.
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=True, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", back_populates="events")

    def __repr__(self) -> str:
        return f"<OrderEvent id={self.id} order_id={self.order_id} type={self.event_type}>"
