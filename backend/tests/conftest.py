"""
pytest configuration — in-memory SQLite fixtures shared across all tests.

Run from the backend/ directory:
    pytest tests/
"""

import os
import sys
import pytest

# Ensure backend root is on the path so imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Point at an in-memory SQLite DB before any app code imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database.models import Base
from database.connection import get_db
from api.main import app

# ── In-memory engine shared by the test session ────────────────────────────────

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once for the entire test session."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture()
def db():
    """
    Provide a database session that is rolled back after each test,
    keeping tests fully isolated from each other.
    """
    connection = TEST_ENGINE.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    """
    FastAPI TestClient with the test DB session injected via dependency override.
    """
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ── Auth helpers ───────────────────────────────────────────────────────────────

def register_and_login(client, email="test@example.com", password="Test1234!", name="Test User"):
    """Register a user and return the access token."""
    client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "full_name": name,
    })
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    if resp.status_code == 200:
        return resp.json().get("access_token")
    # Try alternate field name
    data = resp.json()
    return data.get("access_token") or data.get("token")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
