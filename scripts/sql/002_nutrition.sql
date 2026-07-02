-- 002_nutrition.sql
-- Adds meal logging + daily targets to schedule.db

CREATE TABLE IF NOT EXISTS meals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,                -- "2026-07-02"
    meal_type    TEXT NOT NULL,                -- breakfast | lunch | dinner | snack
    description  TEXT,                         -- "2 eggs, 1 sourdough toast, avocado"
    calories     REAL,
    protein_g    REAL,
    carbs_g      REAL,
    fat_g        REAL,
    source       TEXT NOT NULL DEFAULT 'manual', -- manual | usda | estimate
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_meals_date ON meals(date);
CREATE INDEX IF NOT EXISTS idx_meals_date_type ON meals(date, meal_type);

CREATE TABLE IF NOT EXISTS daily_targets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL UNIQUE,         -- "2026-07-02"
    calories     REAL,
    protein_g    REAL,
    carbs_g      REAL,
    fat_g        REAL,
    weight_kg    REAL,                         -- optional, for trend tracking
    notes        TEXT,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_targets_date ON daily_targets(date);