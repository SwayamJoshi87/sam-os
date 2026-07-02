"""sam-os API — personal OS endpoints (schedule, gym, meals)."""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException

from db import get_conn, init_db, DB_PATH

app = FastAPI(
    title="sam-os",
    description="Personal OS — schedule, gym, nutrition tracking",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    """Verify DB is reachable. Apply migrations if needed."""
    if not DB_PATH.exists():
        raise RuntimeError(
            f"Database not found at {DB_PATH}. "
            f"Set SAMOS_DB_PATH or bind-mount the volume."
        )
    init_db()


@app.get("/health")
def health():
    """Health check — verifies DB connectivity."""
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"status": "ok", "db": str(DB_PATH)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"db error: {e}")


# Routers added in subsequent tasks
from schedule_router import router as schedule_router  # noqa: E402
from gym_router import router as gym_router  # noqa: E402
from meals_router import router as meals_router  # noqa: E402

app.include_router(schedule_router, prefix="/api/schedule", tags=["schedule"])
app.include_router(gym_router, prefix="/api/gym", tags=["gym"])
app.include_router(meals_router, prefix="/api/meals", tags=["meals"])
