"""Small admin-editable settings and run markers, kept as JSON in public.app_settings (key -> value)."""

from typing import Any

from psycopg.types.json import Jsonb

from app.core.db import get_conn


def get_setting(key: str, default: Any = None) -> Any:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM public.app_settings WHERE key = %s", (key,)).fetchone()
    return row[0] if row else default


def set_setting(key: str, value: Any, by: str | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO public.app_settings (key, value, updated_by) VALUES (%s, %s, %s)
               ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now(),
                 updated_by = EXCLUDED.updated_by""",
            (key, Jsonb(value), by),
        )


def delete_setting(key: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM public.app_settings WHERE key = %s", (key,))
