"""Create an admin account, or reset its password.

Usage (from the server/ directory; against Neon, set DATABASE_URL to it first):
  python -m pipeline.create_admin admin@example.com            # asks for the password
  ADMIN_PASSWORD=... python -m pipeline.create_admin admin@example.com
Resetting a password signs that admin out everywhere.
"""
import getpass
import os
import sys
from pathlib import Path

from app.admin import hash_password
from app.db import get_conn

SCHEMA = Path(__file__).resolve().parent.parent / "database" / "sources.sql"


def main():
    if len(sys.argv) != 2 or "@" not in sys.argv[1]:
        sys.exit("Usage: python -m pipeline.create_admin <email>")
    email = sys.argv[1].strip().lower()
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass(f"Password for {email}: ")
    if len(password) < 8:
        sys.exit("Use a password of at least 8 characters.")
    with get_conn() as conn:
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
        conn.execute("""INSERT INTO public.admin_users (email, password_hash) VALUES (%s, %s)
                        ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash""", (email, hash_password(password)))
        conn.execute("DELETE FROM public.admin_sessions WHERE email = %s", (email,))
    print(f"Admin {email} saved.")


if __name__ == "__main__":
    main()
