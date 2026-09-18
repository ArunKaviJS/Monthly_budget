"""
summary.py — Summary & analytics endpoints (per user).
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..database import get_db
from ..security import get_current_user
from .. import crud, schemas
from ..intent_engine import _get_today

router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.get("", response_model=schemas.MonthlySummary)
def get_monthly_summary(
    month: Optional[str] = Query(None, description="YYYY-MM, default=current month"),
    book_id: Optional[int] = Query(None, description="Scope to a book instead of a calendar month"),
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Intent-wise summary, scoped to a book (if given) or a calendar month.
    Includes every intent even with total 0, sorted by total desc."""
    if book_id is None and not month:
        today = _get_today()
        month = f"{today.year}-{today.month:02d}"
    return crud.get_monthly_summary(db, user["_id"], month, book_id=book_id)


@router.get("/daily", response_model=schemas.DailySummaryResponse)
def get_daily_summary(
    month: Optional[str] = Query(None, description="YYYY-MM, default=current month"),
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Per-day totals."""
    if not month:
        today = _get_today()
        month = f"{today.year}-{today.month:02d}"
    return crud.get_daily_summary(db, user["_id"], month)
