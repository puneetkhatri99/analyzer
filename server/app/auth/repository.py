from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.auth.security import SESSION_SECONDS, hash_password


def find_session_user(conn: psycopg.Connection, token_hash: str) -> dict[str, Any] | None:
    return (
        conn.cursor(row_factory=dict_row)
        .execute(
            """SELECT u.email, u.role, u.must_change_password FROM public.admin_sessions s
               JOIN public.admin_users u USING (email) WHERE s.token_hash = %s AND s.expires_at > now()""",
            (token_hash,),
        )
        .fetchone()
    )


def find_user(conn: psycopg.Connection, email: str) -> dict[str, Any] | None:
    return (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT email, password_hash, role, must_change_password FROM public.admin_users WHERE email = %s",
            (email,),
        )
        .fetchone()
    )


def create_session(conn: psycopg.Connection, token_hash: str, email: str) -> None:
    conn.execute("DELETE FROM public.admin_sessions WHERE expires_at < now()")
    conn.execute(
        "INSERT INTO public.admin_sessions (token_hash, email, expires_at)"
        " VALUES (%s, %s, now() + %s * interval '1 second')",
        (token_hash, email, SESSION_SECONDS),
    )


def delete_session(conn: psycopg.Connection, token_hash: str) -> str | None:
    """Ends one session; returns its user's email, or None if it had already ended."""
    row = conn.execute(
        "DELETE FROM public.admin_sessions WHERE token_hash = %s RETURNING email", (token_hash,)
    ).fetchone()
    return row[0] if row else None


def delete_sessions(conn: psycopg.Connection, email: str, keep_token_hash: str | None = None) -> int:
    """Signs a user out everywhere (except the session `keep_token_hash`); returns how many sessions ended."""
    return conn.execute(
        "DELETE FROM public.admin_sessions WHERE email = %s AND token_hash IS DISTINCT FROM %s",
        (email, keep_token_hash),
    ).rowcount


def set_password(conn: psycopg.Connection, email: str, password: str, *, must_change: bool) -> None:
    conn.execute(
        "UPDATE public.admin_users SET password_hash = %s, must_change_password = %s WHERE email = %s",
        (hash_password(password), must_change, email),
    )


def list_users(conn: psycopg.Connection) -> list[dict[str, Any]]:
    return (
        conn.cursor(row_factory=dict_row)
        .execute(
            """SELECT email, role, must_change_password, created_by, created_at FROM public.admin_users
               ORDER BY array_position(ARRAY['admin', 'editor', 'viewer'], role), email"""
        )
        .fetchall()
    )


def create_user(conn: psycopg.Connection, email: str, password: str, role: str, created_by: str) -> bool:
    """A user with a one-time password; False if the email is taken."""
    added = conn.execute(
        """INSERT INTO public.admin_users (email, password_hash, role, must_change_password, created_by)
           VALUES (%s, %s, %s, true, %s) ON CONFLICT (email) DO NOTHING RETURNING email""",
        (email, hash_password(password), role, created_by),
    ).fetchone()
    return added is not None


def set_role(conn: psycopg.Connection, email: str, role: str) -> None:
    conn.execute("UPDATE public.admin_users SET role = %s WHERE email = %s", (role, email))


def delete_user(conn: psycopg.Connection, email: str) -> None:
    conn.execute("DELETE FROM public.admin_users WHERE email = %s", (email,))  # sessions go too (ON DELETE CASCADE)


def save_admin(conn: psycopg.Connection, email: str, password: str) -> bool:
    """Create an admin or reset its password; True when the account already existed."""
    existed = conn.execute("SELECT 1 FROM public.admin_users WHERE email = %s", (email,)).fetchone() is not None
    conn.execute(
        """INSERT INTO public.admin_users (email, password_hash, role) VALUES (%s, %s, 'admin')
           ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash, role = 'admin',
             must_change_password = false""",
        (email, hash_password(password)),
    )
    return existed
