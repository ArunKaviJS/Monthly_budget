"""
crud.py — Database operations (MongoDB).

Every function takes the signed-in user's id and filters on it, so one
person's books, expenses, budgets and learned keywords can never leak into
another person's account.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from bson.decimal128 import Decimal128
from dateutil.parser import parse as parse_date
from pymongo.errors import DuplicateKeyError

from . import schemas
from .database import next_id
from .intent_config import INTENTS
from .intent_engine import (
    parse_expense,
    extract_learnable_tokens,
    normalize,
    extract_amount,
    classify,
    build_description,
    _get_today,
)

_TWO_PLACES = Decimal("0.01")


# ═══════════════════════════════════════════════
# Small helpers
# ═══════════════════════════════════════════════
def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _dec(value) -> Decimal:
    if isinstance(value, Decimal128):
        return value.to_decimal()
    return Decimal(str(value))


def _d128(value) -> Decimal128:
    return Decimal128(_dec(value).quantize(_TWO_PLACES))


def _month_range(month: Optional[str]):
    """'YYYY-MM' -> (first day, first day of next month) as ISO strings, or None."""
    try:
        year, mon = (month or "").split("-")
        year, mon = int(year), int(mon)
        start = date(year, mon, 1)
        end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    except (ValueError, TypeError):
        return None
    return start.isoformat(), end.isoformat()


# ═══════════════════════════════════════════════
# Users
# ═══════════════════════════════════════════════
class DuplicateUser(Exception):
    """Raised when a username or email is already registered."""

    def __init__(self, field: str):
        super().__init__(field)
        self.field = field


def user_out(doc: dict) -> dict:
    return {"id": doc["_id"], "username": doc["username"], "email": doc["email"]}


def create_user(db, username: str, email: str, password_hash: str) -> dict:
    if db.users.find_one({"username_lower": username.lower()}):
        raise DuplicateUser("username")
    if db.users.find_one({"email_lower": email.lower()}):
        raise DuplicateUser("email")

    doc = {
        "_id": next_id(db, "users"),
        "username": username,
        "username_lower": username.lower(),
        "email": email,
        "email_lower": email.lower(),
        "password_hash": password_hash,
        "created_at": _now(),
    }
    try:
        db.users.insert_one(doc)
    except DuplicateKeyError:
        # Two sign-ups raced each other; the unique index caught it.
        raise DuplicateUser("username or email")
    return doc


def find_user_for_login(db, identifier: str) -> Optional[dict]:
    key = identifier.strip().lower()
    return db.users.find_one({"$or": [{"username_lower": key}, {"email_lower": key}]})


# ═══════════════════════════════════════════════
# Learned keywords (per user)
# ═══════════════════════════════════════════════
def load_learned_keywords(db, user_id: int) -> Dict[str, str]:
    return {k["keyword"]: k["intent"] for k in db.learned_keywords.find({"user_id": user_id})}


def save_learned_keywords(db, user_id: int, tokens: List[str], intent: str) -> None:
    for token in tokens:
        db.learned_keywords.update_one(
            {"user_id": user_id, "keyword": token},
            {"$set": {"intent": intent}, "$inc": {"hits": 1}},
            upsert=True,
        )


def get_keywords(db, user_id: int) -> List[dict]:
    docs = db.learned_keywords.find({"user_id": user_id}).sort([("intent", 1), ("hits", -1)])
    return [{"keyword": d["keyword"], "intent": d["intent"], "hits": d["hits"]} for d in docs]


def delete_keyword(db, user_id: int, keyword: str) -> bool:
    return db.learned_keywords.delete_one({"user_id": user_id, "keyword": keyword}).deleted_count > 0


def clear_all_keywords(db, user_id: int) -> int:
    return db.learned_keywords.delete_many({"user_id": user_id}).deleted_count


# ═══════════════════════════════════════════════
# Books
# ═══════════════════════════════════════════════
def _book_totals(db, user_id: int) -> Dict[int, tuple]:
    totals: Dict[int, tuple] = {}
    for e in db.expenses.find({"user_id": user_id}, {"book_id": 1, "amount": 1}):
        total, count = totals.get(e["book_id"], (Decimal("0"), 0))
        totals[e["book_id"]] = (total + _dec(e["amount"]), count + 1)
    return totals


def _pending_debts(db, user_id: int) -> Dict[int, int]:
    """book_id -> number of debts still waiting to be returned."""
    counts: Dict[int, int] = {}
    for d in db.debts.find({"user_id": user_id, "status": "pending"}, {"book_id": 1}):
        counts[d["book_id"]] = counts.get(d["book_id"], 0) + 1
    return counts


def _book_out(doc: dict, totals: Dict[int, tuple], pending: Optional[Dict[int, int]] = None) -> dict:
    total, count = totals.get(doc["_id"], (Decimal("0"), 0))
    return {
        "id": doc["_id"],
        "name": doc["name"],
        "is_active": bool(doc.get("is_active")),
        "created_at": doc.get("created_at"),
        "total": total,
        "count": count,
        "pending_debts": (pending or {}).get(doc["_id"], 0),
    }


def create_book(db, user_id: int, name: str) -> dict:
    """Create a new book and make it this user's active one."""
    db.books.update_many({"user_id": user_id}, {"$set": {"is_active": False}})
    doc = {
        "_id": next_id(db, "books"),
        "user_id": user_id,
        "name": name,
        "is_active": True,
        "created_at": _now(),
    }
    db.books.insert_one(doc)
    return _book_out(doc, {})


def get_books(db, user_id: int) -> List[dict]:
    totals = _book_totals(db, user_id)
    pending = _pending_debts(db, user_id)
    docs = db.books.find({"user_id": user_id}).sort([("_id", -1)])
    return [_book_out(d, totals, pending) for d in docs]


def get_book_by_id(db, user_id: int, book_id: int) -> Optional[dict]:
    doc = db.books.find_one({"_id": book_id, "user_id": user_id})
    return _book_out(doc, _book_totals(db, user_id), _pending_debts(db, user_id)) if doc else None


def get_active_book(db, user_id: int) -> Optional[dict]:
    doc = db.books.find_one({"user_id": user_id, "is_active": True})
    return _book_out(doc, _book_totals(db, user_id), _pending_debts(db, user_id)) if doc else None


def update_book(db, user_id: int, book_id: int, update: schemas.BookUpdate) -> Optional[dict]:
    doc = db.books.find_one({"_id": book_id, "user_id": user_id})
    if not doc:
        return None
    changes: dict = {}
    if update.name is not None:
        changes["name"] = update.name
    if update.is_active:
        db.books.update_many({"user_id": user_id}, {"$set": {"is_active": False}})
        changes["is_active"] = True
    if changes:
        db.books.update_one({"_id": book_id, "user_id": user_id}, {"$set": changes})
    return get_book_by_id(db, user_id, book_id)


def delete_book(db, user_id: int, book_id: int) -> Optional[int]:
    """Permanently delete a book and every expense in it (nothing is kept).
    Returns the number of expenses removed, or None if the book isn't this
    user's. If it was the active book, the newest remaining book takes over."""
    doc = db.books.find_one({"_id": book_id, "user_id": user_id})
    if not doc:
        return None
    deleted = db.expenses.delete_many({"user_id": user_id, "book_id": book_id}).deleted_count
    db.debts.delete_many({"user_id": user_id, "book_id": book_id})
    db.books.delete_one({"_id": book_id, "user_id": user_id})

    if doc.get("is_active"):
        fallback = db.books.find_one({"user_id": user_id}, sort=[("_id", -1)])
        if fallback:
            db.books.update_one({"_id": fallback["_id"]}, {"$set": {"is_active": True}})
    return deleted


# ═══════════════════════════════════════════════
# Expenses
# ═══════════════════════════════════════════════
def _expense_out(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "book_id": doc.get("book_id"),
        "raw_text": doc["raw_text"],
        "description": doc["description"],
        "amount": _dec(doc["amount"]).quantize(_TWO_PLACES),
        "intent": doc["intent"],
        "confidence": float(doc["confidence"]) if doc.get("confidence") is not None else None,
        "spent_on": doc["spent_on"],
        "created_at": doc.get("created_at"),
        "is_manual_override": bool(doc.get("is_manual_override")),
    }


def create_expense_from_text(
    db, user_id: int, raw_text: str, book_id: int, intent: Optional[str] = None
) -> dict:
    """Parse raw_text (amount, description, date) and file it in the given book.
    A category the user picked is used as-is instead of the auto-detected one."""
    learned = load_learned_keywords(db, user_id)
    result = parse_expense(raw_text, learned_keywords=learned)

    doc = {
        "_id": next_id(db, "expenses"),
        "user_id": user_id,
        "book_id": book_id,
        "raw_text": raw_text,
        "description": result.description,
        "amount": _d128(result.amount),
        "intent": intent or result.intent,
        "confidence": 1.0 if intent else float(result.confidence),
        "spent_on": result.spent_on.isoformat(),
        "created_at": _now(),
        "is_manual_override": bool(intent),
    }
    db.expenses.insert_one(doc)
    return _expense_out(doc)


def create_expense_manual(
    db,
    user_id: int,
    amount: Decimal,
    intent: str,
    description: str,
    spent_on: date,
    book_id: int,
) -> dict:
    doc = {
        "_id": next_id(db, "expenses"),
        "user_id": user_id,
        "book_id": book_id,
        "raw_text": f"{description} {amount}",
        "description": description,
        "amount": _d128(amount),
        "intent": intent,
        "confidence": 1.0,
        "spent_on": spent_on.isoformat(),
        "created_at": _now(),
        "is_manual_override": True,
    }
    db.expenses.insert_one(doc)
    return _expense_out(doc)


def get_expenses(
    db,
    user_id: int,
    month: Optional[str] = None,
    intent: Optional[str] = None,
    book_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[dict]:
    flt: dict = {"user_id": user_id}
    if month:
        rng = _month_range(month)
        if rng:
            flt["spent_on"] = {"$gte": rng[0], "$lt": rng[1]}
    if intent:
        flt["intent"] = intent
    if book_id is not None:
        flt["book_id"] = book_id

    cursor = (
        db.expenses.find(flt)
        .sort([("spent_on", -1), ("_id", -1)])
        .skip(offset)
        .limit(limit)
    )
    return [_expense_out(d) for d in cursor]


def get_expense_by_id(db, user_id: int, expense_id: int) -> Optional[dict]:
    doc = db.expenses.find_one({"_id": expense_id, "user_id": user_id})
    return _expense_out(doc) if doc else None


def update_expense(db, user_id: int, expense_id: int, update: schemas.ExpenseUpdate) -> Optional[dict]:
    """Update an expense. If the category changes, the app learns from it."""
    doc = db.expenses.find_one({"_id": expense_id, "user_id": user_id})
    if not doc:
        return None

    changes: dict = {}
    if update.amount is not None:
        changes["amount"] = _d128(update.amount)
    if update.description is not None:
        changes["description"] = update.description
    if update.date is not None:
        try:
            changes["spent_on"] = parse_date(update.date).date().isoformat()
        except (ValueError, TypeError, OverflowError):
            pass
    if update.intent is not None and update.intent in INTENTS:
        changes["intent"] = update.intent
        changes["is_manual_override"] = True

        if update.intent != doc["intent"]:
            description = changes.get("description", doc["description"])
            tokens = extract_learnable_tokens(description)
            if tokens:
                save_learned_keywords(db, user_id, tokens, update.intent)

    if changes:
        db.expenses.update_one({"_id": expense_id, "user_id": user_id}, {"$set": changes})
    return get_expense_by_id(db, user_id, expense_id)


def delete_expense(db, user_id: int, expense_id: int) -> bool:
    return db.expenses.delete_one({"_id": expense_id, "user_id": user_id}).deleted_count > 0


def delete_all_expenses(db, user_id: int) -> int:
    return db.expenses.delete_many({"user_id": user_id}).deleted_count


# ═══════════════════════════════════════════════
# Debts: money given to / got from other people, kept inside a book.
# These are never counted as expenses.
# ═══════════════════════════════════════════════
def _debt_out(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "book_id": doc["book_id"],
        "direction": doc["direction"],
        "person": doc["person"],
        "reason": doc.get("reason"),
        "amount": _dec(doc["amount"]).quantize(_TWO_PLACES),
        "date": doc["date"],
        "status": doc["status"],
        "settled_on": doc.get("settled_on"),
        "created_at": doc.get("created_at"),
    }


def create_debt(
    db,
    user_id: int,
    book_id: int,
    person: str,
    amount: Decimal,
    direction: str,
    reason: Optional[str],
    on: date,
) -> dict:
    doc = {
        "_id": next_id(db, "debts"),
        "user_id": user_id,
        "book_id": book_id,
        "direction": direction,
        "person": person,
        "reason": reason,
        "amount": _d128(amount),
        "date": on.isoformat(),
        "status": "pending",
        "settled_on": None,
        "created_at": _now(),
    }
    db.debts.insert_one(doc)
    return _debt_out(doc)


def get_debts(
    db, user_id: int, book_id: Optional[int] = None, status: Optional[str] = None
) -> List[dict]:
    flt: dict = {"user_id": user_id}
    if book_id is not None:
        flt["book_id"] = book_id
    if status:
        flt["status"] = status
    cursor = db.debts.find(flt).sort([("date", -1), ("_id", -1)])
    return [_debt_out(d) for d in cursor]


def get_debt_by_id(db, user_id: int, debt_id: int) -> Optional[dict]:
    doc = db.debts.find_one({"_id": debt_id, "user_id": user_id})
    return _debt_out(doc) if doc else None


def update_debt(
    db,
    user_id: int,
    debt_id: int,
    update: schemas.DebtUpdate,
    date_on: Optional[date],
    settled_on: Optional[date],
) -> Optional[dict]:
    """Edit a debt, or mark it returned ("settled") / pending again."""
    doc = db.debts.find_one({"_id": debt_id, "user_id": user_id})
    if not doc:
        return None

    changes: dict = {}
    if update.person is not None:
        changes["person"] = update.person
    if update.amount is not None:
        changes["amount"] = _d128(update.amount)
    if update.direction is not None:
        changes["direction"] = update.direction
    if update.reason is not None:
        changes["reason"] = update.reason.strip() or None
    if date_on is not None:
        changes["date"] = date_on.isoformat()

    if update.status == "settled" and doc["status"] != "settled":
        changes["status"] = "settled"
        changes["settled_on"] = (settled_on or _get_today()).isoformat()
    elif update.status == "pending":
        changes["status"] = "pending"
        changes["settled_on"] = None

    if changes:
        db.debts.update_one({"_id": debt_id, "user_id": user_id}, {"$set": changes})
    return get_debt_by_id(db, user_id, debt_id)


def delete_debt(db, user_id: int, debt_id: int) -> bool:
    return db.debts.delete_one({"_id": debt_id, "user_id": user_id}).deleted_count > 0


def get_debt_summary(db, user_id: int, book_id: Optional[int] = None) -> schemas.DebtSummary:
    flt: dict = {"user_id": user_id, "status": "pending"}
    if book_id is not None:
        flt["book_id"] = book_id
    lent = Decimal("0")
    borrowed = Decimal("0")
    count = 0
    for d in db.debts.find(flt, {"direction": 1, "amount": 1}):
        count += 1
        if d["direction"] == "lent":
            lent += _dec(d["amount"])
        else:
            borrowed += _dec(d["amount"])
    return schemas.DebtSummary(pending_count=count, lent_pending=lent, borrowed_pending=borrowed)


# ═══════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════
def _budgets_map(db, user_id: int) -> Dict[str, Decimal]:
    return {b["intent"]: _dec(b["monthly_limit"]) for b in db.budgets.find({"user_id": user_id})}


def get_monthly_summary(
    db, user_id: int, month: Optional[str] = None, book_id: Optional[int] = None
) -> schemas.MonthlySummary:
    """Intent-wise summary, scoped to a book if given, otherwise to a calendar
    month (books are user-named periods, so book_id takes precedence)."""
    flt: dict = {"user_id": user_id}
    label_month: Optional[str] = None

    if book_id is not None:
        flt["book_id"] = book_id
    else:
        rng = _month_range(month)
        if rng is None:
            today = _get_today()
            month = f"{today.year}-{today.month:02d}"
            rng = _month_range(month)
        flt["spent_on"] = {"$gte": rng[0], "$lt": rng[1]}
        label_month = month

    expense_map: Dict[str, tuple] = {}
    for e in db.expenses.find(flt, {"intent": 1, "amount": 1}):
        total, count = expense_map.get(e["intent"], (Decimal("0"), 0))
        expense_map[e["intent"]] = (total + _dec(e["amount"]), count + 1)

    budgets = _budgets_map(db, user_id)
    grand_total = sum((t for t, _ in expense_map.values()), Decimal("0"))
    grand_count = sum(c for _, c in expense_map.values())

    intent_summaries = []
    for intent_name, meta in INTENTS.items():
        total, count = expense_map.get(intent_name, (Decimal("0"), 0))
        budget_limit = budgets.get(intent_name)
        remaining = (budget_limit - total) if budget_limit else None
        percent = float(total / grand_total * 100) if grand_total > 0 else 0.0

        intent_summaries.append(schemas.IntentSummary(
            intent=intent_name,
            label=meta.label,
            emoji=meta.emoji,
            colour=meta.colour,
            total=total,
            count=count,
            percent=round(percent, 1),
            budget_limit=budget_limit,
            remaining=remaining,
        ))

    intent_summaries.sort(key=lambda x: x.total, reverse=True)
    budget_total = sum(budgets.values(), Decimal("0")) if budgets else None

    return schemas.MonthlySummary(
        month=label_month,
        total=grand_total,
        count=grand_count,
        budget_total=budget_total,
        intents=intent_summaries,
    )


def get_daily_summary(db, user_id: int, month: str) -> schemas.DailySummaryResponse:
    rng = _month_range(month)
    if rng is None:
        today = _get_today()
        month = f"{today.year}-{today.month:02d}"
        rng = _month_range(month)

    days: Dict[str, tuple] = {}
    flt = {"user_id": user_id, "spent_on": {"$gte": rng[0], "$lt": rng[1]}}
    for e in db.expenses.find(flt, {"spent_on": 1, "amount": 1}):
        total, count = days.get(e["spent_on"], (Decimal("0"), 0))
        days[e["spent_on"]] = (total + _dec(e["amount"]), count + 1)

    return schemas.DailySummaryResponse(
        month=month,
        days=[
            schemas.DailySummary(date=d, total=t, count=c)
            for d, (t, c) in sorted(days.items())
        ],
    )


# ═══════════════════════════════════════════════
# Budgets (per user)
# ═══════════════════════════════════════════════
def get_budgets(db, user_id: int) -> List[dict]:
    return [
        {"intent": b["intent"], "monthly_limit": _dec(b["monthly_limit"]).quantize(_TWO_PLACES)}
        for b in db.budgets.find({"user_id": user_id})
    ]


def set_budget(db, user_id: int, intent: str, monthly_limit: Decimal) -> dict:
    db.budgets.update_one(
        {"user_id": user_id, "intent": intent},
        {"$set": {"monthly_limit": _d128(monthly_limit)}},
        upsert=True,
    )
    return {"intent": intent, "monthly_limit": _dec(monthly_limit).quantize(_TWO_PLACES)}


# ═══════════════════════════════════════════════
# Preview
# ═══════════════════════════════════════════════
def preview_expense(db, user_id: int, raw_text: str) -> schemas.PreviewResponse:
    """Classify without saving."""
    learned = load_learned_keywords(db, user_id)
    try:
        result = parse_expense(raw_text, learned_keywords=learned)
        return schemas.PreviewResponse(
            intent=result.intent,
            confidence=result.confidence,
            description=result.description,
            amount=result.amount,
            matched_keywords=result.matched_keywords,
            reason=result.reason,
        )
    except ValueError as e:
        normalized = normalize(raw_text)
        _, leftover = extract_amount(normalized)
        intent_result = classify(leftover, learned_keywords=learned)
        return schemas.PreviewResponse(
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            description=build_description(raw_text),
            amount=None,
            matched_keywords=intent_result.matched_keywords,
            reason=str(e),
        )


# ═══════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════
def export_expenses(
    db, user_id: int, month: Optional[str] = None, book_id: Optional[int] = None
) -> List[dict]:
    expenses = get_expenses(db, user_id, month=month, book_id=book_id, limit=100000)
    book_names = {b["_id"]: b["name"] for b in db.books.find({"user_id": user_id}, {"name": 1})}
    return [
        {
            "id": e["id"],
            "book_id": e["book_id"],
            "book_name": book_names.get(e["book_id"], ""),
            "raw_text": e["raw_text"],
            "description": e["description"],
            "amount": str(e["amount"]),
            "intent": e["intent"],
            "confidence": e["confidence"],
            "spent_on": str(e["spent_on"]),
            "created_at": str(e["created_at"]) if e["created_at"] else "",
            "is_manual_override": e["is_manual_override"],
        }
        for e in expenses
    ]
