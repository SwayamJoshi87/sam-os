-- 007_meal_templates.sql
-- Reusable meal templates for one-tap logging.

CREATE TABLE IF NOT EXISTS meal_templates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    meal_type   TEXT NOT NULL,
    calories    REAL NOT NULL,
    protein_g   REAL,
    carbs_g     REAL,
    fat_g       REAL,
    description TEXT,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_meal_templates_type ON meal_templates(meal_type);
