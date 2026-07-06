"""Gym helpers — workout logging and PR tracking."""

import re
from datetime import datetime, timedelta

from samos.db import ValidationError, get_conn

WORKOUT_RE = re.compile(
    r"([a-zA-Z0-9_\-/]+(?:\s+[a-zA-Z0-9_\-/]+)?)\s+(\d+\.?\d*|bw|BW)\s*x\s*(\d+)(?:\s*x\s*(\d+))?",
    re.IGNORECASE,
)
WORKOUT_RE_ALT = re.compile(
    r"([a-zA-Z0-9_\-/]+(?:\s+[a-zA-Z0-9_\-/]+)?)\s+(\d+)\s+x\s+(\d+\.?\d*)(?:\s+x\s*(\d+))?",
    re.IGNORECASE,
)


def epley_1rm(weight: float, reps: int) -> float:
    if weight <= 0 or reps <= 0:
        return 0.0
    return round(weight * (1 + reps / 30.0), 1)


def parse_workout(text: str) -> list[dict]:
    """Parse 'bench 135x10x3 deadlift 225x5' into structured rows."""
    text = text.lower().strip()
    matches = WORKOUT_RE.findall(text)
    if not matches:
        matches = WORKOUT_RE_ALT.findall(text)

    results = []
    for m in matches:
        name = m[0].strip()
        raw_weight = m[1]
        weight = float(raw_weight) if raw_weight.replace(".", "").isdigit() else 0.0
        reps = int(m[2])
        sets = int(m[3]) if m[3] else 1
        results.append({"exercise": name, "weight": weight, "reps": reps, "sets": sets})
    return results


def log_workout(gym: str, entries: list[dict]) -> dict:
    if not gym.strip():
        raise ValidationError("gym name cannot be empty")
    if not entries:
        raise ValidationError("entries cannot be empty")

    date = datetime.now().strftime("%Y-%m-%d")
    new_prs = []
    with get_conn() as conn:
        for entry in entries:
            for _ in range(entry["sets"]):
                conn.execute(
                    """
                    INSERT INTO workouts (date, gym, exercise, weight, reps, sets)
                    VALUES (?, ?, ?, ?, ?, 1)
                    """,
                    (date, gym, entry["exercise"], entry["weight"], entry["reps"]),
                )
                workout_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                est = epley_1rm(entry["weight"], entry["reps"])
                if est <= 0:
                    continue
                existing = conn.execute(
                    "SELECT estimated_1rm FROM prs WHERE exercise=? AND gym=?",
                    (entry["exercise"], gym),
                ).fetchone()
                if not existing or est > existing["estimated_1rm"]:
                    conn.execute(
                        """
                        INSERT INTO prs (exercise, gym, weight, reps, estimated_1rm, workout_id, achieved_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(exercise, gym) DO UPDATE SET
                            weight=excluded.weight,
                            reps=excluded.reps,
                            estimated_1rm=excluded.estimated_1rm,
                            workout_id=excluded.workout_id,
                            achieved_at=excluded.achieved_at
                        """,
                        (entry["exercise"], gym, entry["weight"], entry["reps"], est, workout_id, date),
                    )
                    new_prs.append(
                        {
                            "exercise": entry["exercise"],
                            "gym": gym,
                            "weight": entry["weight"],
                            "reps": entry["reps"],
                            "estimated_1rm": est,
                        }
                    )
    return {"ok": True, "logged_count": sum(e["sets"] for e in entries), "new_prs": new_prs}


def list_prs(gym: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if gym:
            rows = conn.execute(
                """
                SELECT exercise, gym, weight, reps, estimated_1rm, achieved_at
                FROM prs WHERE gym=? ORDER BY exercise
                """,
                (gym,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT exercise, gym, weight, reps, estimated_1rm, achieved_at
                FROM prs ORDER BY gym, exercise
                """
            ).fetchall()
    return [dict(r) for r in rows]


def recent_workouts(days: int = 7) -> list[dict]:
    if days < 1:
        raise ValidationError("days must be >= 1", {"value": days})
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT date, gym, exercise, weight, reps, sets
            FROM workouts WHERE date >= ? ORDER BY date DESC, id DESC
            """,
            (since,),
        ).fetchall()
    return [dict(r) for r in rows]
