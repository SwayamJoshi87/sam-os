CREATE TABLE IF NOT EXISTS email_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    msg_id      TEXT NOT NULL UNIQUE,
    thread_id   TEXT,
    sender      TEXT,
    subject     TEXT,
    date        TEXT,
    is_read     INTEGER DEFAULT 0,
    fetched_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_cache_date ON email_cache(date);
CREATE INDEX IF NOT EXISTS idx_email_cache_unread ON email_cache(is_read);
