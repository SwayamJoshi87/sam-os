"""End-to-end tests for conflict detection and resolution."""

import sqlite3


def _inject_overlapping_tasks(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    cats = {r["name"]: r["id"] for r in conn.execute("SELECT * FROM categories").fetchall()}

    # Two overlapping fixed tasks for today, both pending
    conn.execute(
        """
        INSERT INTO tasks (category_id, name, day_of_week, time_start, duration_min, fixed)
        VALUES (?, 'overlap a', -1, '14:00', 60, 1)
        """,
        (cats["work"],),
    )
    tid_a = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        """
        INSERT INTO tasks (category_id, name, day_of_week, time_start, duration_min, fixed)
        VALUES (?, 'overlap b', -1, '14:30', 60, 1)
        """,
        (cats["work"],),
    )
    tid_b = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO today_instances (date, task_id, status, source, new_time) VALUES (?, ?, 'pending', 'test', '14:00')",
        (today, tid_a),
    )
    conn.execute(
        "INSERT INTO today_instances (date, task_id, status, source, new_time) VALUES (?, ?, 'pending', 'test', '14:30')",
        (today, tid_b),
    )
    conn.commit()
    conn.close()


def test_detect_conflicts_proposes_resolutions(server, fresh_db):
    _inject_overlapping_tasks(fresh_db)
    result = server.call_tool("detect_conflicts")
    assert result["ok"] is True
    conflicts = result["data"]["conflicts"]
    assert len(conflicts) >= 1
    conflict = conflicts[0]
    assert "proposed_resolutions" in conflict
    assert len(conflict["proposed_resolutions"]) >= 3
    types = {p["type"] for p in conflict["proposed_resolutions"]}
    assert "skip" in types


def test_resolve_conflict_skip(server, fresh_db):
    _inject_overlapping_tasks(fresh_db)
    conflicts = server.call_tool("detect_conflicts")["data"]["conflicts"]
    task_name = conflicts[0]["task"]

    result = server.call_tool("schedule_resolve_conflict", {
        "task_name": task_name,
        "option_index": 3,  # skip option
    })
    assert result["ok"] is True
    assert result["data"]["applied"] == "skip"


def test_resolve_conflict_invalid_index(server, fresh_db):
    _inject_overlapping_tasks(fresh_db)
    conflicts = server.call_tool("detect_conflicts")["data"]["conflicts"]
    task_name = conflicts[0]["task"]

    result = server.call_tool("schedule_resolve_conflict", {
        "task_name": task_name,
        "option_index": 99,
    })
    assert result["ok"] is False
    assert result["error"]["type"] == "validation"
