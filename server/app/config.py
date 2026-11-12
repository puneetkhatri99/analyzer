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

# Admin panel: AI extraction of jobs from any URL. Admin accounts live in the database (pipeline.create_admin).
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")

# Logs: also send every log line to Axiom when a token is set (app/logs.py).
AXIOM_TOKEN = os.environ.get("AXIOM_TOKEN")
AXIOM_DATASET = os.environ.get("AXIOM_DATASET", "analyzer")
