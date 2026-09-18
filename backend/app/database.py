"""
database.py — MongoDB connection.

Production / development: MongoDB Atlas via MONGO_URI (database MONGO_DB).
Tests: MONGO_URI=mongomock://... gives an in-memory fake, so tests never
touch a real database.

Every document except `users` carries a `user_id`, and every query filters on
it — that is what keeps two people's books, expenses, budgets and learned
keywords completely separate.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Local development reads backend/.env; in production the variables come from
# the host (Vercel). load_dotenv never overrides variables that are already set.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from pymongo import ASCENDING, ReturnDocument  # noqa: E402

_client = None
_indexes_ready = False


def _connect():
    uri = os.environ.get("MONGO_URI")
    if not uri:
        raise RuntimeError("MONGO_URI is not set")
    if uri.startswith("mongomock://"):
        import mongomock

        return mongomock.MongoClient()

    from pymongo import MongoClient

    return MongoClient(uri, serverSelectionTimeoutMS=8000)


def get_db():
    """FastAPI dependency / helper — returns the application's database."""
    global _client, _indexes_ready
    if _client is None:
        _client = _connect()
    db = _client[os.environ.get("MONGO_DB", "budget")]
    if not _indexes_ready:
        _ensure_indexes(db)
        _indexes_ready = True
    return db


def _ensure_indexes(db) -> None:
    """Uniqueness rules live in the database, so they hold even when two
    requests race each other."""
    db.users.create_index([("username_lower", ASCENDING)], unique=True)
    db.users.create_index([("email_lower", ASCENDING)], unique=True)
    db.books.create_index([("user_id", ASCENDING), ("is_active", ASCENDING)])
    db.expenses.create_index([("user_id", ASCENDING), ("book_id", ASCENDING), ("spent_on", ASCENDING)])
    db.debts.create_index([("user_id", ASCENDING), ("book_id", ASCENDING), ("status", ASCENDING)])
    db.budgets.create_index([("user_id", ASCENDING), ("intent", ASCENDING)], unique=True)
    db.learned_keywords.create_index([("user_id", ASCENDING), ("keyword", ASCENDING)], unique=True)


def next_id(db, name: str) -> int:
    """Auto-incrementing integer ids (the app uses numeric ids)."""
    doc = db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc["seq"])


def reset_for_tests() -> None:
    """Wipe the in-memory test database (mongomock only)."""
    global _client, _indexes_ready
    if _client is not None and os.environ.get("MONGO_URI", "").startswith("mongomock://"):
        _client.drop_database(os.environ.get("MONGO_DB", "budget"))
    _indexes_ready = False
