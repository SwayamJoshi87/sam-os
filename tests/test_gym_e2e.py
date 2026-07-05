"""End-to-end tests for gym tools."""


def test_gym_log_and_prs(server):
    result = server.call_tool("gym_log", {
        "gym": "office",
        "raw_text": "bench 135x10x2 deadlift 225x5",
    })
    assert result["ok"] is True
    data = result["data"]
    assert data["logged_count"] == 3  # 2 sets bench + 1 set deadlift

    prs = server.call_tool("gym_prs", {"gym": "office"})
    assert prs["ok"] is True
    exercises = {p["exercise"] for p in prs["data"]}
    assert "bench" in exercises
    assert "deadlift" in exercises


def test_gym_recent(server):
    server.call_tool("gym_log", {"gym": "home", "raw_text": "squat 185x5x2"})
    result = server.call_tool("gym_recent", {"days": 7})
    assert result["ok"] is True
    assert any(r["exercise"] == "squat" for r in result["data"])


def test_gym_log_invalid_text(server):
    result = server.call_tool("gym_log", {"gym": "office", "raw_text": "hello world"})
    assert result["ok"] is False
    assert result["error"]["type"] == "validation"
