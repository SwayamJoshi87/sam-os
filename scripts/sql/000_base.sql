-- 000_base.sql
-- Base schema for sam-os: categories, tasks, today_instances, schedule_log.
-- today_instances and nutrition are added by later migrations.

CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id  INTEGER NOT NULL,
    name         TEXT NOT NULL,
    day_of_week  INTEGER NOT NULL DEFAULT -1,  -- 0=Mon ... 6=Sun; -1 = ad-hoc / unscheduled
    time_start   TEXT,
    duration_min INTEGER DEFAULT 30,
    fixed        INTEGER DEFAULT 0,  -- 0 = flexible, 1 = fixed
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_day ON tasks(day_of_week);

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

CREATE TABLE IF NOT EXISTS schedule_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date       TEXT NOT NULL,
    task_id    INTEGER,
    status     TEXT,
    reason     TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
