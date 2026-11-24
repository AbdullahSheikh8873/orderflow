import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force AWS calls off before any app module reads settings, so tests never
# hit real AWS credentials/endpoints even if a developer's shell has
# AWS_DISABLED=false set from a previous local session.
os.environ["AWS_DISABLED"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def _fresh_schema():
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    return TestClient(app)


def register_user(client, email="customer@example.com", name="Test Customer", password="SuperSecret123"):
    resp = client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def customer_token(client):
    data = register_user(client)
    return data["access_token"]


@pytest.fixture()
def admin_token(client, db_session):
    data = register_user(client, email="admin@example.com", name="Admin User")
    from app.models.user import User, UserRole

    user = db_session.query(User).filter(User.email == "admin@example.com").first()
    user.role = UserRole.ADMIN
    db_session.commit()

    # Re-login to get a fresh token whose "role" claim reflects the promotion.
    resp = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "SuperSecret123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]
