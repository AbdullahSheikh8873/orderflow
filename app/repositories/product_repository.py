"""Data-access layer for Product records."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Optional[Product]:
        return self.db.get(Product, product_id)

    def list_active(self, skip: int = 0, limit: int = 50):
        stmt = (
            select(Product)
            .where(Product.is_active.is_(True))
            .order_by(Product.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def list_all(self, skip: int = 0, limit: int = 100):
        stmt = select(Product).order_by(Product.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update(self, product: Product, **fields) -> Product:
        for key, value in fields.items():
            if value is not None:
                setattr(product, key, value)
        self.db.commit()
        self.db.refresh(product)
        return product

    def delete(self, product: Product) -> None:
        # Soft delete so historical order_items keep a valid FK reference.
        product.is_active = False
        self.db.commit()

    def decrement_stock(self, product: Product, quantity: int) -> None:
        product.stock_quantity = max(0, product.stock_quantity - quantity)
        self.db.commit()
