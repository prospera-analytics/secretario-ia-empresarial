import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DATABASE_DIR = ROOT_DIR / "database"
SQLITE_PATH = DATABASE_DIR / "empresa.db"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{SQLITE_PATH.as_posix()}",
)
