-- 008_backup_status.sql
-- Track backup run outcomes and timing.

CREATE TABLE IF NOT EXISTS backup_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    status      TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    details     TEXT,
    rows_synced INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_backup_runs_started ON backup_runs(started_at);
