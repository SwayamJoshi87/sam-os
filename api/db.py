"""SQLite connection helpers — read from SAMOS_DB_PATH env var."""
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(os.environ.get("SAMOS_DB_PATH", "/data/schedule.db"))


@contextmanager
def get_conn():
    """Yield a sqlite3 connection. Commits on success, rolls back on error."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Apply migrations from scripts/sql/*.sql in order. Idempotent."""
    sql_dir = Path(__file__).parent.parent / "scripts" / "sql"
    if not sql_dir.exists():
        return
    for sql_file in sorted(sql_dir.glob("*.sql")):
        with get_conn() as conn:
            conn.executescript(sql_file.read_text())
