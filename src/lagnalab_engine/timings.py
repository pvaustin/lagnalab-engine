"""One civil day's timings: Drik sunrise, daytime kalams, and panchanga.

Sunrise and sunset use TIMINGS_SUNRISE_CONVENTION only (Drik: upper limb,
standard refraction). Birth charts do not read that constant.

Weekday part tables, 1-indexed, Sunday through Saturday. Daylight from
sunrise to sunset is split into 8 equal parts. Part 1 begins at sunrise
and part 8 ends at sunset.

Sources that print this same table:
- Drik Panchang, Rahu Kaal: eight equal parts of the sunrise-to-sunset day
  (https://www.drikpanchang.com/panchang/rahu-kaal.html). The columns below
  are the weekday parts that page's method, Kerala panchangams, and this
  product all use.
- Panchang Guru, "Rahu Kaal, Yamaganda and Gulika"
  (https://www.panchangguru.com/guides/rahu-kaal), same eight parts.
- Yamaganda is Jupiter's part and Gulika is Saturn's part in the
  weekday-lord count of Brihat Parashara Hora Shastra 3.66-69, as summarised
  from R. Santhanam's translation at
  https://jyotishya.date/learn/rahu-kalam-sources/. Rahu has no part in that
  count: Sunday's Rahu Kalam is the lordless eighth. Kalaprakasika
  (N. P. Subramania Iyer, 1917) gives the same weekday positions on a fixed
  6:00-18:00 day, and also night periods for Yamaganda and Gulika.

Disagreements, not followed here:
- A minority of sites shift Yamaganda and Gulika one part earlier. That
  shift does not match the BPHS count above. This file keeps the product
  table, which matches Drik and that count.
- Kalaprakasika's night Yamaganda and night Gulika are not computed. The
  product asks for the daytime parts only.
- Kalaprakasika's worked examples use a mean 6:00-18:00 day. The parts here
  are scaled to the true Drik sunrise and sunset, which is what Drik prints.
- This Gulika kalam is not the birth-chart Gulika. The chart's Gulika is the
  Prasna Marga Mandi ghatika, a rising instant that can fall at night
  (constants.MANDI_GHATIKA_DAY). The timings page does not return that point.
"""
from __future__ import annotations

from datetime import date, time, timedelta, timezone

import zoneinfo

from . import __version__
from . import core as C
from . import ephemeris as E
from . import timeutil
from .chart import jd_to_dt
from .constants import (NAKSHATRAS, NAKSHATRAS_IAST, NAKSHATRAS_ML, NAKSHATRAS_ML_LATIN,
                        VIMSHOTTARI_ORDER, karana_record, tithi_record, vara_record,
                        yoga_record)
from .ephemeris import TIMINGS_SUNRISE_CONVENTION

# Sunday .. Saturday. Values are the 1-indexed eighth of the daytime.
RAHU_PART = (8, 2, 7, 5, 6, 4, 3)
YAMAGANDAM_PART = (5, 4, 3, 2, 1, 7, 6)
GULIKA_PART = (7, 6, 5, 4, 3, 2, 1)
KALAM_PARTS = {"rahu": RAHU_PART, "yamagandam": YAMAGANDAM_PART, "gulika": GULIKA_PART}

# Malayalam solar months follow the sidereal signs. 0 = Mesha = Medam.
# The spellings match the rasi names already used on the chart.
KOLLAVARSHAM_MONTHS = (
    ("Medam", "മേടം"), ("Edavam", "ഇടവം"), ("Mithunam", "മിഥുനം"),
    ("Karkidakam", "കർക്കടകം"), ("Chingam", "ചിങ്ങം"), ("Kanni", "കന്നി"),
    ("Thulam", "തുലാം"), ("Vrischikam", "വൃശ്ചികം"), ("Dhanu", "ധനു"),
    ("Makaram", "മകരം"), ("Kumbham", "കുംഭം"), ("Meenam", "മീനം"),
)
# Malayali rule (Positional Astronomy Centre, Kolkata, "Indian Calendars"):
# the month begins on the sankranti's civil day when the ingress is at or
# before aparahna, otherwise on the next civil day. Aparahna is 3/5 of the
# sunrise-to-sunset day. The Kollam year turns on Chingam 1.
APARAHNA_FRACTION = 3.0 / 5.0
KOLLAVARSHAM_RULE = (
    "Malayali solar rule: Lahiri sankranti, month starts that civil day if the "
    "ingress is at or before aparahna (3/5 of the Drik sunrise-to-sunset day), "
    "otherwise the next civil day. Kollam year increments on Chingam 1 "
    "(Gregorian year minus 824 on and after that day, otherwise minus 825)."
)
NO_DAYLIGHT = "the Sun does not rise and set within this civil day at this place"


def weekday_sun0(d: date) -> int:
    """0 = Sunday .. 6 = Saturday. datetime.date.weekday() is Monday = 0."""
    return (d.weekday() + 1) % 7


def kalam_window(sunrise_jd: float, sunset_jd: float, part: int) -> tuple[float, float]:
    """Start and end JD of one equal daytime eighth. `part` is 1..8."""
    if not 1 <= part <= 8:
        raise ValueError("kalam part must be 1..8")
    span = sunset_jd - sunrise_jd
    if span <= 0:
        raise ValueError("sunset must be after sunrise")
    step = span / 8.0
    return sunrise_jd + (part - 1) * step, sunrise_jd + part * step


def civil_month_start(sankranti_jd: float, sunrise_jd: float, sunset_jd: float,
                      sankranti_day: date) -> date:
    """Malayali rule. Aparahna is APARAHNA_FRACTION of that day's daylight."""
    if sunset_jd <= sunrise_jd:
        raise ValueError("sunset must be after sunrise")
    aparahna = sunrise_jd + APARAHNA_FRACTION * (sunset_jd - sunrise_jd)
    if sankranti_jd <= aparahna:
        return sankranti_day
    return sankranti_day + timedelta(days=1)


def _iso(jd: float | None, zone) -> str | None:
    if jd is None:
        return None
    return jd_to_dt(jd).astimezone(zone).isoformat(timespec="seconds")


def _resolve_zone(d: date, lat: float, lon: float, tz: str | None):
    rt = timeutil.resolve(d, time(12, 0), tz, lat, lon)
    if rt.offset_source.startswith("iana:") and rt.tz_name:
        zone = zoneinfo.ZoneInfo(rt.tz_name)
    else:
        zone = timezone(timedelta(seconds=rt.utc_offset_seconds))
    return rt, zone


def _jd_midnight(d: date, tz_name: str | None, lat: float, lon: float) -> tuple[float, list[str]]:
    rt = timeutil.resolve(d, time(0, 0), tz_name, lat, lon)
    return E.julday_utc(rt.utc), list(rt.warnings)


def _daylight(jd_midnight: float, lat: float, lon: float) -> tuple[float | None, float | None]:
    """Sunrise and the following sunset when both belong to this civil day.

    A sunrise exactly at local midnight counts. If the next rise or set is
    not inside the civil day (polar day or night, or the Sun stays up or
    down through the date), both come back as None.
    """
    conv = TIMINGS_SUNRISE_CONVENTION
    start = jd_midnight - 1.0 / 1440.0
    end = jd_midnight + 1.0
    try:
        sr = E.next_sunrise(start, lat, lon, conv)
    except ValueError:
        return None, None
    if sr < jd_midnight or sr >= end:
        return None, None
    try:
        ss = E.next_sunset(sr, lat, lon, conv)
    except ValueError:
        return None, None
    if ss <= sr or ss >= sr + 1.0:
        return None, None
    return sr, ss


def _sun_angle(jd: float):
    body = E.body(jd, "Sun", position_type="apparent")
    return body.longitude, body.speed


def _sankranti(jd_guess: float, sign: int) -> float:
    return C.find_angle_time(_sun_angle, jd_guess, (sign * 30.0) % 360.0)


def _local_date(jd: float, zone) -> date:
    return jd_to_dt(jd).astimezone(zone).date()


def _kollavarsham(d: date, lat: float, lon: float, tz_name: str | None, zone, jd_noon: float):
    """Kollam year, Malayalam month and day, or None when daylight is missing."""
    lon_noon, _rate = _sun_angle(jd_noon)
    sign_now = int(lon_noon // 30.0) % 12
    best = None
    for sign in ((sign_now - 1) % 12, sign_now, (sign_now + 1) % 12):
        delta = (sign - sign_now + 6) % 12 - 6  # -6..+5 signs
        sk = _sankranti(jd_noon + delta * 30.4, sign)
        if abs(sk - jd_noon) > 45:
            continue
        sk_day = _local_date(sk, zone)
        jd0, _w = _jd_midnight(sk_day, tz_name, lat, lon)
        sr, ss = _daylight(jd0, lat, lon)
        if sr is None or ss is None:
            return None
        start = civil_month_start(sk, sr, ss, sk_day)
        if start <= d and (best is None or start > best[0]):
            day_no = (d - start).days + 1
            if 1 <= day_no <= 33:
                best = (start, sign, day_no)
    if best is None:
        return None
    # Chingam 1 of this Gregorian year: Simha ingress near mid-August.
    aug = timeutil.resolve(date(d.year, 8, 16), time(6, 0), tz_name, lat, lon)
    ch_sk = _sankranti(E.julday_utc(aug.utc), 4)
    ch_day = _local_date(ch_sk, zone)
    jd_ch, _w = _jd_midnight(ch_day, tz_name, lat, lon)
    ch_sr, ch_ss = _daylight(jd_ch, lat, lon)
    if ch_sr is None or ch_ss is None:
        return None
    chingam_1 = civil_month_start(ch_sk, ch_sr, ch_ss, ch_day)
    year = d.year - 824 if d >= chingam_1 else d.year - 825
    en, ml = KOLLAVARSHAM_MONTHS[best[1]]
    return {
        "year": year,
        "month_index": best[1] + 1,
        "month_en": en,
        "month_ml": ml,
        "day": best[2],
        "rule": KOLLAVARSHAM_RULE,
    }


def _segment(names: dict, start_jd: float, end_jd: float, zone, note: str | None = None) -> dict:
    out = dict(names)
    out["starts_local"] = _iso(start_jd, zone)
    out["ends_local"] = _iso(end_jd, zone)
    if note:
        out["note"] = note
    return out


def _limb_segments(kind: str, jd0: float, jd1: float, zone) -> list[dict]:
    jd = jd0 + 1e-6
    rows = []
    for _ in range(8):
        if jd >= jd1:
            break
        raw = C.panchanga_elements(jd, "apparent")[kind]
        end = raw["end_jd"]
        if end <= jd:
            break
        rows.append(_segment(_limb_names(kind, raw), raw["start_jd"], end, zone))
        if end >= jd1 - 1e-6:
            break
        jd = end + 1e-6
    return rows


def _limb_names(kind: str, raw: dict) -> dict:
    if kind == "tithi":
        rec = tithi_record(raw["number"])
        return {"name_en": rec["name_en"], "name_iast": rec["name_iast"], "name_ml": rec["name_ml"],
                "paksha_en": rec["paksha_en"], "paksha_iast": rec["paksha_iast"],
                "paksha_ml": rec["paksha_ml"]}
    if kind == "yoga":
        rec = yoga_record(raw["number"])
        return {"name_en": rec["name_en"], "name_iast": rec["name_iast"], "name_ml": rec["name_ml"]}
    if kind == "karana":
        rec = karana_record(raw["number"])
        return {"name_en": rec["name_en"], "name_iast": rec["name_iast"], "name_ml": rec["name_ml"]}
    i = raw["index"] - 1
    return {"name_en": NAKSHATRAS[i], "name_iast": NAKSHATRAS_IAST[i], "name_ml": NAKSHATRAS_ML[i],
            "name_ml_latin": NAKSHATRAS_ML_LATIN[i], "lord": VIMSHOTTARI_ORDER[i % 9]}


def _vara_segments(d: date, jd0: float, jd1: float, sr: float | None, lat: float, lon: float,
                   zone) -> list[dict]:
    sun0 = weekday_sun0(d)
    if sr is None or sr < jd0 or sr >= jd1:
        rec = vara_record(sun0)
        return [_segment(
            {"name_en": rec["name_en"], "name_iast": rec["name_iast"], "name_ml": rec["name_ml"]},
            jd0, jd1, zone, "no sunrise on this civil day: civil weekday shown for the whole date")]
    try:
        # rise_trans returns the rise at jd_start when that instant is itself a
        # sunrise, so step past today's sunrise to reach the next one.
        nsr = E.next_sunrise(sr + 1.0 / 1440.0, lat, lon, TIMINGS_SUNRISE_CONVENTION)
    except ValueError:
        nsr = None
    rows = []
    if sr > jd0 + 1.0 / 1440.0:
        prev = vara_record((sun0 - 1) % 7)
        rows.append(_segment(
            {"name_en": prev["name_en"], "name_iast": prev["name_iast"], "name_ml": prev["name_ml"]},
            jd0, sr, zone))
    today = vara_record(sun0)
    rows.append(_segment(
        {"name_en": today["name_en"], "name_iast": today["name_iast"], "name_ml": today["name_ml"]},
        sr, nsr if nsr and nsr > sr else jd1, zone))
    return rows


def _kalams(sr: float, ss: float, sun0: int, zone) -> dict:
    out = {}
    for name, table in KALAM_PARTS.items():
        part = table[sun0]
        a, b = kalam_window(sr, ss, part)
        out[name] = {"part": part, "start_local": _iso(a, zone), "end_local": _iso(b, zone)}
    return out


def compute_timings(d: date, lat: float, lon: float, tz: str | None = None) -> dict:
    """Timings for the local civil date `d` at this place.

    Panchanga limbs are every span that overlaps local midnight to the next
    local midnight, in order, each with its real end (which may fall on the
    next civil date). Vara changes at sunrise. Kalams use the civil weekday
    of `d` and that day's sunrise-to-sunset, which is the daylight after
    that sunrise.
    """
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("lat must be -90..90 and lon -180..180")
    rt, zone = _resolve_zone(d, lat, lon, tz)
    warnings = list(rt.warnings)
    tz_name = rt.tz_name
    jd0, w0 = _jd_midnight(d, tz_name, lat, lon)
    jd1, w1 = _jd_midnight(d + timedelta(days=1), tz_name, lat, lon)
    warnings.extend(w0)
    warnings.extend(w1)
    # Noon, for the Kollavarsham sign and a stable zone label.
    rt_noon = rt
    jd_noon = E.julday_utc(timeutil.resolve(d, time(12, 0), tz_name, lat, lon).utc)

    with E.LOCK:
        E.set_ayanamsa("lahiri")
        sr, ss = _daylight(jd0, lat, lon)
        limbs = {kind: _limb_segments(kind, jd0, jd1, zone)
                 for kind in ("tithi", "nakshatra", "yoga", "karana")}
        vara = _vara_segments(d, jd0, jd1, sr, lat, lon, zone)
        kollam = None
        if sr is not None and ss is not None:
            try:
                kollam = _kollavarsham(d, lat, lon, tz_name, zone, jd_noon)
            except (ValueError, ZeroDivisionError):
                kollam = None
        if kollam is None and sr is not None:
            warnings.append("Kollavarsham could not be computed for this place and date")
        kalams = _kalams(sr, ss, weekday_sun0(d), zone) if sr is not None and ss is not None else None
    if kalams is None:
        warnings.append(NO_DAYLIGHT + "; Rahu Kalam, Gulika Kalam and Yamagandam are omitted")
    deduped = []
    for w in warnings:
        if w not in deduped:
            deduped.append(w)
    warnings = deduped

    return {
        "date": d.isoformat(),
        "place": {
            "lat": lat,
            "lon": lon,
            "tz_name": tz_name,
            "tz_abbrev": rt_noon.tz_abbrev,
            "utc_offset": timeutil.fmt_offset(rt_noon.utc_offset_seconds),
            "timezone_unverified": rt_noon.timezone_unverified,
        },
        "sunrise_convention": TIMINGS_SUNRISE_CONVENTION,
        "sunrise_local": _iso(sr, zone),
        "sunset_local": _iso(ss, zone),
        "kalams": kalams,
        "panchanga": {
            "vara": vara,
            "tithi": limbs["tithi"],
            "nakshatra": limbs["nakshatra"],
            "yoga": limbs["yoga"],
            "karana": limbs["karana"],
        },
        "kollavarsham": kollam,
        "warnings": warnings,
        "meta": {"engine_version": __version__, "ayanamsa": "lahiri"},
    }
