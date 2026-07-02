"""Meals endpoints — log meals, set target, daily/weekly totals."""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))
from db import get_conn  # noqa: E402

router = APIRouter()

MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack"}


class LogMealRequest(BaseModel):
    meal_type: str
    description: str | None = None
    calories: float
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None


@router.post("/log")
def log_meal(req: LogMealRequest):
    """Log a meal. Returns the meal_id plus today's running totals + target."""
    if req.meal_type not in MEAL_TYPES:
        raise HTTPException(400, f"meal_type must be one of {sorted(MEAL_TYPES)}")
    date = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO meals (date, meal_type, description, calories, protein_g, carbs_g, fat_g)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (date, req.meal_type, req.description, req.calories, req.protein_g, req.carbs_g, req.fat_g))
        meal_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        totals = conn.execute("""
            SELECT COALESCE(SUM(calories),0) AS calories,
                   COALESCE(SUM(protein_g),0) AS protein_g,
                   COALESCE(SUM(carbs_g),0) AS carbs_g,
                   COALESCE(SUM(fat_g),0) AS fat_g,
                   COUNT(*) AS meal_count
            FROM meals WHERE date=?
        """, (date,)).fetchone()
        target = conn.execute("SELECT * FROM daily_targets WHERE date=?", (date,)).fetchone()
    return {
        "ok": True,
        "meal_id": meal_id,
        "today_total": dict(totals),
        "target": dict(target) if target else None,
    }


class SetTargetRequest(BaseModel):
    calories: float
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    weight_kg: float | None = None
    notes: str | None = None


@router.post("/target")
def set_target(req: SetTargetRequest):
    """Set today's calorie/macro target. Idempotent — overwrites existing."""
    date = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM daily_targets WHERE date=?", (date,)).fetchone()
        if existing:
            conn.execute("""
                UPDATE daily_targets SET
                    calories=?, protein_g=?, carbs_g=?, fat_g=?, weight_kg=?, notes=?
                WHERE date=?
            """, (req.calories, req.protein_g, req.carbs_g, req.fat_g, req.weight_kg, req.notes, date))
        else:
            conn.execute("""
                INSERT INTO daily_targets (date, calories, protein_g, carbs_g, fat_g, weight_kg, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (date, req.calories, req.protein_g, req.carbs_g, req.fat_g, req.weight_kg, req.notes))
    return {"ok": True, "date": date, "target": req.model_dump()}


@router.get("/today")
def get_today_meals():
    """Today's meals + totals vs target."""
    date = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        meals = conn.execute("""
            SELECT id, meal_type, description, calories, protein_g, carbs_g, fat_g, source, created_at
            FROM meals WHERE date=? ORDER BY created_at
        """, (date,)).fetchall()
        totals = conn.execute("""
            SELECT COALESCE(SUM(calories),0) AS calories,
                   COALESCE(SUM(protein_g),0) AS protein_g,
                   COALESCE(SUM(carbs_g),0) AS carbs_g,
                   COALESCE(SUM(fat_g),0) AS fat_g,
                   COUNT(*) AS meal_count
            FROM meals WHERE date=?
        """, (date,)).fetchone()
        target = conn.execute("SELECT * FROM daily_targets WHERE date=?", (date,)).fetchone()
    return {
        "date": date,
        "meals": [dict(m) for m in meals],
        "totals": dict(totals),
        "target": dict(target) if target else None,
    }


@router.get("/week")
def get_week_meals():
    """Last 7 days — daily totals with target adherence."""
    since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    with get_conn() as conn:
        rows = conn.execute("""
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
        """, (since,)).fetchall()
    return [dict(r) for r in rows]
