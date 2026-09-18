"""
MedPak AI — Auth dependencies for FastAPI
Provides get_current_user for protecting routes.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth.security import decode_access_token
from auth.users_db import get_user_by_id

# auto_error=False lets us return a friendlier 401 instead of 403
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    FastAPI dependency that validates the Bearer JWT and returns the user.
    Routes using this are inaccessible without a valid token.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Session expired or token invalid. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload.")

    user = get_user_by_id(int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists.")

    return user
