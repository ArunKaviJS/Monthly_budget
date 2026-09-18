"""
security.py — password hashing, login tokens (JWT) and the current-user dependency.
"""

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .database import get_db

_bearer = HTTPBearer(auto_error=False)

# scrypt (memory-hard, standard library — no native dependency to install)
_N, _R, _P = 2 ** 14, 8, 1


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


# Used to spend the same time on "unknown user" as on "wrong password",
# so response time doesn't reveal which usernames exist.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def _secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not set")
    return secret


def create_token(user_id: int) -> str:
    days = int(os.environ.get("JWT_DAYS", "30"))
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(days=days)}
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str) -> int:
    """Return the user id inside a valid token, or raise jwt.PyJWTError."""
    payload = jwt.decode(token, _secret(), algorithms=["HS256"], options={"require": ["exp", "sub"]})
    return int(payload["sub"])


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db=Depends(get_db),
) -> dict:
    """Verifies the Bearer token and loads the user. 401 otherwise."""
    unauthorized = HTTPException(
        status_code=401,
        detail="Not signed in or session expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None or not creds.credentials:
        raise unauthorized
    try:
        user_id = decode_token(creds.credentials)
    except (jwt.PyJWTError, ValueError):
        raise unauthorized
    user = db.users.find_one({"_id": user_id})
    if not user:
        raise unauthorized
    return user
