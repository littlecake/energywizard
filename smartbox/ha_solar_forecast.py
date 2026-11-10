"""Optional Solcast forecasts read from Home Assistant, never the Solcast API.

Only aggregate detailedForecast (30 min) or detailedHourly (60 min) attributes
are used. Their values are average kW, regardless of the daily sensor's kWh unit.
"""
from datetime import datetime, timedelta, timezone
import math
import re
import threading
import time

import ew_settings

_ENTITY = re.compile(r"sensor\.[a-z0-9_]+\Z")
_LOCK = threading.RLock()
_CACHE = {"key": None, "until": 0, "periods": [], "state": "disabled"}
MAX_AGE = timedelta(hours=36)


def configuration():
    source = ew_settings.get("solar_forecast_source", "internal")
    entities = ew_settings.get("solar_forecast_entities", [])
    if not isinstance(entities, list):
        entities = []
    return source, tuple(dict.fromkeys(e for e in entities if isinstance(e, str) and _ENTITY.fullmatch(e)))


def validate(source, entities):
    if source not in ("internal", "solcast_ha"):
        raise ValueError("invalid_source")
    if not isinstance(entities, list) or len(entities) > 7 or any(not isinstance(e, str) or not _ENTITY.fullmatch(e) for e in entities):
        raise ValueError("invalid_entities")
    if source == "solcast_ha" and not entities:
        raise ValueError("missing_entities")
    return list(dict.fromkeys(entities))


def _aware(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    return dt.astimezone(timezone.utc)


def parse_state(state, now):
    """Return valid, non-overlapping UTC intervals; missing data stays missing."""
    if not isinstance(state, dict) or state.get("state") in ("unavailable", "unknown", None):
        return []
    try:
        updated = _aware(state["last_updated"])
        if now - updated > MAX_AGE or updated > now + timedelta(minutes=5):
            return []
    except (KeyError, TypeError, ValueError):
        return []
    attrs = state.get("attributes") or {}
    if not isinstance(attrs, dict):
        return []
    half_hourly = attrs.get("detailedForecast")
    records, duration = (half_hourly, 30) if isinstance(half_hourly, list) and half_hourly else (attrs.get("detailedHourly"), 60)
    if not isinstance(records, list):
        return []
    periods = {}
    for record in records:
        try:
            start = _aware(record["period_start"])
            if isinstance(record["pv_estimate"], bool):
                continue
            watts = float(record["pv_estimate"]) * 1000.0
            if not math.isfinite(watts) or watts < 0:
                continue
            end = start + timedelta(minutes=duration)
            if start in periods and periods[start][1] != watts:
                return []
            periods[start] = (end, watts)
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    result = [(start, end, watts) for start, (end, watts) in sorted(periods.items())]
    if any(a[1] > b[0] for a, b in zip(result, result[1:])):
        return []
    return result


def _read_state(entity):
    import homeassistant as ha
    response = ha.requests.get(f"{ha._BASE}/states/{entity}", headers=ha._HEADERS, verify=ha._VERIFY, timeout=4)
    response.raise_for_status()
    return response.json()


def invalidate():
    with _LOCK:
        _CACHE.update(key=None, until=0, periods=[], state="disabled")


def snapshot():
    """Cache HA reads for five minutes per process; never reuse an expired fetch."""
    source, entities = configuration()
    if source != "solcast_ha" or not entities:
        return {"periods": [], "state": "disabled"}
    key = source, entities
    with _LOCK:
        if _CACHE["key"] == key and time.monotonic() < _CACHE["until"]:
            return dict(_CACHE)
        now = datetime.now(timezone.utc)
        combined = {}
        failures = False
        for entity in entities:
            try:
                periods = parse_state(_read_state(entity), now)
            except Exception:
                periods = []
            failures |= not bool(periods)
            for start, end, watts in periods:
                # Selecting both an aggregate and its rooftop would double count.
                # Conflicting intervals invalidate the source instead of guessing.
                if start in combined and combined[start] != (end, watts):
                    _CACHE.update(key=key, until=time.monotonic() + 300, periods=[], state="conflict")
                    return dict(_CACHE)
                combined[start] = (end, watts)
        periods = [(t, end, w) for t, (end, w) in sorted(combined.items())]
        if any(a[1] > b[0] for a, b in zip(periods, periods[1:])):
            periods, state = [], "conflict"
        else:
            state = "partial" if periods and failures else "ready" if periods else "unavailable"
        _CACHE.update(key=key, until=time.monotonic() + 300, periods=periods, state=state)
        return dict(_CACHE)


def average_w(periods, start, end):
    """Time-weighted power; require complete coverage, including explicit zeros."""
    start, end = _aware(start), _aware(end)
    duration = (end - start).total_seconds()
    if duration <= 0:
        return None
    cursor, energy = start, 0.0
    for a, b, watts in periods:
        if b <= cursor:
            continue
        if a > cursor:
            return None
        stop = min(b, end)
        energy += watts * (stop - cursor).total_seconds()
        cursor = stop
        if cursor >= end:
            return energy / duration
    return None


def power_at(dt):
    """Average power for the containing quarter hour, preserving native slots."""
    periods = snapshot()["periods"]
    if not periods:
        return None
    try:
        start = _aware(dt)
    except (TypeError, ValueError):
        return None
    start = start.replace(minute=(start.minute // 15) * 15, second=0, microsecond=0)
    return average_w(periods, start, start + timedelta(minutes=15))


def hourly_w(dt):
    periods = snapshot()["periods"]
    if not periods:
        return None
    try:
        start = _aware(dt)
    except (TypeError, ValueError):
        return None
    return average_w(periods, start, start + timedelta(hours=1))
