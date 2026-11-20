"""Open-Meteo public forecast and geocoding endpoints with WMO weather-code helpers.

Open-Meteo needs no API key. Coordinates can be any global location.
"""
from urllib.parse import urlencode

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

CURRENT_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "is_day",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]
HOURLY_FIELDS = [
    "temperature_2m",
    "precipitation_probability",
    "weather_code",
    "wind_speed_10m",
]
DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "sunrise",
    "sunset",
]

# WMO weather interpretation codes used by Open-Meteo.
_WMO_DESCRIPTIONS: dict[int, tuple[str, str]] = {
    0: ("Langit cerah", "☀️"),
    1: ("Sebagian besar cerah", "🌤️"),
    2: ("Berawan sebagian", "⛅"),
    3: ("Berawan tebal", "☁️"),
    45: ("Kabut", "🌫️"),
    48: ("Kabut dengan embun beku", "🌫️"),
    51: ("Gerimis ringan", "🌦️"),
    53: ("Gerimis sedang", "🌦️"),
    55: ("Gerimis lebat", "🌦️"),
    56: ("Gerimis beku ringan", "🌧️"),
    57: ("Gerimis beku lebat", "🌧️"),
    61: ("Hujan ringan", "🌧️"),
    63: ("Hujan sedang", "🌧️"),
    65: ("Hujan lebat", "🌧️"),
    66: ("Hujan beku ringan", "🌧️"),
    67: ("Hujan beku lebat", "🌧️"),
    71: ("Salju ringan", "❄️"),
    73: ("Salju sedang", "❄️"),
    75: ("Salju lebat", "❄️"),
    77: ("Butiran salju", "❄️"),
    80: ("Hujan lokal ringan", "🌦️"),
    81: ("Hujan lokal sedang", "🌧️"),
    82: ("Hujan lokal lebat", "⛈️"),
    85: ("Hujan salju ringan", "🌨️"),
    86: ("Hujan salju lebat", "🌨️"),
    95: ("Badai petir", "⛈️"),
    96: ("Badai petir dengan hujan es", "⛈️"),
    99: ("Badai petir dengan hujan es lebat", "⛈️"),
}


def describe_weather_code(code: object) -> tuple[str, str]:
    """Return (description, icon) for a WMO weather code."""
    try:
        return _WMO_DESCRIPTIONS.get(int(code), ("Kondisi tidak diketahui", "❓"))
    except (TypeError, ValueError):
        return "Kondisi tidak diketahui", "❓"


def build_forecast_params(latitude: float, longitude: float, forecast_days: int = 7) -> dict:
    """Build query parameters for a compact dashboard forecast request."""
    return {
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "current": ",".join(CURRENT_FIELDS),
        "hourly": ",".join(HOURLY_FIELDS),
        "daily": ",".join(DAILY_FIELDS),
        "timezone": "auto",
        "forecast_days": forecast_days,
    }


def build_forecast_url(latitude: float, longitude: float, forecast_days: int = 7) -> str:
    """Build the full Open-Meteo forecast URL."""
    params = build_forecast_params(latitude, longitude, forecast_days)
    return f"{OPEN_METEO_FORECAST_URL}?{urlencode(params)}"


def build_geocoding_params(name: str, count: int = 8, language: str = "id") -> dict:
    """Build query parameters for the Open-Meteo geocoding search."""
    return {
        "name": name,
        "count": count,
        "language": language,
        "format": "json",
    }


def build_geocoding_url(name: str, count: int = 8, language: str = "id") -> str:
    """Build the full Open-Meteo geocoding search URL."""
    return f"{OPEN_METEO_GEOCODING_URL}?{urlencode(build_geocoding_params(name, count, language))}"
