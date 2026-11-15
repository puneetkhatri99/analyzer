from collections.abc import Callable
from typing import TypedDict

from fastapi import HTTPException, Request

from app.auth import repository
from app.auth.security import COOKIE, ROLES, token_hash
from app.core.db import get_conn


class User(TypedDict):
    email: str
    role: str
    must_change_password: bool


def signed_in(request: Request) -> User:
    """The signed-in user, even one who still has to change their password; 401 otherwise."""
    if token := request.cookies.get(COOKIE):
        with get_conn() as conn:
            user = repository.find_session_user(conn, token_hash(token))
        if user:
            return User(**user)
    raise HTTPException(401, "Sign in required")


def require_role(minimum: str) -> Callable[[Request], str]:
    """A dependency that returns the signed-in user's email when their role is at least `minimum`."""

    def check(request: Request) -> str:
        user = signed_in(request)
        if user["must_change_password"]:
            raise HTTPException(403, "Change your password first")
        if ROLES.index(user["role"]) < ROLES.index(minimum):
            raise HTTPException(403, "Your account doesn't have access to this")
        return user["email"]

    return check


require_viewer = require_role("viewer")
require_editor = require_role("editor")
require_admin = require_role("admin")
