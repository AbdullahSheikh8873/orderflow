from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.order import OrderStatus
from app.schemas.order import DashboardStats, OrderEventOut, OrderOut
from app.schemas.product import ProductOut
from app.schemas.user import UserOut
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db)):
    service = OrderService(db)
    return service.dashboard_stats()


@router.get("/orders", response_model=List[OrderOut])
def all_orders(
    skip: int = 0,
    limit: int = Query(100, le=500),
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    service = OrderService(db)
    return service.list_all(skip, limit, status_filter)


@router.get("/users", response_model=List[UserOut])
def all_users(skip: int = 0, limit: int = Query(100, le=500), db: Session = Depends(get_db)):
    return UserRepository(db).list_all(skip, limit)


@router.get("/products", response_model=List[ProductOut])
def all_products(skip: int = 0, limit: int = Query(100, le=500), db: Session = Depends(get_db)):
    service = ProductService(db)
    return service.list_products(skip, limit, include_inactive=True)


@router.get("/events", response_model=List[OrderEventOut])
def all_events(skip: int = 0, limit: int = Query(100, le=500), db: Session = Depends(get_db)):
    service = OrderService(db)
    return service.list_all_events(skip, limit)
