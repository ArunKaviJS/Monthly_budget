"""
debts.py — Money you gave to / got from other people, kept inside a book.

  lent      = you gave money (they owe you)
  borrowed  = you got money  (you owe them)

A debt stays "pending" until it is returned; marking it "settled" clears it
from the pending count (the app's notification badge). Debts are never mixed
into expenses or their totals.
"""

from datetime import date
from typing import List, Literal, Optional

from dateutil.parser import parse as parse_date
from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db
from ..security import get_current_user
from .. import crud, schemas
from ..intent_engine import _get_today

router = APIRouter(prefix="/api/debts", tags=["debts"])


def _parse_date_or_422(value: Optional[str], field: str = "date") -> Optional[date]:
    if value is None or not value.strip():
        return None
    try:
        return parse_date(value.strip()).date()
    except (ValueError, TypeError, OverflowError):
        raise HTTPException(status_code=422, detail=f"Enter the {field} as YYYY-MM-DD")


@router.post("", response_model=schemas.DebtResponse, status_code=201)
def create_debt(
    body: schemas.DebtCreate,
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Note a new debt in the user's active book."""
    uid = user["_id"]
    book = crud.get_active_book(db, uid)
    if not book:
        raise HTTPException(
            status_code=409,
            detail="No active book. Create a book before adding debts.",
        )
    on = _parse_date_or_422(body.date) or _get_today()
    return crud.create_debt(db, uid, book["id"], body.person, body.amount, body.direction, body.reason, on)


@router.get("", response_model=List[schemas.DebtResponse])
def list_debts(
    book_id: Optional[int] = Query(None, description="Only this book"),
    status: Optional[Literal["pending", "settled"]] = Query(None),
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return crud.get_debts(db, user["_id"], book_id=book_id, status=status)


@router.get("/summary", response_model=schemas.DebtSummary)
def debt_summary(
    book_id: Optional[int] = Query(None),
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Pending count and totals (what you'll get / what you owe)."""
    return crud.get_debt_summary(db, user["_id"], book_id=book_id)


@router.patch("/{debt_id}", response_model=schemas.DebtResponse)
def update_debt(
    debt_id: int,
    body: schemas.DebtUpdate,
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Edit a debt, or mark it returned (status=settled) / pending again."""
    debt = crud.update_debt(
        db,
        user["_id"],
        debt_id,
        body,
        date_on=_parse_date_or_422(body.date),
        settled_on=_parse_date_or_422(body.settled_on, "return date"),
    )
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")
    return debt


@router.delete("/{debt_id}", status_code=204)
def delete_debt(debt_id: int, db=Depends(get_db), user: dict = Depends(get_current_user)):
    if not crud.delete_debt(db, user["_id"], debt_id):
        raise HTTPException(status_code=404, detail="Debt not found")
