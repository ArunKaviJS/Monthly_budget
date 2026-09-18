"""
books.py — Book endpoints.

A "book" is a user-named ledger (e.g. "September", "Trip to Goa") that
expenses are filed under. Each user has their own books, and exactly one of
them is "active" — new expenses go into the active book.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..security import get_current_user
from .. import crud, schemas

router = APIRouter(prefix="/api/books", tags=["books"])


@router.post("", response_model=schemas.BookResponse, status_code=201)
def create_book(body: schemas.BookCreate, db=Depends(get_db), user: dict = Depends(get_current_user)):
    """Create a new book and make it the active one."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Book name cannot be empty")
    return crud.create_book(db, user["_id"], name)


@router.get("", response_model=List[schemas.BookResponse])
def list_books(db=Depends(get_db), user: dict = Depends(get_current_user)):
    """List this user's books, newest first, each with its total and entry count."""
    return crud.get_books(db, user["_id"])


@router.get("/active", response_model=schemas.BookResponse)
def get_active_book(db=Depends(get_db), user: dict = Depends(get_current_user)):
    """Get the active book. 404 if this user hasn't created one yet."""
    book = crud.get_active_book(db, user["_id"])
    if not book:
        raise HTTPException(status_code=404, detail="No active book")
    return book


@router.patch("/{book_id}", response_model=schemas.BookResponse)
def update_book(
    book_id: int,
    body: schemas.BookUpdate,
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Rename a book and/or make it the active one."""
    if body.name is not None and not body.name.strip():
        raise HTTPException(status_code=422, detail="Book name cannot be empty")
    book = crud.update_book(db, user["_id"], book_id, body)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.delete("/{book_id}", status_code=200)
def delete_book(book_id: int, db=Depends(get_db), user: dict = Depends(get_current_user)):
    """Permanently delete a book and every expense inside it."""
    deleted = crud.delete_book(db, user["_id"], book_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"deleted_expenses": deleted}
