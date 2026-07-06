from samos.modules.weather.tools import weather_current, weather_forecast_days

MODULE = {
    "name": "weather",
    "display_name": "Weather",
    "description": "Current conditions and forecast via OpenWeatherMap.",
    "required_env": ["OPENWEATHER_API_KEY"],
    "tools": [weather_current, weather_forecast_days],
    "resources": [],
    "scheduler_jobs": [],
}
