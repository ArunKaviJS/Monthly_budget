"""
preview.py — Classify text without saving it.
"""

from fastapi import APIRouter, Depends

from ..database import get_db
from ..security import get_current_user
from .. import crud, schemas

router = APIRouter(prefix="/api", tags=["preview"])


@router.post("/preview", response_model=schemas.PreviewResponse)
def preview(
    body: schemas.PreviewRequest,
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Classify the input without saving (uses this user's learned keywords)."""
    return crud.preview_expense(db, user["_id"], body.raw_text)
