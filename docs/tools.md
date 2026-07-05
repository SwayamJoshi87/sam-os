# sam-os — MCP Tools

The sam-os MCP server exposes these tools. Hermes can call any of them.

## Schedule

| Tool | Description |
|---|---|
| `schedule_today` | Return today's living schedule. Auto-instantiates from template if missing. |
| `schedule_week` | Return the weekly template. |
| `schedule_did(task_name)` | Mark today's pending instance of `task_name` as done. |
| `schedule_skip(task_name, reason="skipped")` | Mark today's pending instance as skipped. |
| `schedule_push(task_name, day, permanent=false)` | One-off move to a future date, or permanent template change. |
| `schedule_add_today(task_name, category, time, duration_min)` | Add an ad-hoc task to today only. |
| `schedule_remove_today(task_name_or_id, reason)` | Remove a task from today's living schedule. |
| `schedule_retime_today(task_name_or_id, new_time)` | Change the time of a task already instantiated for today. |
| `schedule_diff_today_vs_template` | Show how today diverges from the template. |
| `schedule_history(days=7)` | Instance log for the last N days. |
| `schedule_stats(days=7)` | Completion stats by category for the last N days. |

## Conflict resolution

| Tool | Description |
|---|---|
| `detect_conflicts` | Detect schedule conflicts today and propose resolutions. Never auto-applies. |
| `schedule_resolve_conflict(task_name, option_index)` | Apply one of the proposed resolutions. |

## Gym

| Tool | Description |
|---|---|
| `gym_log(gym, raw_text)` | Log a workout from text like `bench 135x10x3 squat 225x5`. |
| `gym_prs(gym=None)` | List PRs, optionally filtered by gym. |
| `gym_recent(days=7)` | Recent workouts for the last N days. |

## Meals

| Tool | Description |
|---|---|
| `meal_log(meal_type, calories, description, protein_g, carbs_g, fat_g)` | Log a meal for today. |
| `meal_target(calories, protein_g, carbs_g, fat_g, weight_kg, notes)` | Set today's calorie/macro target. |
| `meals_today` | Today's meals + totals vs target. |
| `meals_week` | Last 7 days adherence. |

## System

| Tool | Description |
|---|---|
| `system_help` | Dump tools, schema, row counts, conventions, and recovery info. |

## Resources

- `schema://tables` — live table schemas and row counts
- `schedule://today` — today's schedule
- `gym://prs` — PR list
- `meals://today` — today's meals

## Error format

All tools return a JSON object with either:

```json
{"ok": true, "data": {}}
```

or

```json
{"ok": false, "error": {"type": "not_found|validation|conflict|database|calendar|internal", "message": "...", "details": {}}}
```
