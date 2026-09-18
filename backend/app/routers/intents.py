"""
intents.py — Intent metadata (public) and the user's learned keywords.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..security import get_current_user
from .. import crud, schemas
from ..intent_config import INTENTS

router = APIRouter(tags=["intents"])


@router.get("/api/intents", response_model=List[schemas.IntentMetaResponse])
def get_intents():
    """Intent metadata (label, emoji, colour). Same for everyone."""
    return [
        schemas.IntentMetaResponse(
            intent=name,
            label=meta.label,
            emoji=meta.emoji,
            colour=meta.colour,
        )
        for name, meta in INTENTS.items()
    ]


@router.get("/api/keywords", response_model=List[schemas.LearnedKeywordResponse])
def get_keywords(db=Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_keywords(db, user["_id"])


@router.delete("/api/keywords/{keyword}", status_code=204)
def delete_keyword(keyword: str, db=Depends(get_db), user: dict = Depends(get_current_user)):
    if not crud.delete_keyword(db, user["_id"], keyword):
        raise HTTPException(status_code=404, detail="Keyword not found")


@router.delete("/api/keywords", status_code=200)
def clear_keywords(db=Depends(get_db), user: dict = Depends(get_current_user)):
    return {"deleted": crud.clear_all_keywords(db, user["_id"])}
