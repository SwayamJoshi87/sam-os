from samos.db import _handle
from samos.modules.weather.models import current_weather, weather_forecast


def weather_current(location: str):
    """Get current weather for a location."""
    return _handle(current_weather, location=location)


def weather_forecast_days(location: str, days: int = 3):
    """Get a multi-day weather forecast for a location."""
    return _handle(weather_forecast, location=location, days=days)
