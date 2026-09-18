"""
schemas.py — Pydantic schemas for request/response validation.
"""

import re

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, List
from datetime import date, datetime
from decimal import Decimal


# ── Auth ──
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,24}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class SignUpRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        v = v.strip()
        if not _USERNAME_RE.match(v):
            raise ValueError("Username must be 3-24 characters: letters, numbers, dot or underscore")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 254 or not _EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        if len(v) > 128:
            raise ValueError("Password is too long")
        return v


class LoginRequest(BaseModel):
    identifier: str  # username or email
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


# ── Book ──
class BookCreate(BaseModel):
    name: str


class BookUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class BookResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: Optional[datetime] = None
    total: Decimal = Decimal("0")
    count: int = 0
    pending_debts: int = 0

    model_config = {"from_attributes": True}


# ── Debts (money given to / got from other people, kept inside a book) ──
class DebtCreate(BaseModel):
    person: str
    amount: Decimal
    direction: Literal["lent", "borrowed"]  # lent = I gave, borrowed = I got
    reason: Optional[str] = None
    date: Optional[str] = None  # when it was given/got; default today

    @field_validator("person")
    @classmethod
    def _person(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 60:
            raise ValueError("Enter the name of the person (up to 60 characters)")
        return v

    @field_validator("amount")
    @classmethod
    def _amount(cls, v: Decimal) -> Decimal:
        if v <= 0 or v >= Decimal("1000000000"):
            raise ValueError("Enter an amount greater than 0")
        return v

    @field_validator("reason")
    @classmethod
    def _reason(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 200:
            raise ValueError("Keep the reason under 200 characters")
        return v or None


class DebtUpdate(BaseModel):
    person: Optional[str] = None
    amount: Optional[Decimal] = None
    direction: Optional[Literal["lent", "borrowed"]] = None
    reason: Optional[str] = None
    date: Optional[str] = None
    status: Optional[Literal["pending", "settled"]] = None
    settled_on: Optional[str] = None  # when it came back; default today

    @field_validator("person")
    @classmethod
    def _person(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v or len(v) > 60:
            raise ValueError("Enter the name of the person (up to 60 characters)")
        return v

    @field_validator("amount")
    @classmethod
    def _amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and (v <= 0 or v >= Decimal("1000000000")):
            raise ValueError("Enter an amount greater than 0")
        return v

    @field_validator("reason")
    @classmethod
    def _reason(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) > 200:
            raise ValueError("Keep the reason under 200 characters")
        return v


class DebtResponse(BaseModel):
    id: int
    book_id: int
    direction: str
    person: str
    reason: Optional[str] = None
    amount: Decimal
    date: date
    status: str
    settled_on: Optional[date] = None
    created_at: Optional[datetime] = None


class DebtSummary(BaseModel):
    pending_count: int = 0
    lent_pending: Decimal = Decimal("0")      # they still owe me
    borrowed_pending: Decimal = Decimal("0")  # I still owe them


# ── Expense ──
class ExpenseCreate(BaseModel):
    raw_text: Optional[str] = None
    # Manual entry fields (used if raw_text is not provided)
    amount: Optional[Decimal] = None
    intent: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None  # "YYYY-MM-DD" or natural language


class ExpenseUpdate(BaseModel):
    amount: Optional[Decimal] = None
    intent: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: int
    book_id: Optional[int] = None
    raw_text: str
    description: str
    amount: Decimal
    intent: str
    confidence: Optional[float] = None
    spent_on: date
    created_at: Optional[datetime] = None
    is_manual_override: bool = False

    model_config = {"from_attributes": True}


# ── Preview ──
class PreviewRequest(BaseModel):
    raw_text: str


class PreviewResponse(BaseModel):
    intent: str
    confidence: float
    description: str
    amount: Optional[Decimal] = None
    matched_keywords: List[str] = []
    reason: str = ""


# ── Summary ──
class IntentSummary(BaseModel):
    intent: str
    label: str
    emoji: str
    colour: str
    total: Decimal
    count: int
    percent: float
    budget_limit: Optional[Decimal] = None
    remaining: Optional[Decimal] = None


class MonthlySummary(BaseModel):
    month: Optional[str] = None
    total: Decimal
    count: int
    budget_total: Optional[Decimal] = None
    intents: List[IntentSummary]


class DailySummary(BaseModel):
    date: date
    total: Decimal
    count: int


class DailySummaryResponse(BaseModel):
    month: str
    days: List[DailySummary]


# ── Budget ──
class BudgetCreate(BaseModel):
    intent: str
    monthly_limit: Decimal


class BudgetResponse(BaseModel):
    intent: str
    monthly_limit: Decimal

    model_config = {"from_attributes": True}


# ── Intent Metadata ──
class IntentMetaResponse(BaseModel):
    intent: str
    label: str
    emoji: str
    colour: str


# ── Learned Keywords ──
class LearnedKeywordResponse(BaseModel):
    keyword: str
    intent: str
    hits: int

    model_config = {"from_attributes": True}


# ── Health ──
class HealthResponse(BaseModel):
    status: str = "ok"
    database: str = "mongodb"
    version: str = "1.0.0"
