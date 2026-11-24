from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_active_user, require_admin
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderEventOut, OrderOut, OrderStatusUpdate
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = OrderService(db)
    return service.create_order(current_user.id, payload)


@router.get("", response_model=List[OrderOut])
def list_my_orders(
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = OrderService(db)
    return service.list_for_user(current_user.id, skip, limit)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = OrderService(db)
    if current_user.role == UserRole.ADMIN:
        return service.get_order(order_id)
    return service.get_order_for_user(order_id, current_user.id)


@router.get("/{order_id}/events", response_model=List[OrderEventOut])
def get_order_events(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = OrderService(db)
    if current_user.role != UserRole.ADMIN:
        service.get_order_for_user(order_id, current_user.id)
    return service.list_events(order_id)


@router.patch("/{order_id}/status", response_model=OrderOut, dependencies=[Depends(require_admin)])
def update_order_status(order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db)):
    service = OrderService(db)
    return service.update_status(order_id, payload.status)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = OrderService(db)
    user_id = None if current_user.role == UserRole.ADMIN else current_user.id
    return service.cancel_order(order_id, user_id)
