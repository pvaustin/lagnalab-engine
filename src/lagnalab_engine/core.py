"""Astrological computations on top of ephemeris.py. All jd values are Julian days in UT."""
from __future__ import annotations

from dataclasses import dataclass

from . import ephemeris as E
from .constants import (COMBUSTION_ORB, DIG_BALA_HOUSE, EXALTATION, GRAHAS, MANDI_GHATIKA_DAY,
                        MANDI_GHATIKA_NIGHT, NAISARGIKA, NAK_SPAN, SIGN_LORD, VIMSHOTTARI_ORDER,
                        VIMSHOTTARI_YEARS, WEEKDAY_LORD, YOGAS, TITHIS, karana_name)

WEEK_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


def norm180(x: float) -> float:
    x = E.norm360(x)
    return x - 360.0 if x > 180.0 else x


# ------------------------------------------------------------------ grahas
def graha_longitudes(jd, node="mean", position_type="apparent"):
    return {g: E.body(jd, g, node, position_type) for g in GRAHAS}


def is_retrograde(name: str, speed: float, node: str) -> bool:
    if name in ("Sun", "Moon"):
        return False
    if name in ("Rahu", "Ketu") and node == "mean":
        return True  # the mean node always moves backwards
    return speed < 0


def combustion(name, lon, sun_lon, retro, moon_combustion=True):
    if name not in COMBUSTION_ORB or (name == "Moon" and not moon_combustion):
        return None, None
    orb = COMBUSTION_ORB[name][1 if retro else 0]
    return abs(norm180(lon - sun_lon)) <= orb, float(orb)


def dignity(name: str, sign: int, house: int):
    if name not in EXALTATION:
        return dict(exalted=False, debilitated=False, sign_relation=None, dig_bala=False)
    ex_sign = EXALTATION[name][0]
    lord = SIGN_LORD[sign]
    if lord == name:
        rel = "own"
    elif lord in NAISARGIKA[name]["friends"]:
        rel = "friend"
    elif lord in NAISARGIKA[name]["enemies"]:
        rel = "enemy"
    else:
        rel = "neutral"
    return dict(exalted=sign == ex_sign, debilitated=sign == (ex_sign + 6) % 12,
                sign_relation=rel, dig_bala=DIG_BALA_HOUSE.get(name) == house)


# ------------------------------------------------------------------ day / night
@dataclass
class DayNight:
    is_day: bool
    vedic_weekday: int       # 0 = Sunday
    start: float             # jd of sunrise (day) or sunset (night)
    end: float
    sunrise: float           # sunrise of the vedic day
    sunset: float


def day_night(jd_birth: float, jd_local_midnight: float, civil_weekday: int, lat, lon, convention):
    """jd_local_midnight: UT jd of 00:00 local civil time on the birth date."""
    sr = E.next_sunrise(jd_local_midnight, lat, lon, convention)
    if jd_birth >= sr:
        ss = E.next_sunset(sr, lat, lon, convention)
        if jd_birth < ss:
            return DayNight(True, civil_weekday, sr, ss, sr, ss)
        nsr = E.next_sunrise(ss, lat, lon, convention)
        return DayNight(False, civil_weekday, ss, nsr, sr, ss)
    # before sunrise: night belonging to the previous vedic day
    psr = E.next_sunrise(sr - 1.1, lat, lon, convention)
    pss = E.next_sunset(psr, lat, lon, convention)
    return DayNight(False, (civil_weekday - 1) % 7, pss, sr, psr, pss)


def segment_lords(dn: DayNight):
    """Lords of the 8 equal parts of the day or night. Day: from the weekday lord in weekday
    order; night: from the lord of the 5th weekday (counting the day itself as 1st). Part 8 has
    no lord (None)."""
    first = dn.vedic_weekday if dn.is_day else (dn.vedic_weekday + 4) % 7
    return [WEEK_ORDER[(first + i) % 7] for i in range(7)] + [None]


def saturn_segment(dn: DayNight):
    lords = segment_lords(dn)
    i = lords.index("Saturn")
    part = (dn.end - dn.start) / 8.0
    return dn.start + i * part, dn.start + (i + 1) * part


def gulika_time(dn: DayNight, point: str) -> float:
    a, b = saturn_segment(dn)
    return {"start": a, "middle": (a + b) / 2, "end": b}[point]


def mandi_time(dn: DayNight, method: str) -> float:
    if method == "prasna_marga_ghatika":
        gh = (MANDI_GHATIKA_DAY if dn.is_day else MANDI_GHATIKA_NIGHT)[dn.vedic_weekday]
        return dn.start + (dn.end - dn.start) * gh / 30.0
    return gulika_time(dn, method.replace("saturn_segment_", ""))


# ------------------------------------------------------------------ panchanga
def _sun_moon(jd, position_type):
    s = E.body(jd, "Sun", position_type=position_type)
    m = E.body(jd, "Moon", position_type=position_type)
    return s, m


def _angle_fn(kind, position_type):
    def f(jd):
        s, m = _sun_moon(jd, position_type)
        if kind == "elong":
            return E.norm360(m.longitude - s.longitude), m.speed - s.speed
        if kind == "moon":
            return m.longitude, m.speed
        if kind == "sum":
            return E.norm360(m.longitude + s.longitude), m.speed + s.speed
        raise ValueError(kind)
    return f


def find_angle_time(f, jd_guess: float, target: float) -> float:
    jd = jd_guess
    for _ in range(30):
        val, rate = f(jd)
        delta = norm180(target - val)
        if abs(delta) < 1e-8:
            break
        jd += delta / rate
    return jd


def _span(f, jd, step):
    val, _ = f(jd)
    i = int(val // step)
    start = find_angle_time(f, jd - (val - i * step) / f(jd)[1], (i * step) % 360)
    end = find_angle_time(f, jd + ((i + 1) * step - val) / f(jd)[1], ((i + 1) * step) % 360)
    return i, val, start, end


def panchanga_elements(jd, position_type="apparent"):
    out = {}
    fe = _angle_fn("elong", position_type)
    i, val, st, en = _span(fe, jd, 12.0)
    if i == 14:
        name = "Purnima"
    elif i == 29:
        name = "Amavasya"
    else:
        name = TITHIS[i % 15]
    out["tithi"] = dict(number=i + 1, name=name, paksha="Shukla" if i < 15 else "Krishna",
                        elongation_deg=val, fraction_elapsed=(val - 12 * i) / 12, start_jd=st, end_jd=en)
    k, _, kst, ken = _span(fe, jd, 6.0)
    out["karana"] = dict(number=k + 1, name=karana_name(k), start_jd=kst, end_jd=ken)
    fm = _angle_fn("moon", position_type)
    n, mval, nst, nen = _span(fm, jd, NAK_SPAN)
    out["nakshatra"] = dict(index=n + 1, pada=E.nakshatra_of(mval)[1], start_jd=nst, end_jd=nen,
                            fraction_elapsed=(mval - n * NAK_SPAN) / NAK_SPAN)
    fs = _angle_fn("sum", position_type)
    y, yval, yst, yen = _span(fs, jd, NAK_SPAN)
    out["yoga"] = dict(number=y + 1, name=YOGAS[y], start_jd=yst, end_jd=yen)
    return out


# ------------------------------------------------------------------ vimshottari
def proportional_years(*lord_years: int) -> float:
    """Aṃśa division shared by daśā, apahāra and chidra.

    One lord is that daśā's years. Each further lord multiplies by its years / 120,
    so apahāra = mahadasha years × antardasha years / 120 and
    chidra = that × chidra years / 120. Calendar days are this count times the
    selected year length (365.25 or 360). The loop below calls this for apahāra.
    Chidra uses the same function; the chart response does not emit that level.
    """
    if not lord_years:
        raise ValueError("need at least one dasha lord")
    # Left-associative `a * b / 120`, the product the mahadasha/bhukti loop has
    # always used. Starting from an int keeps the two-lord case bitwise-identical.
    years: float = lord_years[0]
    for n in lord_years[1:]:
        years = years * n / 120.0
    return years


def vimshottari(moon_lon: float, jd_birth: float, year_days: float):
    n = int(moon_lon // NAK_SPAN)
    frac = (moon_lon - n * NAK_SPAN) / NAK_SPAN
    lord_i = n % 9
    lord = VIMSHOTTARI_ORDER[lord_i]
    yrs = VIMSHOTTARI_YEARS[lord]
    balance = (1 - frac) * yrs
    start = jd_birth - frac * yrs * year_days
    mds = []
    for k in range(9):
        md = VIMSHOTTARI_ORDER[(lord_i + k) % 9]
        md_years = VIMSHOTTARI_YEARS[md]
        md_end = start + md_years * year_days
        bh = []
        b_start = start
        for j in range(9):
            bl = VIMSHOTTARI_ORDER[(lord_i + k + j) % 9]
            b_years = proportional_years(md_years, VIMSHOTTARI_YEARS[bl])
            b_end = b_start + b_years * year_days
            bh.append((bl, b_start, b_end, b_years))
            b_start = b_end
        mds.append((md, start, md_end, md_years, bh))
        start = md_end
    return dict(lord=lord, frac=frac, balance=balance, mahadashas=mds)


# Printed years/months/days of the balance at birth. Independent of dasha_year_days:
# that length scales only the calendar dates of the periods.
YMD_RULE = (
    "Years, months and days decompose the balance in years as 1 year = 12 months "
    "and 1 month = 30 days, with the leftover days truncated toward zero (not rounded). "
    "This split does not use dasha_year_days."
)


def years_to_ymd_parts(y: float) -> tuple[int, int, int]:
    """Traditional y/m/d. See YMD_RULE.

    Truncating the day is what a printed balance does: 16.588 years is
    16 years, 7 months, 1 day. Rounding the day would make that 2.
    """
    if y < 0:
        raise ValueError("dasha balance years must be >= 0")
    # 360 of these days = 1 year. The epsilon keeps a value that lands on a
    # month boundary from being dropped by binary rounding.
    total = int(y * 360.0 + 1e-8)
    yi, rem = divmod(total, 360)
    mi, di = divmod(rem, 30)
    return yi, mi, di


def years_to_ymd(y: float) -> str:
    """Same split as years_to_ymd_parts, with the leftover day shown to 0.1."""
    yi = int(y)
    m = (y - yi) * 12
    mi = int(m)
    d = (m - mi) * 30
    return f"{yi}y {mi}m {d:.1f}d"
