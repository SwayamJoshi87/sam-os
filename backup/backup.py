"""Daily backup: SQLite → remote PostgreSQL.

Reads from the SQLite bind mount, syncs to Postgres. Idempotent — uses
upserts on tables with natural primary keys. Run once on startup, then
scheduled at 3am local time via APScheduler.

Tables synced:
  - categories, tasks, today_instances, workouts, prs, meals,
    daily_targets, schedule_log

Environment:
  SAMOS_DB_PATH  — path to SQLite (default: /data/schedule.db)
  BACKUP_PG_DSN  — full postgres connection string (preferred)
  BACKUP_PG_HOST, BACKUP_PG_PORT, BACKUP_PG_DB,
  BACKUP_PG_USER, BACKUP_PG_PASSWORD — fallback individual vars
  BACKUP_PG_SSLMODE — default 'require' for Neon serverless
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
from apscheduler.schedulers.blocking import BlockingScheduler

DB_PATH = Path(os.environ.get("SAMOS_DB_PATH", "/data/schedule.db"))

# Prefer full DSN if set, otherwise build from individual vars
PG_DSN = os.environ.get("BACKUP_PG_DSN") or (
    f"host={os.environ['BACKUP_PG_HOST']} "
    f"port={os.environ.get('BACKUP_PG_PORT', '5432')} "
    f"dbname={os.environ['BACKUP_PG_DB']} "
    f"user={os.environ['BACKUP_PG_USER']} "
    f"password={os.environ['BACKUP_PG_PASSWORD']} "
    f"sslmode={os.environ.get('BACKUP_PG_SSLMODE', 'require')}"
)

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


def init_pg_schema():
    """Apply pg_schema.sql to remote postgres. Idempotent."""
    schema_path = Path(__file__).parent / "pg_schema.sql"
    schema_sql = schema_path.read_text()
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn.cursor() as c:
            c.execute(schema_sql)
        conn.commit()
        print("  pg schema verified/applied")
    finally:
        conn.close()


def sync_table(sqlite_conn, pg_conn, table):
    """Read all rows from SQLite, upsert into Postgres."""
    cur = sqlite_conn.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    if not rows:
        print(f"  {table}: empty, skipping")
        return 0
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
    sqlite_conn = sqlite3.connect(str(DB_PATH))
    sqlite_conn.row_factory = sqlite3.Row
    try:
        # Ensure target schema exists (idempotent, fast on subsequent runs)
        init_pg_schema()
        pg_conn = psycopg2.connect(PG_DSN)
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


if __name__ == "__main__":
    # Run once on startup, then schedule daily at 3am
    do_backup()
    scheduler = BlockingScheduler()
    scheduler.add_job(do_backup, "cron", hour=3, minute=0)
    print("backup scheduler running, next at 3am")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
