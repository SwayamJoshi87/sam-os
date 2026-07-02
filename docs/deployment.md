# Deployment

## First-time setup

```bash
# 1. Clone
git clone https://github.com/SwayamJoshi87/sam-os.git /home/server/sam-os
cd /home/server/sam-os

# 2. Create venv for CLI tools (optional, for local dev)
python3 -m venv .venv
.venv/bin/pip install -r api/requirements.txt

# 3. Configure env
cp .env.example .env
nano .env
# Set SAMOS_DB_HOST_PATH=/home/server/data
# Set BACKUP_PG_DSN=postgresql://user:***@host/db?sslmode=require
# Set TZ=America/Toronto (or your local timezone)

# 4. Build + start
docker compose -f docker/docker-compose.yml --env-file .env build
docker compose -f docker/docker-compose.yml --env-file .env up -d

# 5. Verify
curl http://localhost:8765/health
# {"status":"ok","db":"/data/schedule.db"}

docker ps --filter "name=sam-os"
# sam-os-api      Up (healthy)  127.0.0.1:8765->8765/tcp
# sam-os-backup   Up

docker logs sam-os-backup
# [timestamp] starting backup from /data/schedule.db
#   pg schema verified/applied
#   categories: 6 rows synced
#   ...
#   backup complete
#   backup scheduler running, next at 3am
```

## Host directory permissions

The api container runs as uid 1000 (user `samos`). The host directory at
`SAMOS_DB_HOST_PATH` must be writable by that uid so SQLite can create
`-wal` and `-journal` files alongside the main DB.

```bash
# If the host user is uid 1000 (default on most systems), this works as-is.
# Otherwise:
chmod 777 /home/server/data
# or:
chown 1000:1000 /home/server/data
```

Verify from inside the container:

```bash
docker exec sam-os-api touch /data/.test && echo "write works" || echo "PERMISSION DENIED"
docker exec sam-os-api rm /data/.test
```

## Updating

```bash
cd /home/server/sam-os
git pull
docker compose -f docker/docker-compose.yml --env-file .env build
docker compose -f docker/docker-compose.yml --env-file .env up -d
```

DB is bind-mounted, so updates never lose data. New SQL migrations in
`scripts/sql/*.sql` are applied automatically on the next API startup.

## Verification

```bash
# API health
curl -s http://localhost:8765/health
# {"status":"ok","db":"/data/schedule.db"}

# Endpoint count
curl -s http://localhost:8765/openapi.json | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(f'{len(d[\"paths\"])} endpoints registered')"

# Backup recent run
docker logs sam-os-backup 2>&1 | tail -20

# Manual backup trigger
docker restart sam-os-backup
sleep 8
docker logs sam-os-backup 2>&1 | tail -15

# Verify backup landed in PG
docker run --rm -e PGPASSWORD='***' postgres:16-alpine \
  psql "host=YOUR_HOST user=YOUR_USER dbname=YOUR_DB sslmode=require" \
  -c "SELECT COUNT(*) FROM workouts;"
```

## Restoring from a postgres backup

The SQLite file is the canonical source. The PG backup is read-only. To restore
from PG to a fresh SQLite (cross-dialect, non-trivial):

1. Export the relevant tables from PG:
   ```bash
   docker run --rm -e PGPASSWORD='***' postgres:16-alpine \
     pg_dump "host=YOUR_HOST user=YOUR_USER dbname=YOUR_DB sslmode=require" \
     --data-only --no-owner --no-privileges \
     -t tasks -t today_instances -t workouts -t prs -t meals -t daily_targets \
     > /tmp/samos_restore.sql
   ```

2. Convert syntax to SQLite (manual transform — see tools like `pg2sqlite` or
   do it by hand for the small set of types involved)

3. Apply to a fresh SQLite file:
   ```bash
   sqlite3 /home/server/data/schedule.db < scripts/sql/001_today_instances.sql
   sqlite3 /home/server/data/schedule.db < scripts/sql/002_nutrition.sql
   sqlite3 /home/server/data/schedule.db < /tmp/samos_restored.sql
   ```

4. Restart the API to pick up the changes:
   ```bash
   docker compose -f docker/docker-compose.yml --env-file .env restart api
   ```

In practice, you almost never need to restore from PG. The host SQLite is
the source of truth and is itself backed up via your usual host backup
strategy (whatever you use for `/home/server/data`).

## Disabling the backup

If you want to run the API without the backup container:

```bash
docker compose -f docker/docker-compose.yml --env-file .env up -d api
# or to stop just the backup:
docker compose -f docker/docker-compose.yml --env-file .env stop backup
```

## Exposing the API remotely

Default is `127.0.0.1:8765` (localhost-only). To expose:

- **LAN only** — change `docker-compose.yml` to `"0.0.0.0:8765:8765"`
- **Public** — put behind a reverse proxy (nginx, caddy) with TLS. See the
  self-hosted-services skill for the local-https recipe.

When exposing, set `SAMOS_API_KEY` in `.env` and add an auth middleware to
`api/main.py` that checks `Authorization: Bearer *** KEY` (deferred — not in v1.0).

## Troubleshooting

### `unable to open database file`

The api user can't write to the host directory. Fix:
```bash
chmod 777 /home/server/data
```

### Backup hangs / never logs

`docker logs sam-os-backup` is empty. Check that the python process is unbuffered
(Dockerfile already has `-u` flag). If you customized the Dockerfile and removed
`-u`, restore it.

### PG connection fails with "password authentication failed"

The `.env` file has the wrong password, or the `BACKUP_PG_DSN` got corrupted.
Check with:
```bash
grep BACKUP_PG_DSN /home/server/sam-os/.env
```

### Migrations fail on API startup

Check the latest file in `scripts/sql/`. The error is in the API logs:
```bash
docker logs sam-os-api 2>&1 | tail -20
```

### Backup overwrites good data with bad data

The backup is one-way (sqlite → pg). It uses upserts, so any old data in PG
for a given `id` gets overwritten. If you accidentally back up a corrupted
SQLite, the PG copy gets corrupted too. Solution: use the PG snapshot
recovery (Neon dashboard → "Restore to point in time") to roll back.
