CREATE TABLE IF NOT EXISTS weather_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    location    TEXT NOT NULL,
    type        TEXT NOT NULL,
    payload     TEXT NOT NULL,
    fetched_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_weather_cache_location ON weather_cache(location, type);
