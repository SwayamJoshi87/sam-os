"""End-to-end tests for optional email and weather modules."""

from conftest import MCPServerProcess


def test_email_and_weather_tools_load_when_configured(fresh_db, monkeypatch):
    """When env vars are present, the modules register and return structured errors on bad credentials."""
    monkeypatch.setenv("EMAIL_IMAP_HOST", "imap.example.com")
    monkeypatch.setenv("EMAIL_IMAP_USER", "test@example.com")
    monkeypatch.setenv("EMAIL_IMAP_PASSWORD", "secret")
    monkeypatch.setenv("EMAIL_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("OPENWEATHER_API_KEY", "dummy-key")

    with MCPServerProcess(fresh_db) as server:
        tools_resp = server.call("tools/list", {})
        tool_names = {t["name"] for t in tools_resp["result"]["tools"]}

        assert "email_unread" in tool_names
        assert "email_search" in tool_names
        assert "email_read" in tool_names
        assert "email_send" in tool_names
        assert "email_daily_digest" in tool_names
        assert "weather_current" in tool_names
        assert "weather_forecast_days" in tool_names

        email_result = server.call_tool("email_daily_digest")
        assert email_result["ok"] is False
        assert "email" in email_result["error"]["message"].lower()

        weather_result = server.call_tool("weather_current", {"location": "London"})
        assert weather_result["ok"] is False
        assert "weather" in weather_result["error"]["message"].lower()
