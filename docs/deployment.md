# Deployment

## First-time setup (Docker — recommended)

```bash
# 1. Clone
git clone https://github.com/SwayamJoshi87/sam-os.git /home/server/sam-os
cd /home/server/sam-os

# 2. Configure env
cp .env.example .env
nano .env
# Set SAMOS_DB_HOST_PATH=/home/server/data
# Set BACKUP_PG_DSN=postgresql://user:***@host/db?sslmode=require (optional)
# Set TZ=America/Toronto (or your local timezone)
# Set SAMOS_CALENDAR_OFFLINE=1 if you are not using iCloud

# 3. Build image
docker compose -f docker/docker-compose.yml --env-file .env build

# 4. Run automated setup inside the container
#    This writes ~/.hermes/mcp.json and seeds a starter template.
docker compose -f docker/docker-compose.yml --env-file .env run --rm sam-os \
  python scripts/setup.py run --calendar-offline

# 5. Test the server manually
docker compose -f docker/docker-compose.yml --env-file .env run --rm sam-os
# (send Ctrl-C after confirming it starts)
```

You can also run setup from the host if Python is available:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/setup.py run --docker --calendar-offline
```

## First-time setup (venv — alternative)

```bash
# 1. Clone
git clone https://github.com/SwayamJoshi87/sam-os.git /home/server/sam-os
cd /home/server/sam-os

# 2. Create venv and install
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Configure env
cp .env.example .env
nano .env

# 4. Run automated setup
.venv/bin/python scripts/setup.py run --calendar-offline

# Or step by step:
.venv/bin/python scripts/setup.py check
.venv/bin/python scripts/setup.py hermes --calendar-offline
.venv/bin/python scripts/setup.py seed

# 5. Test the server manually
.venv/bin/python -m samos.server
# (send Ctrl-C after confirming it starts)
```

## Host directory permissions

The server process needs write access to the SQLite directory so SQLite can create
`-wal` and `-journal` files.

```bash
mkdir -p /home/server/data
# If the host user is uid 1000 (default on most systems), this works as-is.
# Otherwise:
chmod 777 /home/server/data
# or:
chown 1000:1000 /home/server/data
```

## Hermes MCP config

The fastest way to generate the config is:

```bash
# Docker
.venv/bin/python scripts/setup.py hermes --docker --calendar-offline

# venv
.venv/bin/python scripts/setup.py hermes --calendar-offline
```

This writes `~/.hermes/mcp.json` with the correct launch command and environment.
You can also call `setup_write_hermes_config(use_docker=true)` over MCP.

If you prefer to write it by hand, use `hermes/mcp.json` as a starting point.
Key fields for venv mode:

- `command` — path to the venv Python.
- `args` — `[-u, -m, samos.server]`.
- `env` — `SAMOS_DB_PATH`, `TZ`, `PYTHONIOENCODING`, `HERMES_HOME`, `SAMOS_CALENDAR_OFFLINE`.

Restart Hermes after updating the config.

## Updating

```bash
cd /home/server/sam-os
git pull
.venv/bin/pip install -r requirements.txt
# Rebuild image if using Docker
docker compose -f docker/docker-compose.yml --env-file .env build
# Restart the sam-os MCP server from Hermes
```

DB is on the host, so updates never lose data. New SQL migrations in
`scripts/sql/*.sql` are applied automatically on the next server startup.

## Verification

```bash
# Check prerequisites
.venv/bin/python scripts/setup.py check --docker

# Check the server speaks MCP
docker compose -f docker/docker-compose.yml --env-file .env run --rm sam-os \
  sh -c 'echo '{"'"'"'jsonrpc":"2.0","id":1,"method":"initialize"'"'"'}' | python -m samos.server'

# Verify iCloud calendar connectivity (when not in offline mode)
docker compose -f docker/docker-compose.yml --env-file .env run --rm sam-os \
  python scripts/setup.py calendar

# List tools via the CLI helper
.venv/bin/python scripts/schedule.py today
```

## Docker

Build:

```bash
docker compose -f docker/docker-compose.yml --env-file .env build
```

Run interactively for stdio:

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm sam-os
```

Because MCP stdio requires an attached stdin/stdout pipe, `docker compose up -d` is
not the right command for stdio mode. Use `docker compose run --rm` or run the
server directly from the venv.

## Disabling the backup

If you want to run without the Postgres backup, leave `BACKUP_PG_DSN` empty in `.env`.
The backup job will log that backup is disabled and continue.

## Disabling the calendar

Set `SAMOS_CALENDAR_OFFLINE=1` in `.env` or in the MCP server env to skip all
iCloud CalDAV reads/writes. This is useful when credentials are not configured.

## Restoring from a postgres backup

The SQLite file is the canonical source. The PG backup is read-only. To restore
from PG to a fresh SQLite, follow the same steps as before: export from PG,
convert syntax to SQLite, and apply.

## Troubleshooting

### `unable to open database file`

The server process can't write to the host directory. Fix:

```bash
chmod 777 /home/server/data
```

### Hermes cannot connect

- Verify the `command` path in the MCP config points to the venv Python or `docker`.
- Check that `SAMOS_DB_PATH` is set and the directory is writable.
- Run the server manually and confirm it responds to the initialize message.
- Run `.venv/bin/python scripts/setup.py check` for a full prerequisite report.

### Migrations fail on startup

Check the latest file in `scripts/sql/`. The error is printed to stderr:

```bash
.venv/bin/python -m samos.server 2>&1 | tail -20
```

If a migration cannot be made idempotent in plain SQL, add a side table instead
of using `ALTER TABLE`. See `scripts/sql/006_productivity.sql` for the pattern.
