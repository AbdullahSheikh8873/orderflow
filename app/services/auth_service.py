"""Registration / login business logic."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserLogin

logger = get_logger("services.auth")


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register(self, payload: UserCreate) -> User:
        existing = self.users.get_by_email(payload.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        user = User(
            name=payload.name,
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            role=UserRole.CUSTOMER,
        )
        user = self.users.create(user)
        logger.info("User registered", extra={"data": {"user_id": user.id, "email": user.email}})
        return user

    def authenticate(self, payload: UserLogin) -> User:
        user = self.users.get_by_email(payload.email)
        unauthorized = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
        if not user or not verify_password(payload.password, user.password_hash):
            raise unauthorized
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
        logger.info("User logged in", extra={"data": {"user_id": user.id}})
        return user

    @staticmethod
    def issue_token(user: User) -> str:
        return create_access_token(subject=str(user.id), extra_claims={"role": user.role.value})
