-- 006_productivity.sql
-- Habits, shopping list, away-mode suppression, and task notes.

CREATE TABLE IF NOT EXISTS habits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    active      INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS habit_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id  INTEGER NOT NULL,
    date      TEXT NOT NULL,
    status    TEXT NOT NULL CHECK (status IN ('done', 'missed')),
    note      TEXT,
    logged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(habit_id, date),
    FOREIGN KEY (habit_id) REFERENCES habits(id)
);

CREATE INDEX IF NOT EXISTS idx_habit_logs_date ON habit_logs(date);

CREATE TABLE IF NOT EXISTS shopping_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item        TEXT NOT NULL,
    category    TEXT,
    purchased   INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_shopping_category ON shopping_items(category);

CREATE TABLE IF NOT EXISTS away_dates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL,
    reason      TEXT,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_away_dates ON away_dates(start_date, end_date);

-- Notes attached to today's schedule instances (kept separate so migrations stay idempotent).
CREATE TABLE IF NOT EXISTS task_notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id INTEGER NOT NULL,
    note        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES today_instances(id)
);

CREATE INDEX IF NOT EXISTS idx_task_notes_instance ON task_notes(instance_id);
