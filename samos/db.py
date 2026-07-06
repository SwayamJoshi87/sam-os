"""SQLite connection helpers and migration runner."""

import os
import sqlite3
import traceback
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("SAMOS_DB_PATH", "/home/server/data/schedule.db"))


class SamosError(Exception):
    """Base exception for sam-os domain errors."""

    def __init__(self, message: str, error_type: str = "internal", details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}


class NotFoundError(SamosError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, "not_found", details)


class ValidationError(SamosError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, "validation", details)


class ConflictError(SamosError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, "conflict", details)


@contextmanager
def get_conn():
    """Yield a sqlite3 connection. Commits on success, rolls back on error."""
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
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


def _ok(data):
    return {"ok": True, "data": data}


def _err(e: Exception):
    if isinstance(e, SamosError):
        return {"ok": False, "error": {"type": e.error_type, "message": e.message, "details": e.details}}
    return {"ok": False, "error": {"type": "internal", "message": str(e), "details": {}}}


def _handle(fn, *args, **kwargs):
    try:
        return _ok(fn(*args, **kwargs))
    except Exception as e:
        traceback.print_exc()
        return _err(e)


def init_db():
    """Apply migrations from scripts/sql/*.sql, scripts/sql/core/*.sql, and samos/modules/*/migrations/*.sql in order."""
    sql_dir = Path(__file__).parent.parent / "scripts" / "sql"
    core_dir = sql_dir / "core"
    modules_dir = Path(__file__).parent / "modules"
    migration_dirs = [sql_dir, core_dir]
    if modules_dir.exists():
        for mod_dir in sorted(modules_dir.iterdir()):
            if mod_dir.is_dir():
                migs = mod_dir / "migrations"
                migs.mkdir(exist_ok=True)
                migration_dirs.append(migs)
    with get_conn() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        for mig_dir in migration_dirs:
            if not mig_dir.exists():
                continue
            for sql_file in sorted(mig_dir.glob("*.sql")):
                conn.executescript(sql_file.read_text())


def schema_and_counts() -> tuple:
    """Return (table_schemas, row_counts) from the live DB."""
    schema = []
    counts = {}
    try:
        with get_conn() as raw:
            for row in raw.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ):
                schema.append({"table": row["name"], "create_sql": row["sql"] or ""})
            for r in schema:
                tbl = r["table"]
                n = raw.execute(f"SELECT COUNT(*) AS n FROM {tbl}").fetchone()
                counts[tbl] = n["n"]
    except Exception as e:
        return ([{"error": str(e)}], {"error": str(e)})
    return schema, counts
