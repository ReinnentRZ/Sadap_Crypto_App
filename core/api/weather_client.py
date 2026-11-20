"""Cached HTTP client for the Open-Meteo public forecast API.

The dashboard keeps forecasts in ``data/cache/weather`` so a demo still has
usable weather data if the connection drops after the first successful fetch.
"""
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from config.settings import WEATHER_CACHE_DIR, WEATHER_CACHE_TTL_SECONDS
from core.api.weather_endpoints import build_forecast_url, build_geocoding_url
from core.utils.logger import get_logger

logger = get_logger("WeatherClient")


class WeatherAPIError(Exception):
    """Raised when a forecast request fails and no usable cache exists."""


@dataclass
class WeatherResponse:
    data: dict
    from_cache: bool
    fetched_at: str
    source_url: str


def _format_time(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _cache_path(latitude: float, longitude: float, forecast_days: int) -> Path:
    name = f"forecast_{latitude:.4f}_{longitude:.4f}_{forecast_days}d".replace("-", "m").replace(".", "_")
    return WEATHER_CACHE_DIR / f"{name}.json"


def _read_cache(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload.get("data"), dict):
            return payload
    except (OSError, ValueError):
        pass
    return None


def _write_cache(path: Path, data: dict, source_url: str) -> None:
    payload = {"cached_at": time.time(), "source_url": source_url, "data": data}
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning(f"Could not write weather cache {path}: {exc}")


def fetch_forecast(
    latitude: float,
    longitude: float,
    forecast_days: int = 7,
    *,
    ttl_seconds: int = WEATHER_CACHE_TTL_SECONDS,
    timeout: int = 12,
) -> WeatherResponse:
    """Fetch an Open-Meteo forecast with TTL cache and stale-cache fallback."""
    url = build_forecast_url(latitude, longitude, forecast_days)
    cache_path = _cache_path(latitude, longitude, forecast_days)
    cached = _read_cache(cache_path)

    if cached and (time.time() - cached.get("cached_at", 0) < ttl_seconds):
        return WeatherResponse(
            data=cached["data"],
            from_cache=True,
            fetched_at=_format_time(cached.get("cached_at", time.time())),
            source_url=cached.get("source_url", url),
        )

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "SadapGroundStation/2.5 (Open-Meteo forecast demo)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Unexpected Open-Meteo response shape")

        _write_cache(cache_path, data, url)
        return WeatherResponse(
            data=data,
            from_cache=False,
            fetched_at=_format_time(time.time()),
            source_url=url,
        )
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning(f"Open-Meteo request failed for {latitude}, {longitude}: {exc}")
        if cached:
            return WeatherResponse(
                data=cached["data"],
                from_cache=True,
                fetched_at=_format_time(cached.get("cached_at", time.time())),
                source_url=cached.get("source_url", url),
            )
        raise WeatherAPIError(str(exc)) from exc


def search_location(name: str, count: int = 8, language: str = "id", timeout: int = 10) -> list[dict]:
    """Search global locations using the public Open-Meteo geocoding API (no key required)."""
    query = name.strip()
    if not query:
        return []

    url = build_geocoding_url(query, count=count, language=language)
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "SadapGroundStation/2.5 (Open-Meteo geocoding)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning(f"Open-Meteo geocoding failed for {query!r}: {exc}")
        raise WeatherAPIError(str(exc)) from exc

    results = data.get("results") or []
    normalized = []
    for item in results:
        if not isinstance(item, dict):
            continue
        lat = item.get("latitude")
        lon = item.get("longitude")
        if lat is None or lon is None:
            continue
        try:
            normalized.append(
                {
                    "name": str(item.get("name") or query),
                    "admin1": str(item.get("admin1") or ""),
                    "country": str(item.get("country") or ""),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "timezone": str(item.get("timezone") or ""),
                }
            )
        except (TypeError, ValueError):
            continue
    return normalized
