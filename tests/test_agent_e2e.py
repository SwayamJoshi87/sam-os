"""End-to-end tests for the agent interface module."""


def test_agent_context_and_briefing(server):
    result = server.call_tool("agent_context_tool")
    assert result["ok"] is True
    ctx = result["data"]
    assert "now" in ctx
    assert "today" in ctx
    assert isinstance(ctx["schedule"], list)
    assert isinstance(ctx["todos"], list)
    assert "meals" in ctx
    assert "workouts" in ctx

    briefing = server.call_tool("agent_briefing_tool")
    assert briefing["ok"] is True
    b = briefing["data"]
    assert "summary" in b
    assert "schedule" in b
    assert "pending_todos" in b
    assert "conflicts" in b


def test_agent_remember_and_query(server):
    remember_result = server.call_tool(
        "agent_remember_tool",
        {"fact": "Swayam prefers morning workouts before 8am", "entity_type": "preference", "entity_name": "Swayam"},
    )
    assert remember_result["ok"] is True
    assert remember_result["data"]["memory_id"] > 0
    assert remember_result["data"]["entity_id"] > 0

    query = server.call_tool("agent_query_tool", {"target": "Swayam"})
    assert query["ok"] is True
    q = query["data"]
    assert any("Swayam" in e["name"] for e in q["entities"])
    assert any("morning workouts" in m["fact"] for m in q["memories"])


def test_agent_search_cross_module(server):
    server.call_tool("todo_add", {"text": "buy blueberries for smoothies", "priority": 2})
    server.call_tool("note_add", {"title": "Blueberry recipe", "body": "Use blueberries, oats, and yogurt"})
    server.call_tool("memory_remember", {"category": "food", "fact": "Blueberries are a staple snack"})
    server.call_tool("project_add", {"name": "Blueberry garden", "description": "Grow blueberries at home"})

    search = server.call_tool("agent_search_tool", {"query": "blue"})
    assert search["ok"] is True
    s = search["data"]
    assert len(s["todos"]) >= 1
    assert len(s["notes"]) >= 1
    assert len(s["memories"]) >= 1
    assert len(s["projects"]) >= 1
