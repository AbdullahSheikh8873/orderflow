"""
Seed a handful of demo products so the storefront isn't empty on a fresh
database. Safe to re-run -- it skips products that already exist by name.

Usage:
    python scripts/seed_products.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal  # noqa: E402
from app.models.product import Product  # noqa: E402

DEMO_PRODUCTS = [
    {"name": "Wireless Mechanical Keyboard", "description": "Hot-swappable switches, USB-C, 75% layout.",
     "price": 89.99, "stock_quantity": 40, "image_url": None},
    {"name": "27\" 4K Monitor", "description": "IPS panel, 60Hz, USB-C with 65W power delivery.",
     "price": 329.00, "stock_quantity": 15, "image_url": None},
    {"name": "Noise Cancelling Headphones", "description": "Over-ear, 30-hour battery, active noise cancellation.",
     "price": 199.50, "stock_quantity": 60, "image_url": None},
    {"name": "Ergonomic Office Chair", "description": "Adjustable lumbar support and armrests.",
     "price": 259.00, "stock_quantity": 10, "image_url": None},
    {"name": "Portable SSD 1TB", "description": "USB 3.2 Gen 2, up to 1050MB/s read speeds.",
     "price": 109.99, "stock_quantity": 75, "image_url": None},
    {"name": "Standing Desk Converter", "description": "Sit-stand desktop riser, gas-spring assisted.",
     "price": 179.00, "stock_quantity": 20, "image_url": None},
]


def main() -> None:
    db = SessionLocal()
    try:
        created = 0
        for data in DEMO_PRODUCTS:
            exists = db.query(Product).filter(Product.name == data["name"]).first()
            if exists:
                continue
            db.add(Product(**data))
            created += 1
        db.commit()
        print(f"Seeded {created} new product(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
