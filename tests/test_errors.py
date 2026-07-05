"""Tests for structured error handling."""


def test_invalid_day_name(server):
    result = server.call_tool("schedule_push", {"task_name": "morning gym", "day": "fridai", "permanent": True})
    assert result["ok"] is False
    assert result["error"]["type"] == "validation"


def test_missing_task(server):
    result = server.call_tool("schedule_did", {"task_name": "nonexistent task xyz"})
    assert result["ok"] is False
    assert result["error"]["type"] == "not_found"


def test_invalid_time_format(server):
    result = server.call_tool("schedule_add_today", {
        "task_name": "bad",
        "category": "work",
        "time": "25:00",
        "duration_min": 30,
    })
    assert result["ok"] is False
    assert result["error"]["type"] == "validation"


def test_negative_duration(server):
    result = server.call_tool("schedule_add_today", {
        "task_name": "bad",
        "category": "work",
        "time": "10:00",
        "duration_min": -5,
    })
    assert result["ok"] is False
    assert result["error"]["type"] == "validation"


def test_overlapping_fixed_task(server, fresh_db):
    # Inject a fixed task at 09:00 for today, then try to add another at 09:00
    import sqlite3
    from datetime import datetime

    conn = sqlite3.connect(str(fresh_db))
    conn.row_factory = sqlite3.Row
    work_id = conn.execute("SELECT id FROM categories WHERE name='work'").fetchone()["id"]
    conn.execute(
        "INSERT INTO tasks (category_id, name, day_of_week, time_start, duration_min, fixed) VALUES (?, 'fixed blocker', -1, '09:00', 60, 1)",
        (work_id,),
    )
    tid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO today_instances (date, task_id, status, source, new_time) VALUES (?, ?, 'pending', 'test', '09:00')",
        (today, tid),
    )
    conn.commit()
    conn.close()

    result = server.call_tool("schedule_add_today", {
        "task_name": "overlapping",
        "category": "work",
        "time": "09:00",
        "duration_min": 60,
    })
    assert result["ok"] is False
    assert result["error"]["type"] == "conflict"
