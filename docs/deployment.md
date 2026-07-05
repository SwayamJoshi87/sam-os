# Deployment

## First-time setup

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
# Set SAMOS_DB_HOST_PATH=/home/server/data
# Set BACKUP_PG_DSN=postgresql://user:***@host/db?sslmode=require
# Set TZ=America/Toronto (or your local timezone)

# 4. Test the server manually
.venv/bin/python -m samos.server
# (send Ctrl-C after confirming it starts)

# 5. Configure Hermes to launch it
# Copy hermes/mcp.json to your Hermes MCP config location and adjust paths.
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

Use `hermes/mcp.json` as a starting point. Key fields:

- `command` — path to the venv Python.
- `args` — `[-u, -m, samos.server]`.
- `env` — `SAMOS_DB_PATH`, `TZ`, `PYTHONIOENCODING`, `HERMES_HOME`.

Restart Hermes after updating the config.

## Updating

```bash
cd /home/server/sam-os
git pull
.venv/bin/pip install -r requirements.txt
# Restart the sam-os MCP server from Hermes
```

DB is on the host, so updates never lose data. New SQL migrations in
`scripts/sql/*.sql` are applied automatically on the next server startup.

## Verification

```bash
# Check the server speaks MCP
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | .venv/bin/python -m samos.server

# List tools via the CLI helper (or call tools/call over stdio)
.venv/bin/python scripts/schedule.py today
.venv/bin/python scripts/workout.py prs
.venv/bin/python scripts/meal_log.py today
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

If you want to run without the Postgres backup:

- Leave `BACKUP_PG_DSN` empty in `.env`, or
- Set `SAMOS_CALENDAR_OFFLINE=1` to skip iCloud CalDAV reads/writes.

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

- Verify the `command` path in the MCP config points to the venv Python.
- Check that `SAMOS_DB_PATH` is set and the directory is writable.
- Run the server manually and confirm it responds to the initialize message.

### Migrations fail on startup

Check the latest file in `scripts/sql/`. The error is printed to stderr:

```bash
.venv/bin/python -m samos.server 2>&1 | tail -20
```
