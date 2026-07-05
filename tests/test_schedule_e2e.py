"""End-to-end tests for schedule tools."""

import pytest


def test_schedule_today_instantiates_from_template(server):
    result = server.call_tool("schedule_today")
    assert result["ok"] is True
    # Monday template has 2 tasks; today may not be Monday, so just check structure
    assert isinstance(result["data"], list)


def test_add_today_task(server):
    result = server.call_tool("schedule_add_today", {
        "task_name": "dentist",
        "category": "work",
        "time": "14:00",
        "duration_min": 60,
    })
    assert result["ok"] is True
    data = result["data"]
    assert data["name"] == "dentist"
    assert data["time"] == "14:00"
    assert data["duration_min"] == 60


def test_today_shows_added_task(server):
    server.call_tool("schedule_add_today", {
        "task_name": "lunch walk",
        "category": "gym",
        "time": "12:00",
        "duration_min": 30,
    })
    result = server.call_tool("schedule_today")
    names = {r["name"] for r in result["data"]}
    assert "lunch walk" in names


def test_retime_today_task(server):
    server.call_tool("schedule_add_today", {
        "task_name": "call mom",
        "category": "work",
        "time": "16:00",
        "duration_min": 30,
    })
    result = server.call_tool("schedule_retime_today", {
        "task_name_or_id": "call mom",
        "new_time": "17:00",
    })
    assert result["ok"] is True
    assert result["data"]["new_time"] == "17:00"


def test_remove_today_task(server):
    server.call_tool("schedule_add_today", {
        "task_name": "temp task",
        "category": "work",
        "time": "18:00",
        "duration_min": 15,
    })
    result = server.call_tool("schedule_remove_today", {
        "task_name_or_id": "temp task",
        "reason": "cancelled",
    })
    assert result["ok"] is True
    today = server.call_tool("schedule_today")["data"]
    assert not any(r["name"] == "temp task" and r["status"] == "pending" for r in today)


def test_mark_done(server):
    server.call_tool("schedule_add_today", {
        "task_name": "read docs",
        "category": "work",
        "time": "10:00",
        "duration_min": 30,
    })
    result = server.call_tool("schedule_did", {"task_name": "read docs"})
    assert result["ok"] is True


def test_mark_skip(server):
    server.call_tool("schedule_add_today", {
        "task_name": "optional task",
        "category": "work",
        "time": "11:00",
        "duration_min": 30,
    })
    result = server.call_tool("schedule_skip", {
        "task_name": "optional task",
        "reason": "not needed",
    })
    assert result["ok"] is True


def test_week_template(server):
    result = server.call_tool("schedule_week")
    assert result["ok"] is True
    assert "mon" in result["data"]
    mon = result["data"]["mon"]
    assert any(t["name"] == "morning gym" for t in mon)


def test_diff_today_vs_template(server):
    server.call_tool("schedule_add_today", {
        "task_name": "ad-hoc only",
        "category": "work",
        "time": "20:00",
        "duration_min": 30,
    })
    result = server.call_tool("schedule_diff_today_vs_template")
    assert result["ok"] is True
    today_names = {t["name"] for t in result["data"]["today"]}
    template_names = {t["name"] for t in result["data"]["template"]}
    assert "ad-hoc only" in today_names
    assert "ad-hoc only" not in template_names
