"""Product catalog business logic."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate

logger = get_logger("services.product")


class ProductService:
    def __init__(self, db: Session):
        self.db = db
        self.products = ProductRepository(db)

    def list_products(self, skip: int = 0, limit: int = 50, include_inactive: bool = False):
        if include_inactive:
            return self.products.list_all(skip, limit)
        return self.products.list_active(skip, limit)

    def get_product(self, product_id: int) -> Product:
        product = self.products.get_by_id(product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        return product

    def create_product(self, payload: ProductCreate) -> Product:
        product = Product(**payload.model_dump())
        product = self.products.create(product)
        logger.info("Product created", extra={"data": {"product_id": product.id, "name": product.name}})
        return product

    def update_product(self, product_id: int, payload: ProductUpdate) -> Product:
        product = self.get_product(product_id)
        product = self.products.update(product, **payload.model_dump(exclude_unset=True))
        logger.info("Product updated", extra={"data": {"product_id": product.id}})
        return product

    def delete_product(self, product_id: int) -> None:
        product = self.get_product(product_id)
        self.products.delete(product)
        logger.info("Product deactivated", extra={"data": {"product_id": product_id}})
