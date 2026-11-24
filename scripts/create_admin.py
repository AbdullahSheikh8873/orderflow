"""
Create (or promote) an admin user.

Usage:
    python scripts/create_admin.py admin@orderflow.com "Admin User" SuperSecret123
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.security import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


def main() -> None:
    if len(sys.argv) != 4:
        print("Usage: python scripts/create_admin.py <email> <name> <password>")
        sys.exit(1)

    email, name, password = sys.argv[1], sys.argv[2], sys.argv[3]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user:
            user.role = UserRole.ADMIN
            user.is_active = True
            print(f"Promoted existing user {email} to ADMIN.")
        else:
            user = User(
                name=name,
                email=email.lower(),
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(user)
            print(f"Created new admin user {email}.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
