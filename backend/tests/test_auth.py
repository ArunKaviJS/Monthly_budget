"""
test_auth.py — Accounts, login tokens (JWT), and per-user data isolation.

"alice" and "bob" are two different people using the same backend at the same
time; nothing one does may show up in, or change, the other's data.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from app import database
from app.main import app
from tests.conftest import client_for, signup


def _token_for(user_id: int, **overrides) -> str:
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    payload.update(overrides)
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════
# Sign up
# ═══════════════════════════════════════════════
def test_signup_returns_token_and_user_without_password(anon):
    r = anon.post("/api/auth/signup", json={"username": "Arun", "email": "arun@example.com", "password": "secret123"})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["username"] == "Arun"
    assert body["user"]["email"] == "arun@example.com"
    assert body["token"]
    assert "password" not in str(body).lower()


def test_password_is_stored_hashed_never_plain(anon):
    signup(anon, "arun", password="my-plain-password")
    doc = database.get_db().users.find_one({"username_lower": "arun"})
    assert "my-plain-password" not in str(doc)
    assert doc["password_hash"].startswith("scrypt$")


def test_username_must_be_unique_ignoring_case(anon):
    signup(anon, "Arun", "arun@example.com")
    r = anon.post("/api/auth/signup", json={"username": "ARUN", "email": "other@example.com", "password": "secret123"})
    assert r.status_code == 409
    assert "username" in r.json()["detail"].lower()


def test_email_must_be_unique_ignoring_case(anon):
    signup(anon, "arun", "Arun@Example.com")
    r = anon.post("/api/auth/signup", json={"username": "someone", "email": "arun@example.COM", "password": "secret123"})
    assert r.status_code == 409
    assert "email" in r.json()["detail"].lower()


def test_duplicate_signup_does_not_create_a_second_account(anon):
    signup(anon, "arun", "arun@example.com")
    anon.post("/api/auth/signup", json={"username": "arun", "email": "arun@example.com", "password": "secret123"})
    assert database.get_db().users.count_documents({}) == 1


def test_database_enforces_uniqueness_with_unique_indexes(anon):
    signup(anon, "arun")
    info = database.get_db().users.index_information()
    unique_fields = {k for idx in info.values() if idx.get("unique") for k, _ in idx["key"]}
    assert {"username_lower", "email_lower"} <= unique_fields


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "ab", "email": "a@b.co", "password": "secret123"},  # too short
        {"username": "has space", "email": "a@b.co", "password": "secret123"},
        {"username": "x" * 25, "email": "a@b.co", "password": "secret123"},  # too long
        {"username": "arun", "email": "not-an-email", "password": "secret123"},
        {"username": "arun", "email": "a@b", "password": "secret123"},
        {"username": "arun", "email": "a@b.co", "password": "12345"},  # too short
        {"username": "arun", "email": "a@b.co"},  # missing password
    ],
)
def test_signup_rejects_invalid_input(anon, payload):
    assert anon.post("/api/auth/signup", json=payload).status_code == 422


# ═══════════════════════════════════════════════
# Login
# ═══════════════════════════════════════════════
def test_login_with_username_or_email(anon):
    signup(anon, "Arun", "arun@example.com", "secret123")
    by_name = anon.post("/api/auth/login", json={"identifier": "arun", "password": "secret123"})
    by_email = anon.post("/api/auth/login", json={"identifier": "ARUN@example.com", "password": "secret123"})
    assert by_name.status_code == 200 and by_email.status_code == 200
    assert by_name.json()["user"]["id"] == by_email.json()["user"]["id"]
    assert by_name.json()["token"]


def test_login_wrong_password_and_unknown_user_look_identical(anon):
    signup(anon, "arun", password="secret123")
    wrong = anon.post("/api/auth/login", json={"identifier": "arun", "password": "nope-nope"})
    unknown = anon.post("/api/auth/login", json={"identifier": "ghost", "password": "secret123"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # no hint about which usernames exist


# ═══════════════════════════════════════════════
# Token verification / refresh on app start
# ═══════════════════════════════════════════════
def test_refresh_verifies_token_and_returns_user_with_a_fresh_working_token(anon):
    data = signup(anon, "arun", "arun@example.com")
    r = anon.post("/api/auth/refresh", headers=_bearer(data["token"]))
    assert r.status_code == 200
    assert r.json()["user"] == data["user"]

    # the new token is itself valid
    r2 = anon.post("/api/auth/refresh", headers=_bearer(r.json()["token"]))
    assert r2.status_code == 200


def test_me_returns_the_user(alice):
    r = alice.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


def test_missing_token_is_rejected(anon):
    assert anon.post("/api/auth/refresh").status_code == 401
    assert anon.get("/api/auth/me").status_code == 401


def test_garbage_token_is_rejected(anon):
    assert anon.post("/api/auth/refresh", headers=_bearer("not.a.jwt")).status_code == 401


def test_expired_token_is_rejected(anon):
    data = signup(anon, "arun")
    expired = _token_for(data["user"]["id"], exp=datetime.now(timezone.utc) - timedelta(seconds=5))
    assert anon.post("/api/auth/refresh", headers=_bearer(expired)).status_code == 401


def test_token_signed_with_another_secret_is_rejected(anon):
    data = signup(anon, "arun")
    forged = jwt.encode({"sub": str(data["user"]["id"]), "exp": datetime.now(timezone.utc) + timedelta(days=1)},
                        "some-other-secret", algorithm="HS256")
    assert anon.post("/api/auth/refresh", headers=_bearer(forged)).status_code == 401


def test_token_without_expiry_is_rejected(anon):
    data = signup(anon, "arun")
    no_exp = jwt.encode({"sub": str(data["user"]["id"])}, os.environ["JWT_SECRET"], algorithm="HS256")
    assert anon.post("/api/auth/refresh", headers=_bearer(no_exp)).status_code == 401


def test_token_of_a_deleted_user_is_rejected(anon):
    data = signup(anon, "arun")
    database.get_db().users.delete_one({"_id": data["user"]["id"]})
    assert anon.post("/api/auth/refresh", headers=_bearer(data["token"])).status_code == 401


# ═══════════════════════════════════════════════
# Every data endpoint needs a signed-in user
# ═══════════════════════════════════════════════
PROTECTED = [
    ("get", "/api/books"),
    ("post", "/api/books"),
    ("get", "/api/books/active"),
    ("patch", "/api/books/1"),
    ("delete", "/api/books/1"),
    ("get", "/api/expenses"),
    ("post", "/api/expenses"),
    ("get", "/api/expenses/1"),
    ("patch", "/api/expenses/1"),
    ("delete", "/api/expenses/1"),
    ("delete", "/api/expenses"),
    ("get", "/api/summary"),
    ("get", "/api/summary/daily"),
    ("get", "/api/budgets"),
    ("post", "/api/budgets"),
    ("get", "/api/keywords"),
    ("delete", "/api/keywords"),
    ("delete", "/api/keywords/tea"),
    ("post", "/api/preview"),
    ("get", "/api/export/json"),
    ("get", "/api/export/csv"),
]


@pytest.mark.parametrize("method,path", PROTECTED)
def test_data_endpoints_require_sign_in(anon, method, path):
    r = getattr(anon, method)(path)
    assert r.status_code == 401, f"{method.upper()} {path} answered {r.status_code}"


def test_public_endpoints_need_no_sign_in(anon):
    assert anon.get("/api/health").status_code == 200
    assert anon.get("/api/intents").status_code == 200


# ═══════════════════════════════════════════════
# Two people at once: their data never mixes
# ═══════════════════════════════════════════════
def _seed(c: TestClient, book: str, *texts: str) -> dict:
    b = c.post("/api/books", json={"name": book}).json()
    for t in texts:
        assert c.post("/api/expenses", json={"raw_text": t}).status_code == 201
    return b


def test_each_user_only_sees_their_own_books_and_expenses(alice, bob):
    _seed(alice, "Alice Book", "tea 20", "petrol 500")
    _seed(bob, "Bob Book", "movie ticket 250")

    a_books, b_books = alice.get("/api/books").json(), bob.get("/api/books").json()
    assert [b["name"] for b in a_books] == ["Alice Book"]
    assert [b["name"] for b in b_books] == ["Bob Book"]

    assert len(alice.get("/api/expenses").json()) == 2
    assert [e["description"] for e in bob.get("/api/expenses").json()] == ["Movie ticket"]


def test_same_book_name_for_two_users_does_not_collide(alice, bob):
    a = _seed(alice, "September", "tea 20")
    b = _seed(bob, "September", "tea 99")
    assert a["id"] != b["id"]
    assert float(alice.get("/api/books").json()[0]["total"]) == 20.0
    assert float(bob.get("/api/books").json()[0]["total"]) == 99.0


def test_each_user_has_their_own_active_book(alice, bob):
    _seed(alice, "A1", "tea 20")
    _seed(bob, "B1", "tea 20")
    # Bob creating/activating books must not deactivate Alice's
    bob.post("/api/books", json={"name": "B2"})
    assert alice.get("/api/books/active").json()["name"] == "A1"
    assert bob.get("/api/books/active").json()["name"] == "B2"


def test_expenses_go_into_the_callers_own_active_book(alice, bob):
    a = alice.post("/api/books", json={"name": "A"}).json()
    b = bob.post("/api/books", json={"name": "B"}).json()
    assert alice.post("/api/expenses", json={"raw_text": "tea 20"}).json()["book_id"] == a["id"]
    assert bob.post("/api/expenses", json={"raw_text": "tea 20"}).json()["book_id"] == b["id"]


def test_user_without_a_book_cannot_use_someone_elses(alice, bob):
    _seed(alice, "Alice Book", "tea 20")
    # Bob has never made a book, so he must not be able to add to Alice's
    assert bob.post("/api/expenses", json={"raw_text": "tea 20"}).status_code == 409
    assert bob.get("/api/books/active").status_code == 404


def test_cannot_read_edit_or_delete_another_users_expense(alice, bob):
    _seed(alice, "A", "tea 20")
    eid = alice.get("/api/expenses").json()[0]["id"]

    assert bob.get(f"/api/expenses/{eid}").status_code == 404
    assert bob.patch(f"/api/expenses/{eid}", json={"amount": 1}).status_code == 404
    assert bob.delete(f"/api/expenses/{eid}").status_code == 404

    mine = alice.get(f"/api/expenses/{eid}").json()
    assert mine["amount"] == "20.00"  # untouched


def test_cannot_rename_activate_or_delete_another_users_book(alice, bob):
    a = _seed(alice, "Alice Book", "tea 20")
    assert bob.patch(f"/api/books/{a['id']}", json={"name": "hacked"}).status_code == 404
    assert bob.patch(f"/api/books/{a['id']}", json={"is_active": True}).status_code == 404
    assert bob.delete(f"/api/books/{a['id']}").status_code == 404
    assert alice.get("/api/books").json()[0]["name"] == "Alice Book"
    assert len(alice.get("/api/expenses").json()) == 1


def test_cannot_filter_by_another_users_book_id(alice, bob):
    a = _seed(alice, "A", "tea 20")
    assert bob.get("/api/expenses", params={"book_id": a["id"]}).json() == []
    s = bob.get("/api/summary", params={"book_id": a["id"]}).json()
    assert s["count"] == 0 and float(s["total"]) == 0.0


def test_delete_all_and_delete_book_only_affect_the_caller(alice, bob):
    a = _seed(alice, "A", "tea 20", "petrol 500")
    _seed(bob, "B", "movie ticket 250")

    assert bob.delete("/api/expenses").json()["deleted"] == 1
    assert len(alice.get("/api/expenses").json()) == 2

    assert alice.delete(f"/api/books/{a['id']}").json()["deleted_expenses"] == 2
    assert len(bob.get("/api/books").json()) == 1  # Bob's book still exists


def test_summary_and_daily_summary_are_per_user(alice, bob):
    _seed(alice, "A", "tea 20", "petrol 500")
    _seed(bob, "B", "movie ticket 250")
    assert float(alice.get("/api/summary").json()["total"]) == 520.0
    assert float(bob.get("/api/summary").json()["total"]) == 250.0
    assert sum(float(d["total"]) for d in alice.get("/api/summary/daily").json()["days"]) == 520.0


def test_budgets_are_per_user(alice, bob):
    alice.post("/api/budgets", json={"intent": "food", "monthly_limit": 3000})
    assert [b["intent"] for b in alice.get("/api/budgets").json()] == ["food"]
    assert bob.get("/api/budgets").json() == []

    bob.post("/api/budgets", json={"intent": "food", "monthly_limit": 100})
    assert float(alice.get("/api/budgets").json()[0]["monthly_limit"]) == 3000.0
    assert float(bob.get("/api/budgets").json()[0]["monthly_limit"]) == 100.0


def test_learned_keywords_are_per_user(alice, bob):
    _seed(alice, "A", "zorbnax 40")
    eid = alice.get("/api/expenses").json()[0]["id"]
    alice.patch(f"/api/expenses/{eid}", json={"intent": "medical"})

    assert alice.get("/api/keywords").json() != []
    assert bob.get("/api/keywords").json() == []

    # Alice's lesson applies to Alice only
    _seed(bob, "B", "zorbnax 40")
    assert bob.get("/api/expenses").json()[0]["intent"] == "others"
    assert alice.post("/api/expenses", json={"raw_text": "zorbnax 40"}).json()["intent"] == "medical"

    # and Bob clearing keywords can't wipe Alice's
    bob.delete("/api/keywords")
    assert alice.get("/api/keywords").json() != []


def test_export_only_contains_the_callers_data(alice, bob):
    _seed(alice, "A", "tea 20")
    _seed(bob, "B", "petrol 500")
    rows = alice.get("/api/export/json").json()
    assert [r["description"] for r in rows] == ["Tea"]
    assert "Petrol" not in alice.get("/api/export/csv").text


def test_ids_are_unique_across_users(alice, bob):
    _seed(alice, "A", "tea 20")
    _seed(bob, "B", "tea 20")
    a_id = alice.get("/api/expenses").json()[0]["id"]
    b_id = bob.get("/api/expenses").json()[0]["id"]
    assert a_id != b_id


# ═══════════════════════════════════════════════
# Deleting a book really removes the data
# ═══════════════════════════════════════════════
def test_deleting_a_book_removes_its_documents_from_the_database(alice):
    b = _seed(alice, "Gone", "tea 20", "petrol 500")
    other = _seed(alice, "Kept", "movie ticket 250")

    alice.delete(f"/api/books/{b['id']}")

    db = database.get_db()
    assert db.books.count_documents({"_id": b["id"]}) == 0
    assert db.expenses.count_documents({"book_id": b["id"]}) == 0
    assert db.expenses.count_documents({"book_id": other["id"]}) == 1  # other book untouched


# ═══════════════════════════════════════════════
# Database trouble
# ═══════════════════════════════════════════════
def test_database_outage_returns_503_not_a_crash(alice):
    def broken():
        raise ServerSelectionTimeoutError("cluster unreachable")

    app.dependency_overrides[database.get_db] = broken
    try:
        r = alice.get("/api/books")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert "unavailable" in r.json()["detail"].lower()


def test_health_works_even_when_the_database_is_down(anon):
    def broken():
        raise ServerSelectionTimeoutError("cluster unreachable")

    app.dependency_overrides[database.get_db] = broken
    try:
        assert anon.get("/api/health").status_code == 200
    finally:
        app.dependency_overrides.clear()
