"""Orbit propagation helpers for TLE-based telemetry (SGP4)."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

try:
    from sgp4.api import Satrec, jday
except Exception:  # pragma: no cover - optional at runtime until installed
    Satrec = None  # type: ignore
    jday = None  # type: ignore

EARTH_RADIUS_KM = 6378.137


def sgp4_available() -> bool:
    return Satrec is not None and jday is not None


def build_satrec(line1: str, line2: str):
    """Build an sgp4 Satrec from TLE lines."""
    if not sgp4_available():
        raise RuntimeError("sgp4 library is not available")
    return Satrec.twoline2rv(line1, line2)


def _gmst(jd_ut1: float) -> float:
    """Greenwich mean sidereal time (radians) for a given Julian date (UT1~UTC)."""
    t = (jd_ut1 - 2451545.0) / 36525.0
    gmst_sec = (
        67310.54841
        + (876600.0 * 3600.0 + 8640184.812866) * t
        + 0.093104 * t * t
        - 6.2e-6 * t * t * t
    )
    gmst_rad = (gmst_sec % 86400.0) * (2.0 * math.pi / 86400.0)
    return gmst_rad % (2.0 * math.pi)


def _teme_to_ecef(r_km, jd: float, fr: float):
    """Rotate TEME position vector (km) to ECEF (km) for given Julian date."""
    x, y, z = r_km
    jd_ut1 = jd + fr
    theta = _gmst(jd_ut1)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    x_e = cos_t * x + sin_t * y
    y_e = -sin_t * x + cos_t * y
    z_e = z
    return x_e, y_e, z_e


def teme_to_geodetic(r_km, jd: float, fr: float):
    """Convert TEME position (km) at given JD to geodetic lat/lon/alt_km.

    Uses a spherical-Earth approximation which is sufficient for visualization
    and dashboard telemetry display.
    """
    x_e, y_e, z_e = _teme_to_ecef(r_km, jd, fr)
    r = math.sqrt(x_e * x_e + y_e * y_e + z_e * z_e)
    lon = math.atan2(y_e, x_e)
    lat = math.asin(max(-1.0, min(1.0, z_e / r))) if r != 0 else 0.0

    lat_deg = math.degrees(lat)
    lon_deg = math.degrees(lon)
    lon_deg = ((lon_deg + 180.0) % 360.0) - 180.0
    alt_km = r - EARTH_RADIUS_KM
    return lat_deg, lon_deg, alt_km


def _propagate_raw(satrec, when: datetime):
    """Return (jd, fr, r_teme_km, v_teme_km_s) or raise on SGP4 error."""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    when = when.astimezone(timezone.utc)
    jd, fr = jday(
        when.year,
        when.month,
        when.day,
        when.hour,
        when.minute,
        when.second + when.microsecond * 1e-6,
    )
    e, r, v = satrec.sgp4(jd, fr)
    if e != 0:
        raise ValueError(f"SGP4 propagation error code: {e}")
    return jd, fr, r, v


def propagate_position(satrec, when: datetime):
    """Return (lat_deg, lon_deg, alt_km, vel_km_s) for given UTC datetime."""
    jd, fr, r, v = _propagate_raw(satrec, when)
    lat, lon, alt = teme_to_geodetic(r, jd, fr)
    vel = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return lat, lon, alt, vel


def orbital_period_minutes(line2: str) -> float:
    """Estimate orbital period (minutes) from TLE line 2 mean motion."""
    try:
        mean_motion = float(line2[52:63])
        if mean_motion > 0:
            return 1440.0 / mean_motion
    except Exception:
        pass
    return 95.0


def compute_ground_track(satrec, line2: str, center: datetime, step_seconds: int = 60):
    """Compute a ground track list of (lat, lon) over ~one orbital period."""
    period = orbital_period_minutes(line2)
    half_span = (period / 2.0) + 5.0  # minutes
    start = center - timedelta(minutes=half_span)
    end = center + timedelta(minutes=half_span)

    points = []
    t = start
    while t <= end:
        try:
            lat, lon, _alt, _vel = propagate_position(satrec, t)
            points.append((lat, lon))
        except Exception:
            pass
        t += timedelta(seconds=step_seconds)
    return points


def _observer_ecef(lat_deg: float, lon_deg: float, alt_m: float = 0.0):
    """Approximate observer ECEF position (km) on a spherical Earth."""
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    r = EARTH_RADIUS_KM + (alt_m / 1000.0)
    x = r * math.cos(lat) * math.cos(lon)
    y = r * math.cos(lat) * math.sin(lon)
    z = r * math.sin(lat)
    return x, y, z


def _az_el_from_ecef(observer_lat: float, observer_lon: float, obs_ecef, sat_ecef):
    """Compute azimuth/elevation (degrees) of sat_ecef from observer."""
    dx = sat_ecef[0] - obs_ecef[0]
    dy = sat_ecef[1] - obs_ecef[1]
    dz = sat_ecef[2] - obs_ecef[2]

    lat = math.radians(observer_lat)
    lon = math.radians(observer_lon)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    sin_lon, cos_lon = math.sin(lon), math.cos(lon)

    # ECEF -> ENU
    e = -sin_lon * dx + cos_lon * dy
    n = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz
    u = cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz

    horiz = math.sqrt(e * e + n * n)
    el = math.degrees(math.atan2(u, horiz))
    az = math.degrees(math.atan2(e, n)) % 360.0
    return az, el


def _az_to_compass(az: float) -> str:
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((az + 11.25) // 22.5) % 16
    return dirs[idx]


def az_to_compass(az: float) -> str:
    """Public helper: convert azimuth degrees to a compass label."""
    return _az_to_compass(az)


def compute_passes(
    satrec,
    observer_lat: float,
    observer_lon: float,
    observer_alt_m: float = 0.0,
    start: datetime | None = None,
    hours: int = 12,
    step_seconds: int = 30,
    min_elevation_deg: float = 0.0,
):
    """Compute satellite passes over an observer for the next N hours.

    Returns a list of dicts: {aos, los, max_elev_deg, max_elev_az_deg, max_elev_time}.
    Uses spherical-Earth approximation; suitable for dashboard display.
    """
    if start is None:
        start = datetime.now(timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    start = start.astimezone(timezone.utc)
    end = start + timedelta(hours=hours)

    obs_ecef = _observer_ecef(observer_lat, observer_lon, observer_alt_m)
    passes = []

    t = start
    in_pass = False
    aos = None
    max_el = -90.0
    max_el_az = 0.0
    max_el_time = None
    prev_el = None
    prev_t = None

    def _elevation_at(moment: datetime):
        jd, fr, r, _v = _propagate_raw(satrec, moment)
        sat_ecef = _teme_to_ecef(r, jd, fr)
        az, el = _az_el_from_ecef(observer_lat, observer_lon, obs_ecef, sat_ecef)
        return az, el

    while t <= end:
        try:
            az, el = _elevation_at(t)
        except Exception:
            t += timedelta(seconds=step_seconds)
            continue

        if not in_pass and el >= min_elevation_deg and (prev_el is not None and prev_el < min_elevation_deg):
            in_pass = True
            # linear-ish interpolate AOS
            if prev_t is not None and prev_el is not None and el != prev_el:
                frac = (min_elevation_deg - prev_el) / (el - prev_el)
                frac = max(0.0, min(1.0, frac))
                aos = prev_t + (t - prev_t) * frac
            else:
                aos = t
            max_el = el
            max_el_az = az
            max_el_time = t
        elif in_pass:
            if el > max_el:
                max_el = el
                max_el_az = az
                max_el_time = t
            if el < min_elevation_deg and prev_el is not None and prev_el >= min_elevation_deg:
                # interpolate LOS
                if prev_t is not None and prev_el is not None and el != prev_el:
                    frac = (min_elevation_deg - prev_el) / (el - prev_el)
                    frac = max(0.0, min(1.0, frac))
                    los = prev_t + (t - prev_t) * frac
                else:
                    los = t
                if aos is not None:
                    passes.append(
                        {
                            "aos": aos,
                            "los": los,
                            "max_elev_deg": max_el,
                            "max_elev_az_deg": max_el_az,
                            "max_elev_time": max_el_time,
                        }
                    )
                in_pass = False
                aos = None
                max_el = -90.0
                max_el_az = 0.0
                max_el_time = None

        prev_el = el
        prev_t = t
        t += timedelta(seconds=step_seconds)

    # close pass that extends beyond window
    if in_pass and aos is not None:
        passes.append(
            {
                "aos": aos,
                "los": end,
                "max_elev_deg": max_el,
                "max_elev_az_deg": max_el_az,
                "max_elev_time": max_el_time,
            }
        )

    return passes
