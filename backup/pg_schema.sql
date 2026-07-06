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

CREATE TABLE IF NOT EXISTS water_log (
    id         INTEGER PRIMARY KEY,
    date       TEXT NOT NULL,
    amount_ml  INTEGER NOT NULL,
    logged_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sleep_log (
    id          INTEGER PRIMARY KEY,
    date        TEXT NOT NULL UNIQUE,
    hours       REAL,
    quality     INTEGER,
    notes       TEXT,
    logged_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mood_log (
    id        INTEGER PRIMARY KEY,
    date      TEXT NOT NULL,
    level     INTEGER NOT NULL,
    label     TEXT,
    note      TEXT,
    logged_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS habits (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    active      INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS habit_logs (
    id        INTEGER PRIMARY KEY,
    habit_id  INTEGER NOT NULL,
    date      TEXT NOT NULL,
    status    TEXT NOT NULL,
    note      TEXT,
    logged_at TEXT NOT NULL,
    UNIQUE(habit_id, date)
);

CREATE TABLE IF NOT EXISTS shopping_items (
    id          INTEGER PRIMARY KEY,
    item        TEXT NOT NULL,
    category    TEXT,
    purchased   INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS away_dates (
    id          INTEGER PRIMARY KEY,
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL,
    reason      TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_notes (
    id          INTEGER PRIMARY KEY,
    instance_id INTEGER NOT NULL,
    note        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meal_templates (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    meal_type   TEXT NOT NULL,
    calories    REAL NOT NULL,
    protein_g   REAL,
    carbs_g     REAL,
    fat_g       REAL,
    description TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS backup_runs (
    id          INTEGER PRIMARY KEY,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT NOT NULL,
    details     TEXT,
    rows_synced INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_pg_meals_date ON meals(date);
CREATE INDEX IF NOT EXISTS idx_pg_today_date ON today_instances(date);
CREATE INDEX IF NOT EXISTS idx_pg_workouts_date ON workouts(date);
CREATE INDEX IF NOT EXISTS idx_pg_prs_exercise ON prs(exercise, gym);
CREATE INDEX IF NOT EXISTS idx_pg_water_date ON water_log(date);
CREATE INDEX IF NOT EXISTS idx_pg_sleep_date ON sleep_log(date);
CREATE INDEX IF NOT EXISTS idx_pg_mood_date ON mood_log(date);
CREATE INDEX IF NOT EXISTS idx_pg_habit_logs_date ON habit_logs(date);
CREATE INDEX IF NOT EXISTS idx_pg_backup_runs_started ON backup_runs(started_at);

CREATE TABLE IF NOT EXISTS entities (
    id          INTEGER PRIMARY KEY,
    module      TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    name        TEXT NOT NULL,
    entity_key  TEXT,
    meta        TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS relationships (
    id          INTEGER PRIMARY KEY,
    source_id   INTEGER NOT NULL,
    target_id   INTEGER NOT NULL,
    rel_type    TEXT NOT NULL,
    meta        TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
    id          INTEGER PRIMARY KEY,
    entity_id   INTEGER NOT NULL,
    obs_key     TEXT NOT NULL,
    obs_value   TEXT,
    observed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY,
    entity_id   INTEGER,
    module      TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    payload     TEXT,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pg_entities_module ON entities(module);
CREATE INDEX IF NOT EXISTS idx_pg_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_pg_relationships_source ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_pg_relationships_target ON relationships(target_id);
CREATE INDEX IF NOT EXISTS idx_pg_observations_entity ON observations(entity_id);
CREATE INDEX IF NOT EXISTS idx_pg_events_module ON events(module);

CREATE TABLE IF NOT EXISTS todos (
    id          INTEGER PRIMARY KEY,
    text        TEXT NOT NULL,
    status      TEXT NOT NULL,
    priority    INTEGER,
    due_date    TEXT,
    project_id  INTEGER,
    tags        TEXT,
    created_at  TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY,
    title       TEXT,
    body        TEXT NOT NULL,
    tags        TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS journal (
    id          INTEGER PRIMARY KEY,
    date        TEXT NOT NULL UNIQUE,
    mood        INTEGER,
    entry       TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
    id          INTEGER PRIMARY KEY,
    category    TEXT NOT NULL,
    fact        TEXT NOT NULL,
    confidence  INTEGER,
    source      TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL,
    notes       TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_profile (
    id          INTEGER PRIMARY KEY,
    key         TEXT NOT NULL UNIQUE,
    value       TEXT,
    updated_at  TEXT NOT NULL
);
