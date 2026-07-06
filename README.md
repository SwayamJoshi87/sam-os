# sam-os

Personal operating system — schedule, gym, and nutrition tracking. Now an
**MCP server** that Hermes (or any MCP client) can launch and call directly.

## What it does

- **Schedule** — weekly template + per-day living instances (moves, skips, reasons)
- **Template management** — add/remove/update recurring tasks via MCP
- **Gym** — workout log + PR tracking (Epley 1RM)
- **Meals** — calorie/macro logging with daily target adherence + reusable meal templates
- **Wellness** — water, sleep, mood, and weight tracking
- **Productivity** — daily habits, shopping list, away mode, task notes
- **MCP tools** — Hermes calls `schedule_today`, `gym_log`, `meal_log`, etc.
- **Composite state** — `state://today` resource bundles schedule, gym, meals, wellness, habits, and shopping
- **Internal scheduler** — all old cron jobs run inside the server process
- **Daily backup** to Neon Postgres (3am local time)

## Quick start

```bash
git clone https://github.com/SwayamJoshi87/sam-os.git /home/server/sam-os
cd /home/server/sam-os
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Optional: one-shot setup (writes Hermes config and seeds a starter template)
.venv/bin/python scripts/setup.py run --calendar-offline

# Or do it step by step:
.venv/bin/python scripts/setup.py check
.venv/bin/python scripts/setup.py hermes --calendar-offline
.venv/bin/python scripts/setup.py seed
```

Tell Hermes to launch the server via `hermes/mcp.json`:

```json
{
  "mcpServers": {
    "sam-os": {
      "command": "/home/server/sam-os/.venv/bin/python",
      "args": ["-u", "-m", "samos.server"],
      "env": {
        "SAMOS_DB_PATH": "/home/server/data/schedule.db",
        "TZ": "America/Toronto",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
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

## CLI wrappers (optional)

The old CLI scripts still work and use the same `samos` package:

```bash
.venv/bin/python scripts/schedule.py today
.venv/bin/python scripts/workout.py log office bench 135x10x3
.venv/bin/python scripts/meal_log.py log breakfast 500 30 40 20 eggs
```

## Docker

Build the image:

```bash
docker compose -f docker/docker-compose.yml --env-file .env build
```

Run the MCP server in attached stdio mode:

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm sam-os
```

Because MCP stdio needs a persistent stdin/stdout pipe, production deployments usually
run the server directly (see Quick start) and use Docker only for packaging/testing.

## Verification

```bash
# Run the e2e test suite (each test spins up a real MCP server subprocess)
.venv/bin/python -m pytest tests/ -v

# Quick MCP stdio smoke test
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
