"""Sign-in, sign-out, password change, and user management (admins only)."""

import logging

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.auth import repository
from app.auth.dependencies import User, require_admin, signed_in
from app.auth.schemas import Login, NewUser, PasswordChange, UserChange
from app.auth.security import (
    COOKIE,
    DUMMY_HASH,
    MIN_PASSWORD,
    SESSION_SECONDS,
    login_limiter,
    new_session_token,
    token_hash,
    verify_password,
)
from app.core.db import get_conn
from app.shared.email import is_valid_email, normalize_email

router = APIRouter(prefix="/api/admin", tags=["auth"])
log = logging.getLogger("admin")  # an audit trail of admin actions


@router.post("/login")
def login(body: Login, request: Request, response: Response) -> User:
    ip = request.client.host if request.client else "?"
    if login_limiter.blocked(ip):
        log.warning("Sign-in refused: %d failed attempts from %s in 15 minutes", login_limiter.recent(ip), ip)
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    email = normalize_email(body.email)
    with get_conn() as conn:
        user = repository.find_user(conn, email)
        if not verify_password(body.password, user["password_hash"] if user else DUMMY_HASH) or not user:
            attempt = login_limiter.recent(ip) + 1
            login_limiter.fail(ip)
            log.warning(
                "Failed sign-in for %s from %s (%s; attempt %d of %d)",
                email,
                ip,
                "wrong password" if user else "no such admin",
                attempt,
                login_limiter.max_failures,
            )
            raise HTTPException(401, "Incorrect email or password")
        token = new_session_token()
        repository.create_session(conn, token_hash(token), email)
    login_limiter.succeed(ip)
    log.info("Signed in: %s from %s", email, ip)
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite="strict", secure=secure)
    return {"email": email, "role": user["role"], "must_change_password": user["must_change_password"]}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    if token := request.cookies.get(COOKIE):
        with get_conn() as conn:
            email = repository.delete_session(conn, token_hash(token))
        log.info("Signed out: %s", email or "(session had already ended)")
    response.delete_cookie(COOKIE)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(signed_in)) -> User:
    return user


@router.post("/password")
def change_password(body: PasswordChange, request: Request, user: User = Depends(signed_in)) -> dict[str, bool]:
    """Every user changes their own password; a first sign-in with an admin-given password must do this first."""
    if len(body.new_password) < MIN_PASSWORD:
        raise HTTPException(422, f"Use at least {MIN_PASSWORD} characters.")
    if body.new_password == body.current_password:
        raise HTTPException(422, "Choose a password different from the current one.")
    with get_conn() as conn:
        stored = repository.find_user(conn, user["email"])
        if not stored or not verify_password(body.current_password, stored["password_hash"]):
            raise HTTPException(401, "Your current password is incorrect")
        with conn.transaction():
            repository.set_password(conn, user["email"], body.new_password, must_change=False)
            # sign out this user's other sessions; the one making the change stays signed in
            repository.delete_sessions(conn, user["email"], keep_token_hash=token_hash(request.cookies.get(COOKIE, "")))
    return {"ok": True}


# ---------- users (admins only) ----------


def _check_new_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise HTTPException(422, f"Use a password of at least {MIN_PASSWORD} characters.")


def _managed_user(conn: psycopg.Connection, email: str) -> str:
    """A user an admin may change: exists and isn't an admin (admins are managed with the create-admin command)."""
    email = normalize_email(email)
    user = repository.find_user(conn, email)
    if not user:
        raise HTTPException(404, "No such user")
    if user["role"] == "admin":
        raise HTTPException(403, "Admin accounts can't be changed here")
    return email


@router.get("/users", response_model=None)
def list_users(_: str = Depends(require_admin)) -> list[dict]:
    with get_conn() as conn:
        return repository.list_users(conn)


@router.post("/users")
def create_user(body: NewUser, admin_email: str = Depends(require_admin)) -> dict[str, str]:
    email = normalize_email(body.email)
    if not is_valid_email(email):
        raise HTTPException(422, "Enter a valid email address.")
    _check_new_password(body.password)
    with get_conn() as conn:
        if not repository.create_user(conn, email, body.password, body.role, admin_email):
            raise HTTPException(409, "A user with this email already exists")
    log.info("User %s (%s) created by %s", email, body.role, admin_email)
    return {"email": email, "role": body.role}


@router.patch("/users/{email}")
def change_user(email: str, body: UserChange, admin_email: str = Depends(require_admin)) -> dict[str, bool]:
    if body.password is not None:
        _check_new_password(body.password)
    with get_conn() as conn, conn.transaction():
        email = _managed_user(conn, email)
        if body.role:
            repository.set_role(conn, email, body.role)
        if body.password is not None:
            repository.set_password(conn, email, body.password, must_change=True)
            repository.delete_sessions(conn, email)
    log.info("User %s changed by %s", email, admin_email)
    return {"ok": True}


@router.delete("/users/{email}")
def delete_user(email: str, admin_email: str = Depends(require_admin)) -> dict[str, bool]:
    with get_conn() as conn:
        email = _managed_user(conn, email)
        repository.delete_user(conn, email)
    log.info("User %s deleted by %s", email, admin_email)
    return {"ok": True}
