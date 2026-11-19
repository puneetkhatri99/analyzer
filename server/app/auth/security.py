"""Passwords, session tokens and the sign-in lockout.

Admins live in admin_users with scrypt password hashes. A session is a random token in an HttpOnly cookie; only its
SHA-256 is stored in admin_sessions, so a database leak can't be replayed as a sign-in.
"""

import hashlib
import hmac
import secrets
import threading
import time

COOKIE = "admin_session"
SESSION_SECONDS = 12 * 3600
MIN_PASSWORD = 8

# Roles, lowest first; each can do everything the ones before it can.
#   viewer: read the dashboard. editor: also add and delete jobs. admin: also manage users and see AI costs.
# Only admins create users (as viewer or editor), with a one-time password the user must change at first sign-in.
# Admin accounts are made with `python -m app.cli create-admin`, never through the API.
ROLES = ("viewer", "editor", "admin")


# Each scrypt hash takes 16 MB of memory; a burst of sign-in attempts mustn't run the 512 MB server out of it.
_hashing = threading.BoundedSemaphore(4)


def _scrypt(password: str, salt: bytes) -> bytes:
    with _hashing:
        return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"scrypt${salt.hex()}${_scrypt(password, salt).hex()}"


def verify_password(password: str, stored: str) -> bool:
    _, salt, digest = stored.split("$")
    return hmac.compare_digest(_scrypt(password, bytes.fromhex(salt)).hex(), digest)


# Checked for unknown emails, so response time doesn't reveal which accounts exist.
DUMMY_HASH = hash_password(secrets.token_hex(8))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class LoginLimiter:
    """At most `max_failures` failed sign-ins per IP within `window` seconds.

    shortcut: in-memory and per server process, so it resets on restart; move to the database if this runs on
    several instances.
    """

    def __init__(self, max_failures: int = 5, window: float = 15 * 60) -> None:
        self.max_failures, self.window = max_failures, window
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def recent(self, ip: str) -> int:
        with self._lock:
            cutoff = time.time() - self.window
            self._failures[ip] = [t for t in self._failures.get(ip, []) if t > cutoff]
            return len(self._failures[ip])

    def blocked(self, ip: str) -> bool:
        return self.recent(ip) >= self.max_failures

    def fail(self, ip: str) -> None:
        with self._lock:
            self._failures.setdefault(ip, []).append(time.time())

    def succeed(self, ip: str) -> None:
        with self._lock:
            self._failures.pop(ip, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = LoginLimiter()
