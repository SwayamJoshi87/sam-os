"""Schedule endpoints — today, did/skip/push, history, stats."""
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))
from schedule_lib import (  # noqa: E402
    DAYS, conn, today_date, dow_today,
    get_today_view, instantiate_day,
    mark_done, mark_skip, move_task, template_reschedule, find_target_date,
    week_history, stats as week_stats,
)

router = APIRouter()


@router.get("/today")
def get_today():
    """Today's living schedule (instances, not template). Auto-instantiates if missing."""
    instantiate_day(today_date(), dow_today(), source="api")
    return {"date": today_date(), "tasks": get_today_view()}


@router.get("/week")
def get_week():
    """Full template week (immutable tasks)."""
    out = {}
    for dow in range(7):
        with conn() as c:
            rows = c.execute("""
                SELECT t.id, c.name AS cat, t.name, t.time_start, t.duration_min, t.fixed
                FROM tasks t JOIN categories c ON t.category_id=c.id
                WHERE t.day_of_week=? ORDER BY t.time_start
            """, (dow,)).fetchall()
        out[DAYS[dow]] = [dict(r) for r in rows]
    return out


@router.post("/did/{task_name}")
def did_task(task_name: str):
    """Mark today's instance of <task_name> as done."""
    row = mark_done(task_name)
    if not row:
        raise HTTPException(404, f"no pending '{task_name}' today")
    return {"ok": True, "message": f"✅ logged: {row['name']} — done", "data": row}


@router.post("/skip/{task_name}")
def skip_task(task_name: str, reason: str = Query("skipped")):
    """Mark today's instance of <task_name> as skipped."""
    row = mark_skip(task_name, reason)
    if not row:
        raise HTTPException(404, f"no pending '{task_name}' today")
    return {"ok": True, "message": f"❌ logged: {row['name']} — skipped ({reason})", "data": row}


@router.post("/push/{task_name}/{day}")
def push_task(task_name: str, day: str, permanent: bool = Query(False)):
    """Move <task_name> to <day>. By default one-off (today's instance).
    With permanent=true, rewrites the template."""
    if permanent:
        result = template_reschedule(task_name, day)
        if not result:
            raise HTTPException(404, f"unknown day '{day}' or no task matching '{task_name}'")
        return {"ok": True, "message": f"🔁 permanently moved {result['name']} {result['from']} → {result['to']}", "data": result}
    else:
        target = find_target_date(day)
        if not target:
            raise HTTPException(400, f"unknown day: {day}")
        result = move_task(task_name, target, reason=f"pushed to {day}")
        if not result:
            raise HTTPException(404, f"no pending '{task_name}' today to move")
        return {"ok": True, "message": f"✅ moved '{result['task_name']}' to {day} ({target}) — one-off", "data": result}


@router.get("/history")
def get_history(days: int = Query(7, ge=1, le=90)):
    """Last N days of schedule history (instance log)."""
    return week_history(days)


@router.get("/stats")
def get_stats(days: int = Query(7, ge=1, le=90)):
    """Completion stats by category for last N days."""
    return week_stats(days)
