"""Polls the configured PostgreSQL database until it accepts connections."""
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402


def main(timeout_seconds: int = 60) -> None:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database is ready.")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"Waiting for database... ({exc})")
            time.sleep(2)
    print("Timed out waiting for database.")
    sys.exit(1)


if __name__ == "__main__":
    main()
