"""
conftest.py — shared test setup.

The environment is forced to an in-memory fake MongoDB (mongomock) BEFORE the
app is imported, so the tests can never touch the real Atlas database, even
though backend/.env contains its connection string (load_dotenv does not
override variables that are already set).
"""

import os
import sys

os.environ["MONGO_URI"] = "mongomock://tests"
os.environ["MONGO_DB"] = "budget_test"
os.environ["JWT_SECRET"] = "test-secret-not-used-anywhere-else"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import database  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_database():
    """Every test starts with an empty database."""
    database.reset_for_tests()
    app.dependency_overrides.clear()
    yield


def signup(client: TestClient, username: str, email: str = None, password: str = "secret123"):
    email = email or f"{username.lower()}@example.com"
    r = client.post("/api/auth/signup", json={"username": username, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


def client_for(username: str, email: str = None, password: str = "secret123") -> TestClient:
    """A TestClient signed in as a brand-new user."""
    anon = TestClient(app)
    data = signup(anon, username, email, password)
    return TestClient(app, headers={"Authorization": f"Bearer {data['token']}"})


@pytest.fixture
def alice() -> TestClient:
    return client_for("alice")


@pytest.fixture
def bob() -> TestClient:
    return client_for("bob")


@pytest.fixture
def anon() -> TestClient:
    return TestClient(app)
