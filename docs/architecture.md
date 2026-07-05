# Architecture

## Component diagram

```
┌────────────────────────────────────────────┐
│  Host (your machine)                       │
│                                            │
│  /home/server/data/schedule.db  ← SQLite   │
│  /home/server/sam-os/           ← git repo │
│       └── samos/server.py       ← MCP      │
└────────────────┬───────────────────────────┘
                 │
                 │ Hermes launches stdio subprocess
                 │   .venv/bin/python -m samos.server
                 ▼
┌────────────────────────────────────────────┐
│  Hermes / MCP client                       │
│  Calls tools: schedule_today, gym_log,     │
│               meal_log, detect_conflicts   │
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
2. **MCP server** exposes tools/resources and runs an internal APScheduler for cron jobs.
3. **Reads/writes** go to the bind-mounted SQLite file.
4. **Backup job** runs at 3am, reads the same SQLite, syncs to Neon Postgres.
5. **No data in containers** — only code + ephemeral process state.

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

## Conflict handling

The conflict detector returns conflicts **and** proposed resolutions. It never
auto-applies a move. Hermes presents the options and the user chooses.

## Open ports

None by default. MCP stdio does not need a network port. If you choose to expose
the server over SSE/HTTP, configure that separately.
