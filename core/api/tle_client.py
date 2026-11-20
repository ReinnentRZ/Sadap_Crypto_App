"""Cached client for CelesTrak GP/TLE data.

CelesTrak requires no API key. Responses are cached on disk so telemetry can
still show recent orbital elements when offline (with a clear stale/fallback
state surfaced by the caller).
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config.settings import TLE_CACHE_DIR, TLE_CACHE_TTL_SECONDS
from core.api.tle_endpoints import build_tle_url
from core.utils.logger import get_logger

logger = get_logger("TleClient")


class TleAPIError(Exception):
    """Raised when TLE fetch fails and no usable cache exists."""


@dataclass
class TleResponse:
    tle: dict  # {"name", "line1", "line2", "norad_id", ...}
    from_cache: bool
    fetched_at: str
    source_url: str


def _format_time(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _cache_file(norad_id: int) -> Path:
    TLE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return TLE_CACHE_DIR / f"tle_{int(norad_id)}.json"


def _read_cache(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "data" not in payload:
            return None
        return payload
    except (OSError, ValueError):
        return None


def _write_cache(path: Path, data: dict, source_url: str) -> None:
    payload = {"cached_at": time.time(), "source_url": source_url, "data": data}
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning(f"Could not write TLE cache {path}: {exc}")


def _epoch_from_tle_line1(line1: str) -> str | None:
    """Derive a human-readable UTC epoch string from TLE line 1."""
    try:
        yy = int(line1[18:20])
        day = float(line1[20:32])
        year = (1900 + yy) if yy >= 57 else (2000 + yy)
        epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day - 1)
        return epoch.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return None


def _parse_tle_text(text: str, norad_id: int) -> dict:
    """Parse CelesTrak TLE/3LE text into a normalized TLE dict."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) >= 3 and lines[1].startswith("1 ") and lines[2].startswith("2 "):
        name, line1, line2 = lines[0], lines[1], lines[2]
    elif len(lines) >= 2 and lines[0].startswith("1 ") and lines[1].startswith("2 "):
        name, line1, line2 = str(norad_id), lines[0], lines[1]
    else:
        raise TleAPIError("TLE text response incomplete")

    epoch = _epoch_from_tle_line1(line1)
    return {
        "name": str(name),
        "line1": line1,
        "line2": line2,
        "norad_id": int(norad_id),
        "epoch": epoch,
        "raw": {"format": "tle"},
    }


def _extract_tle(data: object, norad_id: int) -> dict:
    """Normalize CelesTrak GP JSON (OMM, possibly with TLE fields) into a TLE dict."""
    item = None
    if isinstance(data, list) and data:
        item = data[0]
    elif isinstance(data, dict):
        for key in ("data", "results"):
            if key in data and isinstance(data[key], list) and data[key]:
                item = data[key][0]
                break
        if item is None:
            item = data
    if not isinstance(item, dict):
        raise TleAPIError("Unexpected TLE response format")

    line1 = item.get("TLE_LINE1") or item.get("tle_line1") or item.get("line1")
    line2 = item.get("TLE_LINE2") or item.get("tle_line2") or item.get("line2")
    name = item.get("OBJECT_NAME") or item.get("object_name") or item.get("name") or str(norad_id)
    epoch = item.get("EPOCH") or item.get("epoch")

    # GP JSON (OMM) from CelesTrak typically omits TLE lines; callers should use
    # FORMAT=tle to receive parseable lines. If present, accept them.
    if not line1 or not line2:
        raise TleAPIError("TLE lines not found in response")

    return {
        "name": str(name),
        "line1": str(line1).strip(),
        "line2": str(line2).strip(),
        "norad_id": int(item.get("NORAD_CAT_ID") or norad_id),
        "epoch": epoch,
        "raw": item,
    }


def fetch_tle(norad_id: int, *, ttl_seconds: int = TLE_CACHE_TTL_SECONDS, timeout: int = 12) -> TleResponse:
    """Fetch TLE for a NORAD catalog number with TTL cache and stale-cache fallback."""
    url = build_tle_url(norad_id, fmt="tle")
    cache_path = _cache_file(norad_id)
    cached = _read_cache(cache_path)

    if cached and (time.time() - cached.get("cached_at", 0) < ttl_seconds):
        return TleResponse(
            tle=cached["data"],
            from_cache=True,
            fetched_at=_format_time(cached.get("cached_at", time.time())),
            source_url=cached.get("source_url", url),
        )

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "SadapGroundStation/2.5 (CelesTrak TLE telemetry)",
                "Accept": "text/plain, application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")

        # CelesTrak FORMAT=tle returns plain text; be tolerant of JSON too.
        try:
            data = json.loads(raw)
            tle = _extract_tle(data, norad_id)
        except (json.JSONDecodeError, ValueError):
            tle = _parse_tle_text(raw, norad_id)

        _write_cache(cache_path, tle, url)
        return TleResponse(
            tle=tle,
            from_cache=False,
            fetched_at=_format_time(time.time()),
            source_url=url,
        )
    except (urllib.error.URLError, TimeoutError, ValueError, OSError, TleAPIError) as exc:
        logger.warning(f"TLE request failed for NORAD {norad_id}: {exc}")
        if cached:
            return TleResponse(
                tle=cached["data"],
                from_cache=True,
                fetched_at=_format_time(cached.get("cached_at", time.time())),
                source_url=cached.get("source_url", url),
            )
        raise TleAPIError(str(exc)) from exc
