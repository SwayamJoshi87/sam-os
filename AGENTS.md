# Agent Guide for sam-os

This repo is a personal OS for schedule, gym, and meal tracking. It is implemented
as a Python MCP server (`samos/server.py`) that Hermes launches over stdio.

## Architecture

- `samos/` — core package
  - `server.py` — MCP server entrypoint; exposes tools/resources and runs APScheduler
  - `schedule.py` — template + today_instances logic, including ad-hoc today editing
  - `gym.py` — workout logging and PR tracking
  - `meals.py` — meal logging, daily targets, and meal templates
  - `calendar.py` — iCloud CalDAV sync + conflict detection
  - `backup.py` — SQLite → Postgres sync + backup status tracking
  - `wellness.py` — water, sleep, mood, and weight tracking
  - `productivity.py` — habits, shopping list, away mode, task notes
  - `insights.py` — composite `state://today` and weekly prep summaries
  - `setup.py` — first-run / agent setup helpers
  - `db.py` — SQLite connection, migrations, and exception types
- `scripts/` — thin CLI wrappers around `samos.*`
- `scripts/setup.py` — standalone CLI for setup, config, and credential verification
- `scripts/sql/*.sql` — idempotent SQLite migrations, applied on server startup
- `backup/pg_schema.sql` — Postgres target schema
- `docker/` — Dockerfile and compose file for containerized deployment
- `hermes/mcp.json` — sample Hermes MCP config

## Agent setup checklist

When setting up sam-os for the first time, run these steps in order.

### Docker deployment (recommended)

1. **Clone and configure**
   ```bash
   git clone https://github.com/SwayamJoshi87/sam-os.git /home/server/sam-os
   cd /home/server/sam-os
   cp .env.example .env
   # Edit .env: SAMOS_DB_HOST_PATH, TZ, optional BACKUP_PG_DSN
   ```

2. **Build image**
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env build
   ```

3. **Run setup inside the container**
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env run --rm sam-os \
     python scripts/setup.py run --calendar-offline
   ```
   or from the host if Python is available:
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/python scripts/setup.py run --docker --calendar-offline
   ```

4. **Verify prerequisites**
   ```bash
   .venv/bin/python scripts/setup.py check --docker
   ```
   or via MCP: `setup_check_tool(use_docker=true)`

5. **(Optional) Verify iCloud calendar credentials**
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env run --rm sam-os \
     python scripts/setup.py calendar
   ```
   or via MCP: `setup_verify_calendar()`

### venv deployment (alternative)

1. **Create the virtualenv and install dependencies**
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. **Run full setup**
   ```bash
   .venv/bin/python scripts/setup.py run --calendar-offline
   ```

3. **Verify**
   ```bash
   .venv/bin/python scripts/setup.py check
   ```
   or via MCP: `setup_check_tool()`

## How to run

Local venv:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
SAMOS_DB_PATH=/home/server/data/schedule.db .venv/bin/python -m samos.server
```

Quick smoke test:

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\n' | .venv/bin/python -m samos.server
```

Docker:

```bash
docker compose -f docker/docker-compose.yml --env-file .env build
docker compose -f docker/docker-compose.yml --env-file .env run --rm sam-os
```

## Key design rules

- **SQLite is the source of truth.** Postgres backup is read-only.
- **Schedule has two layers:**
  - Template = recurring weekly plan in `tasks`.
  - Today instances = editable living schedule in `today_instances`.
- **Today changes only touch today instances.** Use `schedule_add_today`,
  `schedule_remove_today`, `schedule_retime_today`. Permanent changes use
  `template_reschedule` or `schedule_push(..., permanent=True)`.
- **Conflicts are collaborative.** `detect_conflicts` proposes resolutions but
  never auto-applies them. The user chooses via `schedule_resolve_conflict`.
- **All tools return structured results:**
  - Success: `{"ok": true, "data": ...}`
  - Failure: `{"ok": false, "error": {"type": ..., "message": ..., "details": ...}}`

## Adding a new tool

1. Add the domain function in the appropriate `samos/*.py` module.
2. Wrap it with `_handle(fn, ...)` in `samos/server.py` to get consistent error handling.
3. Decorate with `@mcp.tool()` and write a clear docstring — that docstring becomes
   the tool description Hermes sees.
4. Update `docs/tools.md`.

## Testing

Run the full test suite:

```bash
.venv/bin/python -m pytest tests/ -v
```

Tests are end-to-end over stdio: each test starts a real `samos.server`
subprocess, sends JSON-RPC messages, and asserts the returned tool results.

Manual smoke test:

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\n' | .venv/bin/python -m samos.server
```

CLI sanity checks:

```bash
.venv/bin/python scripts/schedule.py today
.venv/bin/python scripts/workout.py prs
.venv/bin/python scripts/meal_log.py today
```

## Environment variables

See `.env.example`. Key vars:

- `SAMOS_DB_PATH` — path to SQLite inside container (default `/data/schedule.db`)
- `SAMOS_DB_HOST_PATH` — host directory bind-mounted into container
- `BACKUP_PG_DSN` — Postgres backup connection string
- `TZ` — timezone for cron triggers
- `SAMOS_CALENDAR_OFFLINE=1` — skip iCloud CalDAV reads/writes
- `HERMES_HOME` — path to `~/.hermes` for iCloud credentials

## Common pitfalls

- If the server fails with "unable to open database file", the process cannot
  write to `SAMOS_DB_PATH`'s parent directory. Fix host permissions.
- On Windows, set `PYTHONIOENCODING=utf-8` to avoid emoji encoding errors in
  CLI scripts.
- The container runs as uid 1000. The host bind-mount directory must be writable
  by that uid.
