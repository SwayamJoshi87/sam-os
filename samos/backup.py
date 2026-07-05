"""Daily backup: SQLite → remote PostgreSQL."""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from .db import DB_PATH

SYNC_TABLES = [
    "categories",
    "tasks",
    "today_instances",
    "workouts",
    "prs",
    "meals",
    "daily_targets",
    "schedule_log",
]


def _pg_dsn() -> str:
    if os.environ.get("BACKUP_PG_DSN"):
        return os.environ["BACKUP_PG_DSN"]
    required = ["BACKUP_PG_HOST", "BACKUP_PG_DB", "BACKUP_PG_USER", "BACKUP_PG_PASSWORD"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Backup disabled: missing {', '.join(missing)}")
    return (
        f"host={os.environ['BACKUP_PG_HOST']} "
        f"port={os.environ.get('BACKUP_PG_PORT', '5432')} "
        f"dbname={os.environ['BACKUP_PG_DB']} "
        f"user={os.environ['BACKUP_PG_USER']} "
        f"password={os.environ['BACKUP_PG_PASSWORD']} "
        f"sslmode={os.environ.get('BACKUP_PG_SSLMODE', 'require')}"
    )


def init_pg_schema():
    """Apply pg_schema.sql to remote postgres. Idempotent."""
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed, skipping backup")
        return False

    schema_path = Path(__file__).parent.parent / "backup" / "pg_schema.sql"
    if not schema_path.exists():
        print(f"pg_schema.sql not found at {schema_path}, skipping backup")
        return False

    schema_sql = schema_path.read_text()
    conn = psycopg2.connect(_pg_dsn())
    try:
        with conn.cursor() as c:
            c.execute(schema_sql)
        conn.commit()
        print("  pg schema verified/applied")
        return True
    finally:
        conn.close()


def sync_table(sqlite_conn, pg_conn, table):
    cur = sqlite_conn.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    if not rows:
        print(f"  {table}: empty, skipping")
        return 0
    import psycopg2.extras

    cols = [d[0] for d in cur.description]
    pg_cols = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c != "id")
    sql = f"INSERT INTO {table} ({pg_cols}) VALUES ({placeholders}) ON CONFLICT (id) DO UPDATE SET {updates}"
    with pg_conn.cursor() as c:
        psycopg2.extras.execute_batch(c, sql, [tuple(r) for r in rows])
    pg_conn.commit()
    return len(rows)


def do_backup():
    print(f"[{datetime.now().isoformat()}] starting backup from {DB_PATH}")
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed, backup disabled")
        return

    sqlite_conn = sqlite3.connect(str(DB_PATH))
    sqlite_conn.row_factory = sqlite3.Row
    try:
        if not init_pg_schema():
            return
        pg_conn = psycopg2.connect(_pg_dsn())
        try:
            for table in SYNC_TABLES:
                try:
                    n = sync_table(sqlite_conn, pg_conn, table)
                    print(f"  {table}: {n} rows synced")
                except Exception as e:
                    print(f"  {table}: ERROR {e}")
            print("backup complete")
        finally:
            pg_conn.close()
    finally:
        sqlite_conn.close()
