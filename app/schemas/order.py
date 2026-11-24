from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus, PaymentStatus
from app.models.order_event import EventStatus, EventType


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    shipping_address: str = Field(min_length=5, max_length=500)
    items: List[OrderItemCreate] = Field(min_length=1)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    user_id: int
    total_amount: Decimal
    status: OrderStatus
    payment_status: PaymentStatus
    shipping_address: str
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemOut] = []


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    event_type: EventType
    event_data: Optional[dict] = None
    status: EventStatus
    created_at: datetime
    processed_at: Optional[datetime] = None


class DashboardStats(BaseModel):
    total_orders: int
    pending_orders: int
    processing_orders: int
    confirmed_orders: int
    completed_orders: int
    cancelled_orders: int
    total_revenue: Decimal
    recent_orders: List[OrderOut] = []
