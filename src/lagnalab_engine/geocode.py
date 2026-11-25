"""Place name -> (lat, lon) via OpenStreetMap Nominatim (geopy), with a JSON file cache.

Nominatim's usage policy asks for <= 1 request/second and a real User-Agent; the cache keeps us
well inside that. Set LAGNALAB_GEOCODE_CACHE to move the cache file."""
from __future__ import annotations

import json
import os
import threading
import time

CACHE_PATH = os.environ.get("LAGNALAB_GEOCODE_CACHE",
                            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".cache", "geocode.json"))
USER_AGENT = os.environ.get("LAGNALAB_GEOCODE_UA", "lagnalab-engine/0.1 (TuskerMind)")
_lock = threading.Lock()
_last_call = [0.0]


def _load():
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f, indent=1, ensure_ascii=False)
    os.replace(tmp, CACHE_PATH)


def geocode(name: str, geocoder=None) -> dict:
    """Returns {"lat", "lon", "display_name", "source", "cached"}. Raises LookupError if not found."""
    key = " ".join(name.lower().split())
    with _lock:
        cache = _load()
        if key in cache:
            return {**cache[key], "cached": True}
        if geocoder is None:
            from geopy.geocoders import Nominatim
            geocoder = Nominatim(user_agent=USER_AGENT, timeout=10)
        wait = 1.0 - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        loc = geocoder.geocode(name)
        _last_call[0] = time.monotonic()
        if loc is None:
            raise LookupError(f"place not found: {name!r}")
        rec = {"lat": float(loc.latitude), "lon": float(loc.longitude),
               "display_name": getattr(loc, "address", name), "source": "nominatim"}
        cache[key] = rec
        _save(cache)
        return {**rec, "cached": False}
