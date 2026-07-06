"""End-to-end tests for new sam-os features."""

import pytest

from conftest import MCPServerProcess


def test_template_management(server: MCPServerProcess):
    # Add a category and template task
    resp = server.call_tool("category_add", {"name": "test-cat", "color": "#123456"})
    assert resp["ok"]

    resp = server.call_tool(
        "template_add",
        {
            "name": "test task",
            "day": "mon",
            "time_start": "09:00",
            "duration_min": 30,
            "category": "test-cat",
            "fixed": True,
        },
    )
    assert resp["ok"]
    assert resp["data"]["name"] == "test task"

    resp = server.call_tool("schedule_week", {})
    assert resp["ok"]
    assert any(t["name"] == "test task" for t in resp["data"]["mon"])

    resp = server.call_tool(
        "template_update", {"task_name": "test task", "duration_min": 45}
    )
    assert resp["ok"]
    assert resp["data"]["duration_min"] == 45

    resp = server.call_tool("template_remove", {"task_name": "test task"})
    assert resp["ok"]


def test_wellness(server: MCPServerProcess):
    resp = server.call_tool("water_log", {"amount_ml": 500})
    assert resp["ok"]

    resp = server.call_tool("water_today_tool", {})
    assert resp["ok"]
    assert resp["data"]["total_ml"] == 500

    resp = server.call_tool("sleep_log", {"hours": 7.5, "quality": 8})
    assert resp["ok"]

    resp = server.call_tool("sleep_history_tool", {"days": 7})
    assert resp["ok"]
    assert len(resp["data"]) >= 1

    resp = server.call_tool("mood_log", {"level": 7, "label": "good", "note": "productive"})
    assert resp["ok"]


def test_productivity(server: MCPServerProcess):
    resp = server.call_tool("habit_add", {"name": "read", "description": "read 10 pages"})
    assert resp["ok"]

    resp = server.call_tool("habit_log", {"habit_name": "read", "status": "done"})
    assert resp["ok"]

    resp = server.call_tool("habits_today_tool", {})
    assert resp["ok"]
    assert any(h["name"] == "read" and h["status"] == "done" for h in resp["data"]["habits"])

    resp = server.call_tool("shopping_add", {"item": "milk", "category": "dairy"})
    assert resp["ok"]

    resp = server.call_tool("shopping_list_tool", {})
    assert resp["ok"]
    assert any(i["item"] == "milk" for i in resp["data"]["items"])

    resp = server.call_tool("away_mode_add", {"start_date": "2099-01-01", "end_date": "2099-01-07"})
    assert resp["ok"]

    resp = server.call_tool("away_mode_check", {"date": "2099-01-03"})
    assert resp["ok"]
    assert resp["data"]["away"] is True


def test_meal_templates(server: MCPServerProcess):
    resp = server.call_tool(
        "meal_template_add",
        {
            "name": "protein oats",
            "meal_type": "breakfast",
            "calories": 500,
            "protein_g": 30,
            "carbs_g": 60,
            "fat_g": 12,
        },
    )
    assert resp["ok"]

    resp = server.call_tool("meal_log_template", {"name": "protein oats"})
    assert resp["ok"]
    assert resp["data"]["today_total"]["calories"] == 500


def test_system_health_and_state(server: MCPServerProcess):
    resp = server.call_tool("system_health", {})
    assert resp["ok"]
    assert "row_counts" in resp["data"]

    resp = server.call_tool("backup_status_tool", {})
    assert resp["ok"]

    resp = server.call_tool("weekly_prep_tool", {})
    assert resp["ok"]
