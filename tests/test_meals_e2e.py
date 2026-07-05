"""End-to-end tests for meal tools."""


def test_meal_log_and_today(server):
    server.call_tool("meal_target", {
        "calories": 2500,
        "protein_g": 150,
        "carbs_g": 250,
        "fat_g": 80,
    })
    result = server.call_tool("meal_log", {
        "meal_type": "lunch",
        "calories": 700,
        "description": "rice bowl",
        "protein_g": 30,
        "carbs_g": 80,
        "fat_g": 20,
    })
    assert result["ok"] is True
    assert result["data"]["today_total"]["calories"] == 700

    today = server.call_tool("meals_today")
    assert today["ok"] is True
    assert today["data"]["totals"]["calories"] == 700
    assert today["data"]["target"]["calories"] == 2500


def test_meals_week(server):
    server.call_tool("meal_log", {"meal_type": "breakfast", "calories": 400})
    result = server.call_tool("meals_week")
    assert result["ok"] is True
    assert len(result["data"]) >= 1


def test_meal_log_invalid_type(server):
    result = server.call_tool("meal_log", {"meal_type": "brunch", "calories": 500})
    assert result["ok"] is False
    assert result["error"]["type"] == "validation"
