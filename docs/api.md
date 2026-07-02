# sam-os — API Reference

**Version:** 1.0.0

Personal OS — schedule, gym, nutrition tracking

_Auto-generated from `/openapi.json` — regenerate with `python3 scripts/gen_api_docs.py`._

## Endpoints

### `default`

#### `GET /health`

_Health_

Health check — verifies DB connectivity.


### `schedule`

#### `GET /api/schedule/today`

_Get Today_

Today's living schedule (instances, not template). Auto-instantiates if missing.


#### `GET /api/schedule/week`

_Get Week_

Full template week (immutable tasks).


#### `POST /api/schedule/did/{task_name}`

_Did Task_

Mark today's instance of <task_name> as done.

- `task_name` (string, required) — 

#### `POST /api/schedule/skip/{task_name}`

_Skip Task_

Mark today's instance of <task_name> as skipped.

- `task_name` (string, required) — 
- `reason` (string, optional) — 

#### `POST /api/schedule/push/{task_name}/{day}`

_Push Task_

Move <task_name> to <day>. By default one-off (today's instance).
With permanent=true, rewrites the template.

- `task_name` (string, required) — 
- `day` (string, required) — 
- `permanent` (boolean, optional) — 

#### `GET /api/schedule/history`

_Get History_

Last N days of schedule history (instance log).

- `days` (integer, optional) — 

#### `GET /api/schedule/stats`

_Get Stats_

Completion stats by category for last N days.

- `days` (integer, optional) — 

### `gym`

#### `POST /api/gym/log`

_Log Workout_

Log a workout. Auto-detects PRs (Epley 1RM, best per exercise × gym).

- **Body** (application/json): `LogWorkoutRequest` schema

#### `GET /api/gym/prs`

_List Prs_

List all PRs. Filter by gym via ?gym=office.

- `gym` (any, optional) — 

#### `GET /api/gym/recent`

_Recent Workouts_

Last N days of workouts.

- `days` (integer, optional) — 

### `meals`

#### `POST /api/meals/log`

_Log Meal_

Log a meal. Returns the meal_id plus today's running totals + target.

- **Body** (application/json): `LogMealRequest` schema

#### `POST /api/meals/target`

_Set Target_

Set today's calorie/macro target. Idempotent — overwrites existing.

- **Body** (application/json): `SetTargetRequest` schema

#### `GET /api/meals/today`

_Get Today Meals_

Today's meals + totals vs target.


#### `GET /api/meals/week`

_Get Week Meals_

Last 7 days — daily totals with target adherence.


## Schemas

### `HTTPValidationError`

- `detail` (array) — 

### `LogMealRequest`

- `meal_type` (string, required) — 
- `description` () — 
- `calories` (number, required) — 
- `protein_g` () — 
- `carbs_g` () — 
- `fat_g` () — 

### `LogWorkoutRequest`

- `gym` (string, required) — 
- `entries` (array, required) — 

### `LogWorkoutResponse`

- `ok` (boolean, required) — 
- `logged_count` (integer, required) — 
- `new_prs` (array, required) — 

### `SetEntry`

- `exercise` (string, required) — 
- `weight` (number, required) — 
- `reps` (integer, required) — 
- `sets` (integer) — 

### `SetTargetRequest`

- `calories` (number, required) — 
- `protein_g` () — 
- `carbs_g` () — 
- `fat_g` () — 
- `weight_kg` () — 
- `notes` () — 

### `ValidationError`

- `loc` (array, required) — 
- `msg` (string, required) — 
- `type` (string, required) — 
- `input` () — 
- `ctx` (object) — 
