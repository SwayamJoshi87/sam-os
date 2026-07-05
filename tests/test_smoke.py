"""Smoke tests: server starts, speaks MCP, exposes expected tools."""

import pytest


def test_server_initializes(server):
    """Server responds to initialize with correct protocol version and server name."""
    resp = server.call("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "pytest", "version": "1.0"},
    })
    result = resp["result"]
    assert result["protocolVersion"] == "2024-11-05"
    assert result["serverInfo"]["name"] == "sam-os"


def test_tools_list_contains_expected_tools(server):
    """Expected tools are registered."""
    resp = server.call("tools/list", {})
    names = {t["name"] for t in resp["result"]["tools"]}
    expected = {
        "schedule_today",
        "schedule_add_today",
        "schedule_remove_today",
        "schedule_retime_today",
        "schedule_push",
        "schedule_did",
        "schedule_skip",
        "schedule_week",
        "schedule_history",
        "schedule_stats",
        "schedule_diff_today_vs_template",
        "detect_conflicts",
        "schedule_resolve_conflict",
        "gym_log",
        "gym_prs",
        "gym_recent",
        "meal_log",
        "meal_target",
        "meals_today",
        "meals_week",
        "system_help",
    }
    assert expected.issubset(names), f"missing: {expected - names}"


def test_system_help(server):
    """system_help returns metadata including tools and schema."""
    result = server.call_tool("system_help")
    assert result["ok"] is True
    data = result["data"]
    assert data["service"]["name"] == "sam-os"
    assert "schedule_today" in data["tools"]
    assert "row_counts" in data
    assert "tables" in data
