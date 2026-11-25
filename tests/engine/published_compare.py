"""Compare engine panchanga timings with published pages (prokerala.com, drikpanchang.com)."""
from __future__ import annotations

import glob
import json
import os
from datetime import date, datetime, time, timedelta, timezone

import swisseph as swe

from lagnalab_engine import core as C, ephemeris as E, timeutil
from lagnalab_engine.constants import NAKSHATRAS, TITHIS, YOGAS, karana_name

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")
ALIAS = {"Moola": "Mula", "Dhanishta": "Dhanishtha", "Jyeshta": "Jyeshtha", "Vishaka": "Vishakha",
         "Garija": "Gara", "Siva": "Shiva", "Sobhana": "Shobhana", "Soola": "Shula",
         "Vaidhruthi": "Vaidhriti", "Variyan": "Variyana", "Vridhi": "Vriddhi", "Sukla": "Shukla"}


def norm(name: str) -> str:
    return " ".join(ALIAS.get(w, w) for w in name.split())


def local_to_jd(s: str, tz: str) -> float:
    d = datetime.fromisoformat(s)
    rt = timeutil.resolve(d.date(), d.time(), tz)
    return E.julday_utc(rt.utc)


def jd_to_local(jd: float, tz: str) -> datetime:
    import zoneinfo
    y, m, d, h = swe.revjul(jd)
    return (datetime(y, m, d, tzinfo=timezone.utc) + timedelta(hours=h)).astimezone(zoneinfo.ZoneInfo(tz))


def our_name(kind, el):
    if kind == "tithi":
        return f"{el['paksha']} Paksha {el['name']}"
    if kind == "nakshatra":
        return NAKSHATRAS[el["index"] - 1]
    return el["name"]


def compare_prokerala():
    rows = []
    for f in sorted(glob.glob(os.path.join(GOLDEN, "prokerala", "*.json"))):
        rec = json.load(open(f))
        if "error" in rec:
            rows.append(dict(page=rec["id"], kind="unreachable", detail=rec["error"]))
            continue
        tz = rec["tz"]
        lat, lon = rec["coordinates_used"]["lat"], rec["coordinates_used"]["lon"]
        v = rec["values"]
        with E.LOCK:
            E.set_ayanamsa("lahiri")
            for kind in ("tithi", "nakshatra", "karana", "yoga"):
                for e in v[kind]:
                    a, b = local_to_jd(e["start_local"], tz), local_to_jd(e["end_local"], tz)
                    el = C.panchanga_elements((a + b) / 2)[kind]
                    rows.append(dict(page=rec["id"], kind=kind, theirs=norm(e["name"]), ours=our_name(kind, el),
                                     name_ok=norm(e["name"]) == our_name(kind, el),
                                     d_start_min=(el["start_jd"] - a) * 1440, d_end_min=(el["end_jd"] - b) * 1440))
            d0 = date.fromisoformat(rec["date"])
            midnight = local_to_jd(f"{rec['date']}T00:00", tz)
            for conv in ("apparent_upper_limb", "hindu"):
                sr = E.next_sunrise(midnight, lat, lon, conv)
                ss = E.next_sunset(sr, lat, lon, conv)
                for key, jd in (("sunrise", sr), ("sunset", ss)):
                    hh, mm = map(int, v[key + "_local"].split(":"))
                    theirs = local_to_jd(f"{rec['date']}T{hh:02d}:{mm:02d}", tz)
                    rows.append(dict(page=rec["id"], kind=f"{key}[{conv}]", d_min=(jd - theirs) * 1440))
                dn = C.DayNight(True, (d0.weekday() + 1) % 7, sr, ss, sr, ss)
                a, _ = C.saturn_segment(dn)
                hh, mm = map(int, v["gulika_kalam_local"][0].split(":"))
                theirs = local_to_jd(f"{rec['date']}T{hh:02d}:{mm:02d}", tz)
                rows.append(dict(page=rec["id"], kind=f"gulika_kalam_start[{conv}]", d_min=(a - theirs) * 1440))
    return rows


def compare_drikpanchang():
    """DP01 is the only drikpanchang page we could fetch (later requests hit a reCAPTCHA)."""
    rows = []
    for f in sorted(glob.glob(os.path.join(GOLDEN, "drikpanchang", "*.json"))):
        rec = json.load(open(f))
        v = rec["values"]
        d0 = datetime.strptime(rec["date"], "%d/%m/%Y").date()
        tz = v["olson_tz"]
        lat, lon = v["lat"], v["lon"]
        rt = timeutil.resolve(d0, time(12), tz)
        rows.append(dict(page=rec["id"], kind="tz_offset", ok=timeutil.fmt_offset(rt.utc_offset_seconds) == v["tz_offset"],
                         detail=f"{timeutil.fmt_offset(rt.utc_offset_seconds)} vs {v['tz_offset']}"))
        with E.LOCK:
            E.set_ayanamsa("lahiri")
            noon = local_to_jd(f"{d0.isoformat()}T12:00", tz)
            pe = C.panchanga_elements(noon)
            rows.append(dict(page=rec["id"], kind="ayanamsa_arcsec", d=(E.ayanamsa_value(noon) - v["lahiri_ayanamsha_deg"]) * 3600))
            for kind in ("tithi", "nakshatra", "yoga", "karana"):
                e = v[kind]
                day = d0 + timedelta(days=1) if e["next_day_label"] else d0
                theirs = local_to_jd(f"{day.isoformat()}T{e['upto_local']}", tz)
                el = pe[kind]
                rows.append(dict(page=rec["id"], kind=f"{kind}_end_min", d=(el["end_jd"] - theirs) * 1440,
                                 name_ok=norm(e["name"]) in our_name(kind, el)))
            midnight = local_to_jd(f"{d0.isoformat()}T00:00", tz)
            for conv in ("apparent_upper_limb", "hindu"):
                sr = E.next_sunrise(midnight, lat, lon, conv)
                ss = E.next_sunset(sr, lat, lon, conv)
                for key, jd in (("sunrise", sr), ("sunset", ss)):
                    theirs = local_to_jd(f"{d0.isoformat()}T{v[key + '_local']}", tz)
                    rows.append(dict(page=rec["id"], kind=f"{key}_min[{conv}]", d=(jd - theirs) * 1440))
                a, _ = C.saturn_segment(C.DayNight(True, (d0.weekday() + 1) % 7, sr, ss, sr, ss))
                theirs = local_to_jd(f"{d0.isoformat()}T{v['gulikai_kalam_local'][0]}", tz)
                rows.append(dict(page=rec["id"], kind=f"gulika_kalam_start_min[{conv}]", d=(a - theirs) * 1440))
    return rows
