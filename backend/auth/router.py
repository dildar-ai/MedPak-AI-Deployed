"""
MedPak AI — Authentication API endpoints
Public routes: register, login, me (token required for /me).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, field_validator
import re

from auth.security import hash_password, verify_password, create_access_token
from auth.users_db import create_user, get_user_by_email, get_user_by_id, init_users_db
from auth.dependencies import get_current_user
from ratelimit import limiter

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Ensure the users table exists (idempotent)
init_users_db()


# ── Request models ────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if not (3 <= len(v) <= 30):
            raise ValueError("Username must be 3-30 characters.")
        if not re.match(r"^[a-zA-Z0-9_.-]+$", v):
            raise ValueError("Username can only contain letters, numbers, _ . -")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not re.search(r"[a-zA-Z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must contain at least one letter and one number.")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register")
@limiter.limit("5/minute")
def register(req: RegisterRequest, request: Request):
    """Create a new account and return an access token."""
    if get_user_by_email(req.email) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    try:
        user = create_user(
            email=req.email,
            username=req.username,
            password_hash=hash_password(req.password),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    token = create_access_token(user["id"], user["email"])
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/login")
@limiter.limit("5/minute")
def login(req: LoginRequest, request: Request):
    """Verify credentials and return an access token."""
    user = get_user_by_email(req.email)
    if user is None or not verify_password(req.password, user["password_hash"]):
        # Same message for both cases — don't reveal which one failed
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(user["id"], user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "created_at": user["created_at"],
        },
    }


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return {"user": current_user}
