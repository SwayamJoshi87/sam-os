"""sam-os API — personal OS endpoints (schedule, gym, meals)."""
import os
import sqlite3
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException

from db import get_conn, init_db, DB_PATH

app = FastAPI(
    title="sam-os",
    description="Personal OS — schedule, gym, nutrition tracking",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    """Verify DB is reachable. Apply migrations if needed."""
    if not DB_PATH.exists():
        raise RuntimeError(
            f"Database not found at {DB_PATH}. "
            f"Set SAMOS_DB_PATH or bind-mount the volume."
        )
    init_db()


@app.get("/health")
def health():
    """Health check — verifies DB connectivity."""
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"status": "ok", "db": str(DB_PATH)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"db error: {e}")


def _read_env_file() -> dict:
    """Read .env from the bind-mounted repo (host's repo, not container's env).

    The api container doesn't see SAMOS_DB_HOST_PATH or BACKUP_PG_DSN because
    those are in the host's .env file. The user might want to verify what's
    configured at the host level.
    """
    # try mounted repo first, then host path as fallback
    for env_path in (Path("/app/repo/.env"), Path("/home/server/sam-os/.env")):
        if env_path.exists():
            out = {}
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    # mask the DSN password
                    if "DSN" in k.upper() or "PASSWORD" in k.upper():
                        v = "<redacted>" if v else "(empty)"
                    out[k.strip()] = v.strip()
            out["_source"] = str(env_path)
            return out
    return {"_error": ".env not found at /app/repo/.env or /home/server/sam-os/.env"}


def _walk_routes(app) -> list:
    """Get all routes via the OpenAPI schema (the source of truth).

    app.routes and app.router.routes only show routes registered directly
    on the main app, not those from included APIRouters. The OpenAPI spec
    contains the merged view that clients actually see.
    """
    out = []
    try:
        spec = app.openapi()
    except Exception:
        return out
    for path, methods in sorted(spec.get("paths", {}).items()):
        for m, op in methods.items():
            m = m.upper()
            if m == "HEAD":
                continue
            out.append({
                "method": m,
                "path": path,
                "summary": op.get("summary", "") or "",
                "tags": sorted(op.get("tags", []) or []),
            })
    return out


def _collect_routes() -> list:
    """Walk the full app router tree (includes mounted APIRouters)."""
    return _walk_routes(app)


def _schema_and_counts() -> tuple:
    """Return (table_schemas, row_counts) from the live DB."""
    schema = []
    counts = {}
    try:
        with sqlite3.connect(str(DB_PATH)) as raw:
            raw.row_factory = sqlite3.Row
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


@app.get("/help")
def help():
    """Self-describing help endpoint. Returns everything needed to operate
    sam-os without skills, IDE, or memory. Use this if telegram skills vanish
    or you need to onboard a fresh LLM session.

    Includes: routes summary, db schema, env vars, docker commands,
    CLI ↔ API mapping, sample bash invocations, recovery commands.
    """
    routes = _collect_routes()
    schema, counts = _schema_and_counts()
    host_env = _read_env_file()

    return {
        "service": {
            "name": "sam-os",
            "version": app.version,
            "title": app.title,
            "description": app.description,
            "started_at": datetime.now().isoformat(),
            "url": "http://localhost:8765",
            "openapi_docs": "http://localhost:8765/docs",
            "openapi_schema": "http://localhost:8765/openapi.json",
            "repo": "https://github.com/SwayamJoshi87/sam-os",
            "plan": "/home/server/.hermes/plans/2026-07-02_sam-os-api.md",
        },
        "data": {
            "sqlite_path_inside_container": str(DB_PATH),
            "sqlite_path_on_host": host_env.get("SAMOS_DB_HOST_PATH", "/home/server/data"),
            "row_counts": counts,
            "tables": schema,
        },
        "container_env": {
            "SAMOS_DB_PATH": str(DB_PATH),
            "TZ": os.environ.get("TZ", "(not set)"),
            "note": "BACKUP_PG_DSN and SAMOS_DB_HOST_PATH live in the host's .env file, not the container env. See 'host_env' below.",
        },
        "host_env": host_env,
        "docker": {
            "compose_file": "/home/server/sam-os/docker/docker-compose.yml",
            "env_file": "/home/server/sam-os/.env",
            "note": "Run these from the host, not from inside the api container (api has no docker CLI).",
            "commands": {
                "status": "docker ps --filter name=sam-os",
                "logs_api": "docker logs sam-os-api --tail 50",
                "logs_backup": "docker logs sam-os-backup --tail 50",
                "restart_api": "cd /home/server/sam-os && docker compose -f docker/docker-compose.yml --env-file .env restart api",
                "restart_backup": "cd /home/server/sam-os && docker compose -f docker/docker-compose.yml --env-file .env restart backup",
                "rebuild": "cd /home/server/sam-os && docker compose -f docker/docker-compose.yml --env-file .env build && docker compose -f docker/docker-compose.yml --env-file .env up -d",
                "stop_all": "cd /home/server/sam-os && docker compose -f docker/docker-compose.yml --env-file .env down",
            },
        },
        "cli_to_api_mapping": {
            "schedule": [
                ("schedule.py today", "GET /api/schedule/today"),
                ("schedule.py week", "GET /api/schedule/week"),
                ("schedule.py did <task>", "POST /api/schedule/did/{task_name}"),
                ("schedule.py skip <task> <reason>", "POST /api/schedule/skip/{task_name}?reason=..."),
                ("schedule.py push <task> <day>", "POST /api/schedule/push/{task_name}/{day}"),
                ("schedule.py push <task> <day> --permanent", "POST /api/schedule/push/{task_name}/{day}?permanent=true"),
                ("schedule.py history", "GET /api/schedule/history"),
                ("schedule.py stats", "GET /api/schedule/stats"),
            ],
            "gym": [
                ("workout.py log <gym> <ex> <wt>x<rep>[x<sets>]", "POST /api/gym/log (JSON: {gym, entries:[{exercise,weight,reps,sets}]})"),
                ("workout.py prs", "GET /api/gym/prs"),
                ("workout.py prs <gym>", "GET /api/gym/prs?gym=..."),
                ("workout.py recent <days>", "GET /api/gym/recent?days=..."),
            ],
            "meals": [
                ("meal_log.py log <type> <cals> [P] [C] [F] [desc]", "POST /api/meals/log (JSON)"),
                ("meal_log.py target <cals> [P] [C] [F]", "POST /api/meals/target (JSON)"),
                ("meal_log.py today", "GET /api/meals/today"),
                ("meal_log.py week", "GET /api/meals/week"),
            ],
        },
        "cli_locations": {
            "schedule": "/home/server/.hermes/scripts/schedule.py",
            "workout": "/home/server/.hermes/scripts/workout.py",
            "meal_log": "/home/server/.hermes/scripts/meal_log.py",
            "shared_lib": "/home/server/.hermes/scripts/schedule_lib.py",
        },
        "crons": {
            "8am-briefing": "0 8 * * * — daily morning briefing (weather + calendar + email + schedule)",
            "8pm-gym-check": "0 20 * * * — pings if gym not logged on gym days",
            "8am-instantiate-today": "0 8 * * * — copies today's template tasks into today_instances",
            "midnight-eod-sweep": "0 0 * * * — converts lingering pending instances to skipped",
            "schedule-conflict-detector": "*/30 8-20 * * * — checks calendar for task overlaps",
            "sunday-review": "0 20 * * 0 — weekly stats summary",
            "list_command": "hermes cron list",
        },
        "conventions": {
            "timezone": "America/Toronto (TZ env var)",
            "date_format": "YYYY-MM-DD",
            "day_of_week": "0=mon, 1=tue, 2=wed, 3=thu, 4=fri, 5=sat, 6=sun",
            "status_enum": ["pending", "done", "skipped", "moved"],
            "meal_type_enum": ["breakfast", "lunch", "dinner", "snack"],
            "categories": ["gym", "work", "meal_prep", "commute", "free", "language"],
            "pr_formula": "epley_1rm = weight * (1 + reps/30)",
        },
        "fallback_strategy": {
            "skills_disappear": "curl http://localhost:8765/help to get this dump again",
            "api_container_down": "use CLI scripts directly (no docker needed), they read the same sqlite",
            "backup_failed": "check `docker logs sam-os-backup`. SQLite is the source of truth, backup is best-effort.",
            "sqlite_corrupted": "Neon Postgres has the last good copy. Restore via docs/deployment.md → 'Restoring from a postgres backup' section.",
        },
        "endpoints": routes,
    }


# Routers added in subsequent tasks
from schedule_router import router as schedule_router  # noqa: E402
from gym_router import router as gym_router  # noqa: E402
from meals_router import router as meals_router  # noqa: E402

app.include_router(schedule_router, prefix="/api/schedule", tags=["schedule"])
app.include_router(gym_router, prefix="/api/gym", tags=["gym"])
app.include_router(meals_router, prefix="/api/meals", tags=["meals"])
