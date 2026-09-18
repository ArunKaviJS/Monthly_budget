"""
budgets.py — Budget limit endpoints (per user).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..security import get_current_user
from .. import crud, schemas
from ..intent_config import INTENTS

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.get("", response_model=List[schemas.BudgetResponse])
def get_budgets(db=Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_budgets(db, user["_id"])


@router.post("", response_model=schemas.BudgetResponse, status_code=201)
def set_budget(body: schemas.BudgetCreate, db=Depends(get_db), user: dict = Depends(get_current_user)):
    """Create or update this user's monthly limit for an intent."""
    if body.intent not in INTENTS:
        raise HTTPException(status_code=400, detail=f"Unknown intent: {body.intent}")
    return crud.set_budget(db, user["_id"], body.intent, body.monthly_limit)
