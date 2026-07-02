"""Gym endpoints — log workouts, list PRs, recent workouts."""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))
from db import get_conn  # noqa: E402

router = APIRouter()


def epley_1rm(weight: float, reps: int) -> float:
    """Epley formula: weight × (1 + reps/30). Industry standard."""
    return weight * (1 + reps / 30)


class SetEntry(BaseModel):
    exercise: str
    weight: float
    reps: int
    sets: int = 1


class LogWorkoutRequest(BaseModel):
    gym: str
    entries: list[SetEntry]


class LogWorkoutResponse(BaseModel):
    ok: bool
    logged_count: int
    new_prs: list[dict]


@router.post("/log", response_model=LogWorkoutResponse)
def log_workout(req: LogWorkoutRequest):
    """Log a workout. Auto-detects PRs (Epley 1RM, best per exercise × gym)."""
    date = datetime.now().strftime("%Y-%m-%d")
    new_prs = []
    logged = 0
    with get_conn() as conn:
        for entry in req.entries:
            for _ in range(entry.sets):
                conn.execute("""
                    INSERT INTO workouts (date, gym, exercise, weight, reps, sets)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (date, req.gym, entry.exercise, entry.weight, entry.reps))
                workout_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                logged += 1
                # PR check
                est = epley_1rm(entry.weight, entry.reps)
                existing = conn.execute("""
                    SELECT estimated_1rm FROM prs WHERE exercise=? AND gym=?
                """, (entry.exercise, req.gym)).fetchone()
                if not existing or est > existing["estimated_1rm"]:
                    conn.execute("""
                        INSERT INTO prs (exercise, gym, weight, reps, estimated_1rm, workout_id, achieved_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(exercise, gym) DO UPDATE SET
                            weight=excluded.weight,
                            reps=excluded.reps,
                            estimated_1rm=excluded.estimated_1rm,
                            workout_id=excluded.workout_id,
                            achieved_at=excluded.achieved_at
                    """, (entry.exercise, req.gym, entry.weight, entry.reps, est, workout_id, date))
                    new_prs.append({
                        "exercise": entry.exercise,
                        "gym": req.gym,
                        "weight": entry.weight,
                        "reps": entry.reps,
                        "estimated_1rm": round(est, 1),
                    })
    return LogWorkoutResponse(ok=True, logged_count=logged, new_prs=new_prs)


@router.get("/prs")
def list_prs(gym: str | None = None):
    """List all PRs. Filter by gym via ?gym=office."""
    with get_conn() as conn:
        if gym:
            rows = conn.execute("""
                SELECT exercise, gym, weight, reps, estimated_1rm, achieved_at
                FROM prs WHERE gym=? ORDER BY exercise
            """, (gym,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT exercise, gym, weight, reps, estimated_1rm, achieved_at
                FROM prs ORDER BY gym, exercise
            """).fetchall()
    return [dict(r) for r in rows]


@router.get("/recent")
def recent_workouts(days: int = Query(7, ge=1, le=90)):
    """Last N days of workouts."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT date, gym, exercise, weight, reps, sets
            FROM workouts WHERE date >= ? ORDER BY date DESC, id DESC
        """, (since,)).fetchall()
    return [dict(r) for r in rows]
