"""Thin wrapper over pyswisseph. Swiss Ephemeris keeps global state (ephemeris path, sidereal
mode), so every public computation in chart.py runs under LOCK."""
from __future__ import annotations

import math
import os
import threading
from dataclasses import dataclass

import swisseph as swe

from .constants import NAK_SPAN, PADA_SPAN

LOCK = threading.RLock()
EPHE_PATH = os.environ.get("LAGNALAB_EPHE_PATH",
                           os.path.join(os.path.dirname(__file__), "ephe"))
_tls = threading.local()


def ensure_thread_init() -> None:
    """The Swiss Ephemeris C library keeps its state in thread-local storage, so the ephemeris
    path must be set in every thread that computes (FastAPI runs sync handlers in a threadpool).
    Without this, worker threads silently fall back to the Moshier ephemeris."""
    if getattr(_tls, "path", None) != EPHE_PATH:
        swe.set_ephe_path(EPHE_PATH)
        _tls.path = EPHE_PATH


ensure_thread_init()

AYANAMSA_MODES = {
    "lahiri": swe.SIDM_LAHIRI,
    "raman": swe.SIDM_RAMAN,
    "kp": swe.SIDM_KRISHNAMURTI,
    "true_chitra": swe.SIDM_TRUE_CITRA,
}

PLANET_IDS = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
              "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN}


def norm360(x: float) -> float:
    x = math.fmod(x, 360.0)
    return x + 360.0 if x < 0 else x


def julday_utc(dt) -> float:
    """dt: aware UTC datetime -> Julian day (UT)."""
    h = dt.hour + dt.minute / 60 + (dt.second + dt.microsecond / 1e6) / 3600
    return swe.julday(dt.year, dt.month, dt.day, h, swe.GREG_CAL)


def jd_to_utc_tuple(jd: float):
    y, m, d, h = swe.revjul(jd, swe.GREG_CAL)
    return y, m, d, h


def set_ayanamsa(name: str) -> None:
    ensure_thread_init()
    try:
        swe.set_sid_mode(AYANAMSA_MODES[name])
    except KeyError:
        raise ValueError(f"unknown ayanamsa {name!r}; choose from {sorted(AYANAMSA_MODES)}")


def ayanamsa_value(jd: float) -> float:
    return swe.get_ayanamsa_ex_ut(jd, swe.FLG_SWIEPH)[1]


def _flags(position_type: str) -> int:
    f = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
    if position_type == "true_geometric":
        f |= swe.FLG_TRUEPOS
    elif position_type != "apparent":
        raise ValueError("position_type must be 'apparent' or 'true_geometric'")
    return f


@dataclass
class Body:
    longitude: float  # sidereal, degrees
    speed: float      # degrees/day
    ephemeris: str    # "swiss" or "moshier"


def body(jd: float, name: str, node: str = "mean", position_type: str = "apparent") -> Body:
    flags = _flags(position_type)
    if name in ("Rahu", "Ketu"):
        pid = swe.MEAN_NODE if node == "mean" else swe.TRUE_NODE
    else:
        pid = PLANET_IDS[name]
    xx, ret = swe.calc_ut(jd, pid, flags)
    lon = norm360(xx[0])
    if name == "Ketu":
        lon = norm360(lon + 180.0)
    src = "moshier" if (ret & swe.FLG_MOSEPH) else "swiss"
    return Body(lon, xx[3], src)


def ascendant(jd: float, lat: float, lon: float) -> float:
    """Sidereal ascendant (current sid mode)."""
    _cusps, ascmc = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
    return norm360(ascmc[0])


# ---------------------------------------------------------------- rise / set
RISE_CONVENTIONS = {
    # Classical Hindu rising: centre of the disc on the true horizon, no refraction
    # (swe.BIT_HINDU_RISING). Matches PyJHora's default.
    "hindu": swe.BIT_HINDU_RISING,
    # Civil/astronomical sunrise: upper limb, standard refraction (what most almanac sites print).
    "apparent_upper_limb": 0,
}

# Daily timings use this one sunrise convention: Drik, upper limb, standard
# refraction (the "apparent_upper_limb" flag above, which is 0). Birth charts
# keep their own sunrise_convention and do not read this constant.
TIMINGS_SUNRISE_CONVENTION = "apparent_upper_limb"


def _rise_set(jd_start: float, lat: float, lon: float, rise: bool, convention: str) -> float:
    rsmi = (swe.CALC_RISE if rise else swe.CALC_SET) | RISE_CONVENTIONS[convention]
    res, tret = swe.rise_trans(jd_start, swe.SUN, rsmi, (lon, lat, 0.0), 1013.25, 15.0, swe.FLG_SWIEPH)
    if res != 0:
        raise ValueError("the Sun does not rise or set on this date at this latitude; "
                         "sunrise-based values (weekday, Gulika/Mandi) cannot be computed")
    return tret[0]


def next_sunrise(jd_start, lat, lon, convention="hindu"):
    return _rise_set(jd_start, lat, lon, True, convention)


def next_sunset(jd_start, lat, lon, convention="hindu"):
    return _rise_set(jd_start, lat, lon, False, convention)


def nakshatra_of(longitude: float):
    idx = int(longitude // NAK_SPAN)
    idx = min(idx, 26)
    pada = min(int((longitude - idx * NAK_SPAN) // PADA_SPAN) + 1, 4)
    return idx, pada
