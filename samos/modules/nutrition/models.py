"""Meal logging and daily target helpers."""

from datetime import datetime, timedelta

from samos.db import NotFoundError, ValidationError, get_conn

MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack"}


def today_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _validate_meal_type(meal_type: str) -> str:
    mt = meal_type.lower().strip()
    if mt not in MEAL_TYPES:
        raise ValidationError(
            f"meal_type must be one of {sorted(MEAL_TYPES)}",
            {"meal_type": meal_type},
        )
    return mt


def get_target(date_str: str) -> dict | None:
    with get_conn() as c:
        row = c.execute("SELECT * FROM daily_targets WHERE date=?", (date_str,)).fetchone()
    return dict(row) if row else None


def set_target(
    date_str: str,
    calories: float,
    protein_g: float | None = None,
    carbs_g: float | None = None,
    fat_g: float | None = None,
    weight_kg: float | None = None,
    notes: str | None = None,
) -> dict:
    if calories < 0:
        raise ValidationError("calories cannot be negative", {"value": calories})
    with get_conn() as c:
        existing = c.execute("SELECT id FROM daily_targets WHERE date=?", (date_str,)).fetchone()
        if existing:
            c.execute(
                """
                UPDATE daily_targets SET
                    calories=?, protein_g=?, carbs_g=?, fat_g=?, weight_kg=?, notes=?
                WHERE id=?
                """,
                (calories, protein_g, carbs_g, fat_g, weight_kg, notes, existing["id"]),
            )
        else:
            c.execute(
                """
                INSERT INTO daily_targets (date, calories, protein_g, carbs_g, fat_g, weight_kg, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (date_str, calories, protein_g, carbs_g, fat_g, weight_kg, notes),
            )
    return {"ok": True, "date": date_str, "target": get_target(date_str)}


def log_meal(
    date_str: str,
    meal_type: str,
    calories: float,
    description: str | None = None,
    protein_g: float | None = None,
    carbs_g: float | None = None,
    fat_g: float | None = None,
    source: str = "manual",
) -> dict:
    mt = _validate_meal_type(meal_type)
    if calories < 0:
        raise ValidationError("calories cannot be negative", {"value": calories})
    with get_conn() as c:
        c.execute(
            """
            INSERT INTO meals (date, meal_type, description, calories, protein_g, carbs_g, fat_g, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (date_str, mt, description, calories, protein_g, carbs_g, fat_g, source),
        )
        meal_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        totals = c.execute(
            """
            SELECT COALESCE(SUM(calories),0) AS calories,
                   COALESCE(SUM(protein_g),0) AS protein_g,
                   COALESCE(SUM(carbs_g),0) AS carbs_g,
                   COALESCE(SUM(fat_g),0) AS fat_g,
                   COUNT(*) AS meal_count
            FROM meals WHERE date=?
            """,
            (date_str,),
        ).fetchone()
        target = c.execute("SELECT * FROM daily_targets WHERE date=?", (date_str,)).fetchone()
    return {
        "ok": True,
        "meal_id": meal_id,
        "today_total": dict(totals),
        "target": dict(target) if target else None,
    }


def get_day_meals(date_str: str) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            """
            SELECT id, meal_type, description, calories, protein_g, carbs_g, fat_g, source, created_at
            FROM meals WHERE date=? ORDER BY created_at
            """,
            (date_str,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_day_totals(date_str: str) -> dict:
    with get_conn() as c:
        row = c.execute(
            """
            SELECT
                COALESCE(SUM(calories), 0) AS calories,
                COALESCE(SUM(protein_g), 0) AS protein_g,
                COALESCE(SUM(carbs_g), 0) AS carbs_g,
                COALESCE(SUM(fat_g), 0) AS fat_g,
                COUNT(*) AS meal_count
            FROM meals WHERE date=?
            """,
            (date_str,),
        ).fetchone()
    return dict(row)


def today_meals() -> dict:
    d = today_date()
    return {
        "date": d,
        "meals": get_day_meals(d),
        "totals": get_day_totals(d),
        "target": get_target(d),
    }


def week_meals() -> list[dict]:
    since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    with get_conn() as c:
        rows = c.execute(
            """
            SELECT m.date,
                   SUM(m.calories) AS calories,
                   SUM(m.protein_g) AS protein_g,
                   SUM(m.carbs_g) AS carbs_g,
                   SUM(m.fat_g) AS fat_g,
                   COUNT(*) AS meal_count,
                   t.calories AS target_calories
            FROM meals m
            LEFT JOIN daily_targets t ON m.date = t.date
            WHERE m.date >= ?
            GROUP BY m.date
            ORDER BY m.date
            """,
            (since,),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Meal templates
# ---------------------------------------------------------------------------


def add_meal_template(
    name: str,
    meal_type: str,
    calories: float,
    protein_g: float | None = None,
    carbs_g: float | None = None,
    fat_g: float | None = None,
    description: str | None = None,
) -> dict:
    """Create a reusable meal template."""
    mt = _validate_meal_type(meal_type)
    if calories < 0:
        raise ValidationError("calories cannot be negative", {"value": calories})
    name = name.strip()
    if not name:
        raise ValidationError("template name cannot be empty")
    with get_conn() as c:
        c.execute(
            """
            INSERT INTO meal_templates (name, meal_type, calories, protein_g, carbs_g, fat_g, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, mt, calories, protein_g, carbs_g, fat_g, description),
        )
    return {"name": name, "meal_type": mt, "calories": calories}


def list_meal_templates() -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM meal_templates ORDER BY meal_type, name"
        ).fetchall()
    return [dict(r) for r in rows]


def log_meal_template(name: str, date_str: str | None = None) -> dict:
    """Log a meal from a template by name."""
    d = date_str or today_date()
    with get_conn() as c:
        row = c.execute(
            "SELECT * FROM meal_templates WHERE name LIKE ? LIMIT 1",
            (f"%{name}%",),
        ).fetchone()
        if not row:
            raise NotFoundError(f"no meal template matching '{name}'", {"template": name})
    return log_meal(
        date_str=d,
        meal_type=row["meal_type"],
        calories=row["calories"],
        description=row["description"],
        protein_g=row["protein_g"],
        carbs_g=row["carbs_g"],
        fat_g=row["fat_g"],
        source="template",
    )
