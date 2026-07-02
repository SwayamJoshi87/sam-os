# Architecture

## Component diagram

```
┌────────────────────────────────────────────┐
│  Host (your machine)                       │
│                                            │
│  /home/server/data/schedule.db  ← SQLite   │
│  /home/server/sam-os/           ← git repo │
└────────────────┬───────────────────────────┘
                 │ bind mount
                 ▼
┌────────────────────────────────────────────┐
│  Docker                                    │
│                                            │
│  ┌────────────────────┐  ┌──────────────┐  │
│  │  sam-os-api        │  │ sam-os-backup│  │
│  │  FastAPI :8765     │  │ psycopg2     │  │
│  │                    │  │ APScheduler  │  │
│  │  /api/schedule     │  │ 3am daily    │  │
│  │  /api/gym          │  │              │  │
│  │  /api/meals        │  │              │  │
│  │  /docs (OpenAPI)   │  │              │  │
│  └────────────────────┘  └──────┬───────┘  │
└──────────────────────────────────┼──────────┘
                                   │ TLS
                                   ▼
                        ┌─────────────────────┐
                        │  Neon Postgres      │
                        │  (serverless)       │
                        └─────────────────────┘
```

## Data flow

1. **Reads** (telegram bot, cron, browser) hit `sam-os-api:8765` via HTTP
2. **API** reads from bind-mounted SQLite, returns JSON
3. **Mutations** (POST /did/gym, /api/meals/log) write to SQLite via the API
4. **Backup container** runs at 3am, reads the same SQLite, syncs to Neon
5. **No data in containers** — only code + ephemeral process state

## Why SQLite on the host, not in a Docker volume

- Container restarts never lose data (`docker rm -f` is safe)
- `docker compose up` after a config change keeps the DB intact
- Backup reads from the same source the API writes to (no drift)
- Easy to inspect from the host: `sqlite3 /home/server/data/schedule.db`
- DB permissions follow the host's standard layout (uid 1000)

The api container needs `:rw` because it writes (instantiates today's instances
on first GET). The backup container only reads, so it could safely be `:ro`.

## Why two services, not one

The API is read-heavy and latency-sensitive. The backup is batch and tolerates
restarts. Separating them means:

- Backup can crashloop without taking down the API
- API can be redeployed without losing backup history
- Different resource limits (api: 256MB, backup: 128MB)
- Different restart policies if you want

## Why FastAPI

- Async (uvicorn under the hood) — handles concurrent requests cleanly
- Auto-generated OpenAPI docs at `/docs` and `/openapi.json`
- Pydantic models catch type errors before they hit the DB
- Type hints make the code self-documenting
- Stdlib sqlite3 + FastAPI = no ORM bloat, full control over SQL

## Why stdlib sqlite3 (not SQLAlchemy)

- The schema is small (8 tables), the queries are simple
- We already have working CLI scripts that use raw sqlite3
- ORM adds an abstraction layer we'd have to teach the LLM skills
- Direct SQL keeps the mental model: "what the script does is what the API does"
- Migrations are plain SQL files (`scripts/sql/*.sql`), applied idempotently on API startup

## Why Neon Postgres (not a local PG container)

- Serverless — no maintenance, no resource overhead on the homelab
- Free tier handles 1 daily backup job fine
- TLS by default (no firewall config)
- Separate from the homelab — survives total local hardware failure
- The SQLite file is still the canonical source of truth; PG is read-only backup

## Open ports

| Port | Service | Bound to | Notes |
|---|---|---|---|
| 8765 | sam-os-api | 127.0.0.1 | localhost-only by default. Expose via reverse proxy if remote access needed. |

No other ports are exposed. The backup container has no inbound ports.
