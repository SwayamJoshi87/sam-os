# sam-os

Personal operating system — schedule, gym, and nutrition tracking. Implemented as
an **MCP server** that Hermes (or any MCP client) launches over stdio.

## What it does

- **Schedule** — weekly template + per-day living instances (moves, skips, reasons)
- **Template management** — add/remove/update recurring tasks via MCP
- **Gym** — workout log + PR tracking (Epley 1RM)
- **Meals** — calorie/macro logging with daily target adherence + reusable meal templates
- **Wellness** — water, sleep, mood, and weight tracking
- **Productivity** — daily habits, shopping list, away mode, task notes
- **MCP tools** — Hermes calls `schedule_today`, `gym_log`, `meal_log`, etc.
- **Composite state** — `state://today` resource bundles schedule, gym, meals, wellness, habits, and shopping
- **Internal scheduler** — all cron jobs run inside the server process
- **Daily backup** to Neon Postgres (3am local time)

## Quick start (Docker — recommended)

```bash
git clone https://github.com/SwayamJoshi87/sam-os.git /home/server/sam-os
cd /home/server/sam-os

# Configure environment
cp .env.example .env
# Edit .env: SAMOS_DB_HOST_PATH, TZ, optional BACKUP_PG_DSN

# Build image
docker compose -f docker/docker-compose.yml --env-file .env build

# One-shot setup: generate Hermes config and seed starter template
.venv/bin/python scripts/setup.py run --docker --calendar-offline
# Or run setup inside the container:
# docker compose -f docker/docker-compose.yml --env-file .env run --rm sam-os python scripts/setup.py run --calendar-offline
```

The setup helper writes `~/.hermes/mcp.json` so Hermes can launch the container:

```json
{
  "mcpServers": {
    "sam-os": {
      "command": "docker",
      "args": [
        "compose",
        "-f", "/home/server/sam-os/docker/docker-compose.yml",
        "--env-file", "/home/server/sam-os/.env",
        "run", "--rm", "sam-os"
      ],
      "env": {
        "TZ": "America/Toronto",
        "SAMOS_CALENDAR_OFFLINE": "1"
      }
    }
  }
}
```

## Quick start (venv — alternative)

```bash
git clone https://github.com/SwayamJoshi87/sam-os.git /home/server/sam-os
cd /home/server/sam-os
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python scripts/setup.py run --calendar-offline
```

## Schedule model

- **Template** (`schedule_week`, `template_add`, `template_update`, `template_remove`, `template_reschedule`) — the recurring weekly plan.
- **Today instances** (`schedule_today`, `schedule_add_today`, `schedule_remove_today`, `schedule_retime_today`) — the editable schedule for the current day.

When something changes **today**, use the today-editing tools. When a change should be
**permanent**, use the template-management tools.

## Conflict resolution

`detect_conflicts` finds overlaps between your fixed tasks and iCloud calendar events
and returns **proposed resolutions**. The server never auto-moves a task — you choose
which resolution to apply with `schedule_resolve_conflict`.

## CLI wrappers

The same `samos` package is used by CLI scripts and the server:

```bash
# venv
.venv/bin/python scripts/schedule.py today
.venv/bin/python scripts/workout.py log office bench 135x10x3
.venv/bin/python scripts/meal_log.py log breakfast 500 30 40 20 eggs

# Docker
docker compose -f docker/docker-compose.yml --env-file .env run --rm sam-os python scripts/schedule.py today
```

## Verification

```bash
# e2e test suite (venv)
.venv/bin/python -m pytest tests/ -v

# Quick MCP stdio smoke test (venv)
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | .venv/bin/python -m samos.server

# CLI sanity checks
.venv/bin/python scripts/schedule.py today
.venv/bin/python scripts/workout.py prs
.venv/bin/python scripts/meal_log.py today
```

## Documentation

- [docs/tools.md](docs/tools.md) — MCP tool reference
- [docs/architecture.md](docs/architecture.md) — system design
- [docs/data-model.md](docs/data-model.md) — schema reference
- [docs/deployment.md](docs/deployment.md) — install, update, restore

## License

MIT. See [LICENSE](LICENSE).
