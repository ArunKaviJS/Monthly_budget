"""
auth.py — Sign up, sign in, and session refresh.

Sign-in returns a JWT. The app stores it and, every time it opens, calls
/api/auth/refresh: the server verifies the token and returns the user's
details together with a fresh token.
"""

from fastapi import APIRouter, Depends, HTTPException

from .. import crud, schemas
from ..database import get_db
from ..security import (
    burn_password_check,
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _auth_response(user: dict) -> dict:
    return {"token": create_token(user["_id"]), "user": crud.user_out(user)}


@router.post("/signup", response_model=schemas.AuthResponse, status_code=201)
def signup(body: schemas.SignUpRequest, db=Depends(get_db)):
    """Create an account. Username and email must both be unused (any letter case)."""
    try:
        user = crud.create_user(db, body.username, body.email, hash_password(body.password))
    except crud.DuplicateUser as e:
        if e.field == "username":
            detail = "That username is already taken"
        elif e.field == "email":
            detail = "That email is already registered"
        else:
            detail = "That username or email is already in use"
        raise HTTPException(status_code=409, detail=detail)
    return _auth_response(user)


@router.post("/login", response_model=schemas.AuthResponse)
def login(body: schemas.LoginRequest, db=Depends(get_db)):
    """Sign in with username or email plus password."""
    user = crud.find_user_for_login(db, body.identifier)
    if not user:
        burn_password_check(body.password)
        raise HTTPException(status_code=401, detail="Incorrect username/email or password")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username/email or password")
    return _auth_response(user)


@router.post("/refresh", response_model=schemas.AuthResponse)
def refresh(user: dict = Depends(get_current_user)):
    """Verify the current token and return the user's details with a fresh token."""
    return _auth_response(user)


@router.get("/me", response_model=schemas.UserResponse)
def me(user: dict = Depends(get_current_user)):
    return crud.user_out(user)
