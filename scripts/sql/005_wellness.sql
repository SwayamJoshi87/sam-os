-- 005_wellness.sql
-- Water, sleep, and mood tracking tables.

CREATE TABLE IF NOT EXISTS water_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date       TEXT NOT NULL,
    amount_ml  INTEGER NOT NULL,
    logged_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_water_date ON water_log(date);

CREATE TABLE IF NOT EXISTS sleep_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL UNIQUE,
    hours       REAL,
    quality     INTEGER CHECK (quality BETWEEN 1 AND 10),
    notes       TEXT,
    logged_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sleep_date ON sleep_log(date);

CREATE TABLE IF NOT EXISTS mood_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    date      TEXT NOT NULL,
    level     INTEGER NOT NULL CHECK (level BETWEEN 1 AND 10),
    label     TEXT,
    note      TEXT,
    logged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mood_date ON mood_log(date);
