"""End-to-end tests for new personal context modules."""

from conftest import MCPServerProcess


def test_todos(server: MCPServerProcess):
    resp = server.call_tool("todo_add", {"text": "buy milk", "priority": 2, "tags": "errands,grocery"})
    assert resp["ok"]
    assert resp["data"]["text"] == "buy milk"

    resp = server.call_tool("todo_list", {})
    assert resp["ok"]
    assert any(t["text"] == "buy milk" for t in resp["data"])

    resp = server.call_tool("todo_today", {})
    assert resp["ok"]


def test_notes(server: MCPServerProcess):
    resp = server.call_tool("note_add", {"title": "idea", "body": "build a robot", "tags": "ideas"})
    assert resp["ok"]

    resp = server.call_tool("note_search", {"query": "robot"})
    assert resp["ok"]
    assert len(resp["data"]) >= 1


def test_journal(server: MCPServerProcess):
    resp = server.call_tool("journal_add", {"date": "2099-01-01", "entry": "productive day", "mood": 8})
    assert resp["ok"]

    resp = server.call_tool("journal_get", {"date": "2099-01-01"})
    assert resp["ok"]
    assert resp["data"]["entry"] == "productive day"


def test_memories(server: MCPServerProcess):
    resp = server.call_tool("memory_remember", {"category": "preferences", "fact": "prefers mornings"})
    assert resp["ok"]

    resp = server.call_tool("memory_recall", {"category": "preferences"})
    assert resp["ok"]
    assert any("mornings" in m["fact"] for m in resp["data"])


def test_projects(server: MCPServerProcess):
    resp = server.call_tool("project_add", {"name": "home gym", "description": "setup basement gym"})
    assert resp["ok"]

    resp = server.call_tool("project_list", {})
    assert resp["ok"]
    assert any(p["name"] == "home gym" for p in resp["data"])


def test_profile(server: MCPServerProcess):
    resp = server.call_tool("profile_set", {"key": "timezone", "value": "America/Toronto"})
    assert resp["ok"]

    resp = server.call_tool("profile_get", {"key": "timezone"})
    assert resp["ok"]
    assert resp["data"]["value"] == "America/Toronto"
