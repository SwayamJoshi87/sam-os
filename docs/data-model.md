# Data Model

All tables live in `schedule.db` (SQLite, single file on the host).

The same schema is mirrored in the Neon Postgres backup target.

## Tables

| Table | Purpose | Primary key |
|---|---|---|
| `categories` | Color-coded task categories (gym, work, meal_prep, etc.) | `id` |
| `tasks` | Weekly template — what the ideal week looks like | `id` |
| `today_instances` | Per-day reality — moves, skips, reasons, completions | `id` |
| `workouts` | One row per set logged (date, gym, exercise, weight, reps) | `id` |
| `prs` | Current PR per exercise × gym (Epley 1RM) | `id` |
| `meals` | One row per meal (date, type, cals, P/C/F) | `id` |
| `daily_targets` | Per-day calorie/macro target + weight | `id` |
| `schedule_log` | Legacy — completion log (mostly superseded by today_instances) | `id` |
| `water_log` | Water intake entries | `id` |
| `sleep_log` | Sleep per night | `id` |
| `mood_log` | Mood entries | `id` |
| `habits` | Recurring daily habits | `id` |
| `habit_logs` | Per-date habit status | `id` |
| `shopping_items` | Shopping list | `id` |
| `away_dates` | Date ranges where schedule instantiation is suppressed | `id` |
| `task_notes` | Notes attached to today_instances | `id` |
| `meal_templates` | Reusable meal templates | `id` |
| `backup_runs` | Backup run history | `id` |
| `entities` | Graph nodes (people, projects, topics, ...) | `id` |
| `observations` | Timestamped facts attached to entities | `id` |
| `relationships` | Typed edges between entities | `id` |
| `events` | Append-only audit log | `id` |
| `todos` | Standalone action items | `id` |
| `notes` | Free-form notes | `id` |
| `journal` | Dated journal entries | `id` |
| `memories` | Remembered facts | `id` |
| `projects` | Projects / workstreams | `id` |
| `user_profile` | Key/value user preferences | `id` |
| `email_cache` | Minimal IMAP metadata cache | `id` |
| `weather_cache` | Recent weather API responses | `id` |

## Schema

See `scripts/sql/*.sql` for the canonical CREATE TABLE statements. Migrations
are applied automatically on API startup via `init_db()`. The same DDL is in
`backup/pg_schema.sql` for the postgres target.

## Sample queries

```sql
-- today's meals vs target
SELECT m.meal_type, m.calories, m.protein_g,
       SUM(m.calories) OVER (ORDER BY m.created_at) AS running_cals
FROM meals m WHERE m.date = date('now');

-- this week's gym PRs (top 5)
SELECT exercise, weight, reps, estimated_1rm, achieved_at
FROM prs WHERE achieved_at >= date('now', '-7 days')
ORDER BY estimated_1rm DESC
LIMIT 5;

-- schedule adherence last 30 days
SELECT i.status, COUNT(*) FROM today_instances i
WHERE i.date >= date('now', '-30 days')
GROUP BY i.status;

-- meals summary for a specific date
SELECT m.date, SUM(m.calories) AS cals, SUM(m.protein_g) AS p,
       t.calories AS target
FROM meals m
LEFT JOIN daily_targets t ON m.date = t.date
WHERE m.date = '2026-07-02'
GROUP BY m.date, t.calories;

-- daily water totals this week
SELECT date, SUM(amount_ml) AS total_ml
FROM water_log
WHERE date >= date('now', '-7 days')
GROUP BY date;

-- habit streak current
SELECT h.name, COUNT(*) AS streak
FROM habits h
JOIN habit_logs l ON l.habit_id=h.id
WHERE l.status='done'
  AND l.date > date('now', '-30 days')
GROUP BY h.name;
```

## Key relationships

- `tasks.category_id → categories.id` — many-to-one
- `today_instances.task_id → tasks.id` — many-to-one (per-day)
- `prs.workout_id → workouts.id` — best PR per (exercise, gym)
- `meals.date → daily_targets.date` — target lookup (LEFT JOIN since target is optional)
- `habit_logs.habit_id → habits.id` — many-to-one
- `task_notes.instance_id → today_instances.id` — many-to-one

## Schema versioning

Migrations come from three places and are applied in order:

1. `scripts/sql/*.sql` — base schema and early features (`000_base.sql`, `001_today_instances.sql`, ...)
2. `scripts/sql/core/*.sql` — core graph store (`000_graph.sql`)
3. `samos/modules/<name>/migrations/*.sql` — per-module schema

Module migrations are discovered automatically by `init_db()`, so new modules only need a `migrations/` directory.

All migrations use `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`
so they're safe to re-run. Schema changes that cannot be expressed idempotently
in plain SQL (for example adding a column) are handled by creating a new side
table rather than using `ALTER TABLE`, which lets migrations stay idempotent.

## Why no FK constraints in the postgres target

The postgres schema omits `FOREIGN KEY` constraints because:

1. SQLite uses `PRAGMA foreign_keys = OFF` by default per-connection
2. Backup sync is one-way (sqlite → pg), and FKs would just slow inserts
3. The data integrity is enforced at the application layer

If you need strict referential integrity in the PG target (e.g. for analytics),
add `FOREIGN KEY` clauses to the relevant tables in `backup/pg_schema.sql`.
