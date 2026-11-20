"""Small, cached HTTP client for NASA Open APIs.

All requests are read-only. Responses are cached on disk so the cover dashboard
still has something useful to show during a demo with unstable internet access.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from config.settings import NASA_API_KEY, NASA_CACHE_DIR, NASA_CACHE_TTL_SECONDS
from core.utils.logger import get_logger

logger = get_logger("NasaClient")


class NasaAPIError(Exception):
    """Raised when a NASA request fails and no usable cache exists."""


@dataclass
class NasaResponse:
    data: dict | list
    from_cache: bool
    fetched_at: str
    source_url: str


def _format_time(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _cache_file(cache_name: str, suffix: str = ".json") -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in cache_name)
    return NASA_CACHE_DIR / f"{safe_name}{suffix}"


def _read_json_cache(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "data" not in payload:
            return None
        return payload
    except (OSError, ValueError):
        return None


def _write_json_cache(path: Path, data: dict | list, source_url: str) -> None:
    payload = {"cached_at": time.time(), "source_url": source_url, "data": data}
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning(f"Could not write NASA cache {path}: {exc}")


def fetch(
    endpoint: str,
    params: dict | None = None,
    *,
    use_key: bool = True,
    cache_name: str | None = None,
    ttl_seconds: int = NASA_CACHE_TTL_SECONDS,
    timeout: int = 12,
) -> NasaResponse:
    """Fetch JSON from a NASA endpoint with TTL cache and stale-cache fallback."""
    query = dict(params or {})
    if use_key and "api_key" not in query:
        query["api_key"] = NASA_API_KEY

    suffix = f"?{urllib.parse.urlencode(query)}" if query else ""
    url = f"{endpoint}{suffix}"
    cache_path = _cache_file(cache_name) if cache_name else None
    cached = _read_json_cache(cache_path) if cache_path else None

    if cached and (time.time() - cached.get("cached_at", 0) < ttl_seconds):
        return NasaResponse(
            data=cached["data"],
            from_cache=True,
            fetched_at=_format_time(cached.get("cached_at", time.time())),
            source_url=cached.get("source_url", url),
        )

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "SadapGroundStation/2.4 (NASA Open APIs demo)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)

        if cache_path:
            _write_json_cache(cache_path, data, url)

        return NasaResponse(
            data=data,
            from_cache=False,
            fetched_at=_format_time(time.time()),
            source_url=url,
        )
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning(f"NASA request failed for {endpoint}: {exc}")
        if cached:
            return NasaResponse(
                data=cached["data"],
                from_cache=True,
                fetched_at=_format_time(cached.get("cached_at", time.time())),
                source_url=cached.get("source_url", url),
            )
        raise NasaAPIError(str(exc)) from exc


def fetch_image_bytes(url: str, cache_name: str, timeout: int = 15) -> tuple[bytes, bool]:
    """Download an image with a simple disk cache. Returns (bytes, from_cache)."""
    cache_path = _cache_file(cache_name, ".img")
    if cache_path.exists():
        try:
            return cache_path.read_bytes(), True
        except OSError:
            pass

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "SadapGroundStation/2.4 (NASA Open APIs demo)"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
        try:
            cache_path.write_bytes(payload)
        except OSError as exc:
            logger.warning(f"Could not cache NASA image {cache_path}: {exc}")
        return payload, False
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise NasaAPIError(str(exc)) from exc
