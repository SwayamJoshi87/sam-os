-- 004_gym.sql
-- Adds workout logging and PR tracking tables.

CREATE TABLE IF NOT EXISTS workouts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    gym          TEXT NOT NULL,
    exercise     TEXT NOT NULL,
    weight       REAL,
    reps         INTEGER,
    sets         INTEGER DEFAULT 1,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(date);
CREATE INDEX IF NOT EXISTS idx_workouts_exercise ON workouts(exercise);
CREATE INDEX IF NOT EXISTS idx_workouts_gym ON workouts(gym);

CREATE TABLE IF NOT EXISTS prs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise       TEXT NOT NULL,
    gym            TEXT NOT NULL,
    weight         REAL,
    reps           INTEGER,
    estimated_1rm  REAL,
    workout_id     INTEGER,
    achieved_at    TEXT,
    UNIQUE(exercise, gym)
);

CREATE INDEX IF NOT EXISTS idx_prs_exercise_gym ON prs(exercise, gym);
