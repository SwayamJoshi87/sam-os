# Architecture

## Component diagram

```
┌────────────────────────────────────────────┐
│  Host (your machine)                       │
│                                            │
│  /home/server/data/schedule.db  ← SQLite   │
│  /home/server/sam-os/           ← git repo │
│       └── samos/server.py       ← MCP      │
│       └── samos/modules/        ← domain   │
│       └── samos/graph.py        ← graph    │
└────────────────┬───────────────────────────┘
                 │
                 │ Hermes launches stdio subprocess
                 │   .venv/bin/python -m samos.server
                 ▼
┌────────────────────────────────────────────┐
│  Hermes / MCP client                       │
│  Calls tools: schedule_today, gym_log,     │
│               meal_log, detect_conflicts,  │
│               agent_briefing_tool, ...     │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│  Docker (optional packaging)               │
│  sam-os image runs the same MCP server     │
│  with stdin/stdout attached                │
└────────────────────────────────────────────┘
                                   │ TLS
                                   ▼
                        ┌─────────────────────┐
                        │  Neon Postgres      │
                        │  (serverless)       │
                        └─────────────────────┘
```

## Data flow

1. **Hermes** launches `python -m samos.server` as a stdio subprocess.
2. **MCP server** loads domain modules via `samos.registry`, exposes their tools/resources, and runs an internal APScheduler for cron jobs.
3. **Reads/writes** go to the bind-mounted SQLite file.
4. **Backup job** runs at 3am, reads the same SQLite, syncs to Neon Postgres.
5. **No data in containers** — only code + ephemeral process state.

## Module system

`samos/registry.py` discovers every package under `samos/modules/`. Each module declares a `MODULE` manifest with:

- `name`, `display_name`, `description`
- `required_env` / `optional_env`
- `tools`, `resources`, `scheduler_jobs`
- a `migrations/` directory

Modules are disabled at startup when required env vars are missing, so optional integrations (email, weather) stay out of the tool list until configured.

## Core graph store

`samos/graph.py` provides a small knowledge graph on top of SQLite:

- `entities` — typed nodes (people, projects, topics, ...)
- `observations` — timestamped facts attached to entities
- `relationships` — typed edges between entities
- `events` — an append-only audit log

Personal-context modules write to their own optimized tables and can feed the graph store so agents can query across all of them.

## Personal context modules

`samos/modules/{todos,notes,journal,memories,projects,profile}/` store action items, notes, journal entries, remembered facts, projects, and user preferences. They are always enabled.

## External integrations

`samos/modules/email/` (IMAP/SMTP) and `samos/modules/weather/` (OpenWeatherMap) are optional. They register tools only when their credentials are present in the environment.

## Agent interface

`samos/modules/agent/` exposes read-only aggregation tools (`agent_context_tool`, `agent_query_tool`, `agent_search_tool`, `agent_briefing_tool`) plus `agent_remember_tool` for storing facts. sam-os owns the state and the query tools; Hermes/LLM owns reasoning and orchestration.

## Why MCP instead of REST

- Hermes already supports stdio MCP servers.
- One process replaces FastAPI + CLI scripts + AI-side cron jobs.
- Tool descriptions become the API contract, discoverable by the LLM.
- No need to maintain OpenAPI specs or REST clients.

## Why SQLite on the host, not in a Docker volume

- Container restarts never lose data (`docker rm -f` is safe).
- `docker compose up` after a config change keeps the DB intact.
- Backup reads from the same source the server writes to (no drift).
- Easy to inspect from the host: `sqlite3 /home/server/data/schedule.db`.

## Internal scheduler

APScheduler runs these jobs in a background thread inside the MCP server:

| Cron | Job |
|---|---|
| `0 8 * * *` | Instantiate today's instances + iCloud calendar push |
| `0 20 * * *` | Gym check |
| `0 0 * * *` | EOD sweep (pending → skipped) |
| `*/30 8-20 * * *` | Calendar conflict detection (logs only, never auto-moves) |
| `0 20 * * 0` | Sunday review |
| `0 3 * * *` | Postgres backup sync |

## Today vs template

- **Template** = the recurring weekly plan stored in `tasks`.
- **Today instances** = per-day reality stored in `today_instances`.

Ad-hoc changes today should only touch `today_instances`. Permanent changes should
rewrite the template.

Use `template_add`, `template_remove`, and `template_update` to manage the weekly
template through MCP. `schedule_add_today` creates ad-hoc tasks that do *not*
appear in the template.

## Conflict handling

The conflict detector returns conflicts **and** proposed resolutions. It never
auto-applies a move. Hermes presents the options and the user chooses.

## Away mode

`away_dates` stores date ranges where the morning instantiation job should skip
creating `today_instances`. This is useful for vacations or sick days without
having to edit the template.

## Backup container

The backup job runs inside the same `sam-os` container as the MCP server. There
is no separate backup container. The scheduler triggers `do_backup()` at 3am,
which reads SQLite and upserts into Neon Postgres. `backup_runs` tracks outcomes.

## Open ports

None by default. MCP stdio does not need a network port. If you choose to expose
the server over SSE/HTTP, configure that separately.
