"""Data-access layer for User records. Keeps raw SQLAlchemy queries out of the service layer."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower())
        return self.db.scalar(stmt)

    def list_all(self, skip: int = 0, limit: int = 100):
        stmt = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
