CREATE TABLE IF NOT EXISTS today_instances (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    task_id      INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    moved_to     TEXT,
    new_time     TEXT,
    reason       TEXT,
    source       TEXT NOT NULL DEFAULT 'cron',
    UNIQUE(date, task_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_instances_date ON today_instances(date);
CREATE INDEX IF NOT EXISTS idx_instances_status ON today_instances(status);
CREATE INDEX IF NOT EXISTS idx_instances_date_status ON today_instances(date, status);
