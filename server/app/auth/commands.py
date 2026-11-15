"""create-admin: create an admin account, or reset its password. Admins then add viewer and editor users in the panel.

  python -m app.cli create-admin admin@example.com             # asks for the password
  ADMIN_PASSWORD=... python -m app.cli create-admin admin@example.com
Resetting a password signs that admin out everywhere. Against Neon, set DATABASE_URL to it first.
"""

import argparse
import getpass
import logging
import os

from app.auth import repository
from app.auth.security import MIN_PASSWORD
from app.core.db import connect
from app.core.logs import script_log
from app.shared.email import is_valid_email, normalize_email

log = logging.getLogger("create_admin")


def register(commands: argparse._SubParsersAction) -> None:
    parser = commands.add_parser("create-admin", help="create an admin account or reset its password")
    parser.add_argument("email")
    parser.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> int:
    script_log("create_admin")  # logs the email and the outcome, never the password
    email = normalize_email(args.email)
    if not is_valid_email(email):
        log.error("Not saved: %s isn't an email address", email)
        return 1
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass(f"Password for {email}: ")
    if len(password) < MIN_PASSWORD:
        log.error("Not saved: the password for %s is shorter than %d characters", email, MIN_PASSWORD)
        return 1
    with connect() as conn, conn.transaction():
        existed = repository.save_admin(conn, email, password)
        ended = repository.delete_sessions(conn, email)
    log.info("Admin %s %s; %d signed-in session(s) ended", email, "password reset" if existed else "created", ended)
    return 0
