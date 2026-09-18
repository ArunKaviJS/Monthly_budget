"""
expenses.py — Expense endpoints (all scoped to the signed-in user).
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db
from ..security import get_current_user
from .. import crud, schemas
from ..intent_config import INTENTS
from ..intent_engine import _get_today

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.post("", response_model=schemas.ExpenseResponse, status_code=201)
def create_expense(
    body: schemas.ExpenseCreate,
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create an expense from raw_text (amount/description/date parsed) or manual
    fields. Always filed under the user's active book."""
    uid = user["_id"]
    active_book = crud.get_active_book(db, uid)
    if not active_book:
        raise HTTPException(
            status_code=409,
            detail="No active book. Create a book before adding expenses.",
        )

    if body.raw_text:
        if body.intent and body.intent not in INTENTS:
            raise HTTPException(status_code=400, detail=f"Unknown intent: {body.intent}")
        try:
            return crud.create_expense_from_text(
                db, uid, body.raw_text, book_id=active_book["id"], intent=body.intent
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    elif body.amount is not None and body.intent and body.description:
        if body.intent not in INTENTS:
            raise HTTPException(status_code=400, detail=f"Unknown intent: {body.intent}")
        spent_on = date.today()
        if body.date:
            from dateutil.parser import parse as parse_date

            try:
                spent_on = parse_date(body.date).date()
            except (ValueError, TypeError):
                spent_on = _get_today()
        return crud.create_expense_manual(
            db, uid, body.amount, body.intent, body.description, spent_on, book_id=active_book["id"]
        )
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either 'raw_text' or all of 'amount', 'intent', 'description'.",
        )


@router.get("", response_model=List[schemas.ExpenseResponse])
def list_expenses(
    month: Optional[str] = Query(None, description="Filter by month YYYY-MM"),
    intent: Optional[str] = Query(None, description="Filter by intent"),
    book_id: Optional[int] = Query(None, description="Filter by book"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List this user's expenses, newest first. Optional month/intent/book filters."""
    return crud.get_expenses(
        db, user["_id"], month=month, intent=intent, book_id=book_id, limit=limit, offset=offset
    )


@router.get("/{expense_id}", response_model=schemas.ExpenseResponse)
def get_expense(expense_id: int, db=Depends(get_db), user: dict = Depends(get_current_user)):
    expense = crud.get_expense_by_id(db, user["_id"], expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.patch("/{expense_id}", response_model=schemas.ExpenseResponse)
def update_expense(
    expense_id: int,
    body: schemas.ExpenseUpdate,
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update an expense. Changing the category teaches the app."""
    expense = crud.update_expense(db, user["_id"], expense_id, body)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.delete("", status_code=200)
def delete_all_expenses(db=Depends(get_db), user: dict = Depends(get_current_user)):
    """Permanently delete every expense of the signed-in user."""
    return {"deleted": crud.delete_all_expenses(db, user["_id"])}


@router.delete("/{expense_id}", status_code=204)
def delete_expense(expense_id: int, db=Depends(get_db), user: dict = Depends(get_current_user)):
    if not crud.delete_expense(db, user["_id"], expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")
