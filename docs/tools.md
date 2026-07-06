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

## Template management

| Tool | Description |
|---|---|
| `category_add(name, color="#808080")` | Add a new schedule category. |
| `template_add(name, day, time_start, duration_min, category, fixed=false)` | Add a recurring task to the weekly template. |
| `template_remove(task_name)` | Remove a recurring task from the template. |
| `template_update(task_name, ...)` | Update any field of an existing template task. |
| `template_reschedule(task_name, new_day)` | Move an existing template task to a different day. |

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
| `meal_template_add(...)` | Create a reusable meal template. |
| `meal_templates_list` | List all meal templates. |
| `meal_log_template(name)` | Log a meal from a template by name. |

## Wellness

| Tool | Description |
|---|---|
| `water_log(amount_ml)` | Log water intake for today. |
| `water_today_tool` | Today's water total and entries. |
| `water_week_tool(days=7)` | Daily water totals for the last N days. |
| `sleep_log(hours, quality, notes)` | Log last night's sleep. |
| `sleep_history_tool(days=7)` | Sleep history. |
| `mood_log(level, label, note)` | Log mood level 1-10. |
| `mood_history_tool(days=7)` | Mood history. |
| `weight_history_tool(days=30)` | Weight entries from daily targets. |

## Productivity

| Tool | Description |
|---|---|
| `habit_add(name, description)` | Create a daily habit. |
| `habits_list` | List all habits. |
| `habit_log(habit_name, status, note)` | Mark a habit done or missed for today. |
| `habits_today_tool` | All habits and today's status. |
| `shopping_add(item, category)` | Add an item to the shopping list. |
| `shopping_list_tool(show_purchased=false)` | Return the shopping list. |
| `shopping_mark_purchased(item_id, purchased=true)` | Mark an item purchased. |
| `shopping_clear_purchased` | Remove purchased items. |
| `away_mode_add(start_date, end_date, reason)` | Suppress schedule instantiation for a range. |
| `away_mode_list` | List away-date ranges. |
| `away_mode_check(date)` | Check if a date is inside an away range. |
| `task_note(task_name_or_id, note)` | Attach a note to today's instance of a task. |

## System

| Tool | Description |
|---|---|
| `system_help` | Dump tools, schema, row counts, conventions, and recovery info. |
| `system_health` | DB size, row counts, backup status, and environment flags. |
| `backup_status_tool(days=7)` | Recent backup run status. |
| `weekly_prep_tool` | Sunday-style summary: last week, upcoming template, PRs, backup. |

## Resources

- `schema://tables` — live table schemas and row counts
- `schedule://today` — today's schedule
- `gym://prs` — PR list
- `meals://today` — today's meals
- `state://today` — composite snapshot of today (schedule, gym, meals, wellness, habits, shopping)

## Error format

All tools return a JSON object with either:

```json
{"ok": true, "data": {}}
```

or

```json
{"ok": false, "error": {"type": "not_found|validation|conflict|database|calendar|internal", "message": "...", "details": {}}}
```
