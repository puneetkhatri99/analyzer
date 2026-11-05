import os
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent

_env_file = SERVER_DIR / ".env"
if _env_file.exists():
    # local dev only; in production these are set as real environment variables
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

DATABASE_URL = os.environ.get("DATABASE_URL")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
