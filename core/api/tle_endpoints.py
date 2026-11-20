"""Endpoint helpers for public CelesTrak GP/TLE data (no API key required)."""

CELESTRAK_GP_URL = "https://celestrak.org/NORAD/elements/gp.php"


def build_tle_params(norad_id: int, fmt: str = "tle") -> dict:
    """Build query params to fetch GP/TLE data for a NORAD catalog number."""
    return {"CATNR": int(norad_id), "FORMAT": fmt}


def build_tle_url(norad_id: int, fmt: str = "tle") -> str:
    from urllib.parse import urlencode

    return f"{CELESTRAK_GP_URL}?{urlencode(build_tle_params(norad_id, fmt=fmt))}"
