"""Setup, configuration, backup, and system helpers for sam-os."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from samos.calendar import CALDAV_URL, _creds
from samos.db import DB_PATH, get_conn
from samos.modules.schedule.models import add_category, template_add

REPO_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
ENV_PATH = HERMES_HOME / ".env"
DOCKER_COMPOSE = REPO_ROOT / "docker" / "docker-compose.yml"
ENV_EXAMPLE = REPO_ROOT / ".env.example"

SYNC_TABLES = [
    "categories",
    "tasks",
    "today_instances",
    "workouts",
    "prs",
    "meals",
    "daily_targets",
    "schedule_log",
    "water_log",
    "sleep_log",
    "mood_log",
    "habits",
    "habit_logs",
    "shopping_items",
    "away_dates",
    "task_notes",
    "meal_templates",
    "backup_runs",
]


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

def _docker_available() -> bool:
    """Return True if docker appears usable on this host."""
    return shutil.which("docker") is not None


def _venv_python() -> Path | None:
    """Best-effort detection of the project virtualenv python executable."""
    candidates = [
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
        REPO_ROOT / ".venv" / "bin" / "python",
        REPO_ROOT / "venv" / "Scripts" / "python.exe",
        REPO_ROOT / "venv" / "bin" / "python",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _hermes_config_path() -> Path:
    return HERMES_HOME / "mcp.json"


def _read_hermes_env(key: str) -> str:
    """Read a key from the Hermes .env file if it exists."""
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip("\"'")
    return ""


def _ensure_db_schema():
    """Apply migrations if the DB/schema is missing."""
    try:
        from samos.db import init_db

        init_db()
    except Exception:
        pass


def setup_check(use_docker: bool = False) -> dict:
    """Verify prerequisites for running sam-os. Safe to call before full setup."""
    _ensure_db_schema()
    checks = {
        "repo_root": str(REPO_ROOT),
        "deployment": "docker" if use_docker else "venv",
        "docker_available": _docker_available(),
        "docker_compose_present": DOCKER_COMPOSE.exists(),
        "env_example_present": ENV_EXAMPLE.exists(),
        "venv_present": False,
        "venv_python": None,
        "deps_importable": False,
        "db_path": str(DB_PATH),
        "db_dir_exists": DB_PATH.parent.exists(),
        "db_dir_writable": False,
        "hermes_home": str(HERMES_HOME),
        "hermes_env_present": ENV_PATH.exists(),
        "icloud_username": "",
        "icloud_app_password_present": False,
        "hermes_config_present": _hermes_config_path().exists(),
        "pg_dsn_present": bool(os.environ.get("BACKUP_PG_DSN")),
        "calendar_offline": os.environ.get("SAMOS_CALENDAR_OFFLINE") == "1",
        "template_populated": False,
        "issues": [],
    }

    venv_python = _venv_python()
    if venv_python:
        checks["venv_present"] = True
        checks["venv_python"] = str(venv_python)

    # Test DB writability without requiring a valid DB file.
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        test_file = DB_PATH.parent / ".samos_write_test"
        test_file.write_text("ok")
        test_file.unlink()
        checks["db_dir_writable"] = True
    except Exception as e:
        checks["issues"].append(f"DB directory not writable: {e}")

    # Test core imports.
    try:
        import mcp  # noqa: F401
        import apscheduler  # noqa: F401

        checks["deps_importable"] = True
    except Exception as e:
        checks["issues"].append(f"Missing Python dependencies: {e}")

    # iCloud credentials.
    checks["icloud_username"] = (
        os.environ.get("ICLOUD_USERNAME") or _read_hermes_env("ICLOUD_USERNAME")
    )
    checks["icloud_app_password_present"] = bool(
        os.environ.get("ICLOUD_APP_PASSWORD") or _read_hermes_env("ICLOUD_APP_PASSWORD")
    )

    if not checks["calendar_offline"]:
        if not checks["icloud_app_password_present"]:
            checks["issues"].append(
                "iCloud app password missing; set SAMOS_CALENDAR_OFFLINE=1 or add ICLOUD_APP_PASSWORD to ~/.hermes/.env"
            )

    # Template population.
    try:
        with get_conn() as c:
            n = c.execute("SELECT COUNT(*) AS n FROM tasks WHERE day_of_week BETWEEN 0 AND 6").fetchone()["n"]
            checks["template_populated"] = n > 0
    except Exception as e:
        checks["issues"].append(f"Could not read template state: {e}")

    if use_docker:
        checks["ready_to_run"] = (
            checks["docker_available"]
            and checks["docker_compose_present"]
            and checks["db_dir_writable"]
            and (checks["calendar_offline"] or checks["icloud_app_password_present"])
        )
    else:
        checks["ready_to_run"] = (
            checks["venv_present"]
            and checks["deps_importable"]
            and checks["db_dir_writable"]
            and (checks["calendar_offline"] or checks["icloud_app_password_present"])
        )

    return checks


def write_hermes_config(
    output_path: str | None = None,
    db_path: str | None = None,
    tz: str | None = None,
    calendar_offline: bool | None = None,
    use_docker: bool = False,
) -> dict:
    """Generate a Hermes mcp.json config for this installation."""
    target = Path(output_path) if output_path else _hermes_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    tz_value = tz or os.environ.get("TZ", "America/Toronto")
    offline = (
        "1"
        if calendar_offline is True or os.environ.get("SAMOS_CALENDAR_OFFLINE") == "1"
        else "0"
    )

    if use_docker:
        compose_file = str(DOCKER_COMPOSE)
        env_file = str(REPO_ROOT / ".env")
        config = {
            "mcpServers": {
                "sam-os": {
                    "command": "docker",
                    "args": [
                        "compose",
                        "-f",
                        compose_file,
                        "--env-file",
                        env_file,
                        "run",
                        "--rm",
                        "sam-os",
                    ],
                    "env": {
                        "TZ": tz_value,
                        "SAMOS_CALENDAR_OFFLINE": offline,
                    },
                }
            }
        }
    else:
        venv_python = _venv_python()
        if not venv_python:
            raise RuntimeError("no virtualenv found; create .venv first")

        db = db_path or str(DB_PATH)
        config = {
            "mcpServers": {
                "sam-os": {
                    "command": str(venv_python),
                    "args": ["-u", "-m", "samos.server"],
                    "env": {
                        "SAMOS_DB_PATH": db,
                        "TZ": tz_value,
                        "PYTHONIOENCODING": "utf-8",
                        "SAMOS_CALENDAR_OFFLINE": offline,
                    },
                }
            }
        }

    target.write_text(json.dumps(config, indent=2) + "\n")
    return {"written_to": str(target), "config": config, "deployment": "docker" if use_docker else "venv"}


def seed_template() -> dict:
    """Create a minimal starter weekly template so first run is not empty."""
    _ensure_db_schema()

    # Idempotent: only seed if template is empty.
    with get_conn() as c:
        existing = c.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE day_of_week BETWEEN 0 AND 6"
        ).fetchone()["n"]
        if existing > 0:
            return {"seeded": False, "reason": "template already populated"}

    categories = [
        ("gym", "#e74c3c"),
        ("work", "#3498db"),
        ("personal", "#2ecc71"),
        ("meal_prep", "#f39c12"),
    ]
    for name, color in categories:
        try:
            add_category(name, color)
        except Exception:
            pass

    starter = [
        ("morning gym", "mon", "07:00", 60, "gym", True),
        ("focus block", "mon", "09:00", 120, "work", True),
        ("lunch", "mon", "12:00", 60, "personal", False),
        ("evening review", "mon", "20:00", 30, "personal", False),
        ("morning gym", "wed", "07:00", 60, "gym", True),
        ("focus block", "wed", "09:00", 120, "work", True),
        ("lunch", "wed", "12:00", 60, "personal", False),
        ("morning gym", "fri", "07:00", 60, "gym", True),
        ("focus block", "fri", "09:00", 120, "work", True),
        ("meal prep", "sun", "16:00", 60, "meal_prep", False),
    ]

    added = []
    for name, day, time, duration, category, fixed in starter:
        try:
            result = template_add(name, day, time, duration, category, fixed)
            added.append(result)
        except Exception as e:
            return {"seeded": False, "error": str(e), "added": added}

    return {"seeded": True, "tasks_added": len(added), "tasks": added}


def verify_calendar_credentials() -> dict:
    """Test iCloud CalDAV connectivity and return a clear report."""
    result = {
        "offline": os.environ.get("SAMOS_CALENDAR_OFFLINE") == "1",
        "username": "",
        "app_password_present": False,
        "caldav_package_installed": False,
        "icalendar_package_installed": False,
        "principal_accessible": False,
        "calendars_found": 0,
        "can_create_calendar": False,
        "errors": [],
    }

    if result["offline"]:
        return result

    try:
        import caldav  # noqa: F401

        result["caldav_package_installed"] = True
    except Exception as e:
        result["errors"].append(f"caldav package not installed: {e}")
        return result

    try:
        import icalendar  # noqa: F401

        result["icalendar_package_installed"] = True
    except Exception as e:
        result["errors"].append(f"icalendar package not installed: {e}")

    user, pwd = _creds()
    result["username"] = user
    result["app_password_present"] = bool(pwd)

    if not pwd:
        result["errors"].append(
            "iCloud app password missing. Set ICLOUD_APP_PASSWORD in ~/.hermes/.env or env."
        )
        return result

    try:
        client = caldav.DAVClient(url=CALDAV_URL, username=user, password=pwd)
        principal = client.principal()
        result["principal_accessible"] = True
        calendars = principal.calendars()
        result["calendars_found"] = len(calendars)
        # Test calendar creation permission with a throwaway name.
        test_name = "samos-test-calendar"
        try:
            test_cal = principal.make_calendar(name=test_name, cal_id=f"samos-{test_name}")
            test_cal.delete()
            result["can_create_calendar"] = True
        except Exception as e:
            result["errors"].append(f"Cannot create/delete test calendar: {e}")
    except Exception as e:
        result["errors"].append(f"CalDAV connection failed: {e}")

    result["valid"] = (
        result["principal_accessible"] and result["app_password_present"] and not result["errors"]
    )
    return result


def run_setup(
    write_hermes: bool = True,
    seed_template_flag: bool = True,
    calendar_offline: bool = False,
    use_docker: bool = False,
) -> dict:
    """One-shot setup routine: check, write config, seed template, verify calendar."""
    results = {
        "check": setup_check(use_docker=use_docker),
        "hermes_config": None,
        "template": None,
        "calendar": None,
    }

    if write_hermes:
        results["hermes_config"] = write_hermes_config(
            calendar_offline=calendar_offline, use_docker=use_docker
        )

    if seed_template_flag:
        results["template"] = seed_template()

    results["calendar"] = verify_calendar_credentials()

    return results


# ---------------------------------------------------------------------------
# Backup helpers
# ---------------------------------------------------------------------------

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

    schema_path = REPO_ROOT / "backup" / "pg_schema.sql"
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


def _record_backup(status: str, details: str | None = None, rows_synced: int = 0):
    try:
        with get_conn() as c:
            c.execute(
                "INSERT INTO backup_runs (status, details, rows_synced) VALUES (?, ?, ?)",
                (status, details, rows_synced),
            )
    except Exception as e:
        print(f"  could not record backup status: {e}")


def backup_status(days: int = 7) -> dict:
    """Return recent backup run status."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with get_conn() as c:
            total = c.execute(
                "SELECT COUNT(*) AS n FROM backup_runs WHERE started_at >= ?",
                (since,),
            ).fetchone()["n"]
            last = c.execute(
                "SELECT * FROM backup_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            failures = c.execute(
                "SELECT COUNT(*) AS n FROM backup_runs WHERE started_at >= ? AND status='failed'",
                (since,),
            ).fetchone()["n"]
        return {
            "total_runs": total,
            "failed_runs": failures,
            "last_run": dict(last) if last else None,
        }
    except Exception as e:
        return {"error": str(e)}


def do_backup():
    print(f"[{datetime.now().isoformat()}] starting backup from {DB_PATH}")
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed, backup disabled")
        _record_backup("failed", "psycopg2 not installed")
        return

    _record_backup("running")
    run_id = None
    try:
        with get_conn() as c:
            run_id = c.execute(
                "SELECT id FROM backup_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()["id"]
    except Exception:
        pass

    sqlite_conn = sqlite3.connect(str(DB_PATH))
    sqlite_conn.row_factory = sqlite3.Row
    total_rows = 0
    try:
        if not init_pg_schema():
            _record_backup("failed", "could not initialize pg schema")
            return
        pg_conn = psycopg2.connect(_pg_dsn())
        try:
            for table in SYNC_TABLES:
                try:
                    n = sync_table(sqlite_conn, pg_conn, table)
                    total_rows += n
                    print(f"  {table}: {n} rows synced")
                except Exception as e:
                    print(f"  {table}: ERROR {e}")
            _record_backup("success", "backup complete", total_rows)
            if run_id is not None:
                try:
                    with get_conn() as c:
                        c.execute(
                            "UPDATE backup_runs SET finished_at=CURRENT_TIMESTAMP WHERE id=?",
                            (run_id,),
                        )
                except Exception:
                    pass
            print("backup complete")
        finally:
            pg_conn.close()
    except Exception as e:
        _record_backup("failed", str(e))
        print(f"backup failed: {e}")
        raise
    finally:
        sqlite_conn.close()
