-- sam-os postgres schema (for backup target)
-- Run once before first sync. Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS categories (
    id    INTEGER PRIMARY KEY,
    name  TEXT UNIQUE NOT NULL,
    color TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    id            INTEGER PRIMARY KEY,
    name          TEXT,
    category_id   INTEGER,
    duration_min  INTEGER,
    priority      INTEGER DEFAULT 3,
    fixed         INTEGER DEFAULT 0,
    day_of_week   INTEGER,
    time_start    TEXT
);

CREATE TABLE IF NOT EXISTS today_instances (
    id            INTEGER PRIMARY KEY,
    date          TEXT NOT NULL,
    task_id       INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    TEXT NOT NULL,
    completed_at  TEXT,
    moved_to      TEXT,
    new_time      TEXT,
    reason        TEXT,
    source        TEXT NOT NULL DEFAULT 'cron'
);

CREATE TABLE IF NOT EXISTS workouts (
    id        INTEGER PRIMARY KEY,
    date      TEXT NOT NULL,
    gym       TEXT NOT NULL,
    exercise  TEXT NOT NULL,
    weight    REAL,
    reps      INTEGER,
    sets      INTEGER DEFAULT 1,
    notes     TEXT
);

CREATE TABLE IF NOT EXISTS prs (
    id              INTEGER PRIMARY KEY,
    exercise        TEXT NOT NULL,
    gym             TEXT NOT NULL,
    weight          REAL,
    reps            INTEGER,
    estimated_1rm   REAL,
    workout_id      INTEGER,
    achieved_at     TEXT,
    UNIQUE (exercise, gym)
);

CREATE TABLE IF NOT EXISTS meals (
    id           INTEGER PRIMARY KEY,
    date         TEXT NOT NULL,
    meal_type    TEXT NOT NULL,
    description  TEXT,
    calories     REAL,
    protein_g    REAL,
    carbs_g      REAL,
    fat_g        REAL,
    source       TEXT NOT NULL DEFAULT 'manual',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_targets (
    id           INTEGER PRIMARY KEY,
    date         TEXT NOT NULL UNIQUE,
    calories     REAL,
    protein_g    REAL,
    carbs_g      REAL,
    fat_g        REAL,
    weight_kg    REAL,
    notes        TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedule_log (
    id              INTEGER PRIMARY KEY,
    date            TEXT,
    task_id         INTEGER,
    completed       INTEGER DEFAULT 0,
    skipped_reason  TEXT
);

CREATE INDEX IF NOT EXISTS idx_pg_meals_date ON meals(date);
CREATE INDEX IF NOT EXISTS idx_pg_today_date ON today_instances(date);
CREATE INDEX IF NOT EXISTS idx_pg_workouts_date ON workouts(date);
CREATE INDEX IF NOT EXISTS idx_pg_prs_exercise ON prs(exercise, gym);
