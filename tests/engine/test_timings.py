"""Kalam tables, panchanga transitions, and checks against fetched Drik pages.

The clock times in tests/engine/golden/timings/*.json were fetched from
drikpanchang.com day-panchang (see each file's url and fetched_at_utc).
They are minute-resolution displays, not values invented for this test.
The engine is compared after rounding each instant to the nearest minute.
A difference of one displayed minute is the rounding boundary (recorded in
the PR); anything larger fails.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lagnalab_engine.api import app
from lagnalab_engine.ephemeris import RISE_CONVENTIONS, TIMINGS_SUNRISE_CONVENTION
from lagnalab_engine.timings import (APARAHNA_FRACTION, GULIKA_PART, KALAM_PARTS, RAHU_PART,
                                     YAMAGANDAM_PART, civil_month_start, compute_timings,
                                     kalam_window, weekday_sun0)

# GeoNames points the site autocomplete returns (places-core.json / places/au.json).
# Not observatory coordinates, and not a source of clock times.
PLACES = {
    "kochi": (9.94, 76.26, "Asia/Kolkata"),
    "tvm": (8.486, 76.949, "Asia/Kolkata"),
    "kozhikode": (11.248, 75.78, "Asia/Kolkata"),
    "chennai": (13.088, 80.278, "Asia/Kolkata"),
    "austin": (30.267, -97.743, "America/Chicago"),
}
GOLDEN = Path(__file__).parent / "golden" / "timings"
# A few dates spread over weekday and season. Expected clock times are not
# written here; the structural checks and the fetched Drik files carry that.
PROBE_DATES = (date(2026, 11, 14), date(2026, 8, 17), date(2024, 4, 14), date(1990, 5, 14))


def test_sunrise_convention_is_one_constant():
    assert TIMINGS_SUNRISE_CONVENTION == "apparent_upper_limb"
    assert RISE_CONVENTIONS[TIMINGS_SUNRISE_CONVENTION] == 0
    assert set(KALAM_PARTS) == {"rahu", "yamagandam", "gulika"}


def test_kalam_tables_match_the_product_parts():
    # Sunday .. Saturday, 1-indexed eighths of the daytime.
    assert RAHU_PART == (8, 2, 7, 5, 6, 4, 3)
    assert YAMAGANDAM_PART == (5, 4, 3, 2, 1, 7, 6)
    assert GULIKA_PART == (7, 6, 5, 4, 3, 2, 1)
    for sun0 in range(7):
        parts = {table[sun0] for table in KALAM_PARTS.values()}
        assert len(parts) == 3  # the three periods never share an eighth
        assert all(1 <= p <= 8 for p in parts)


def test_kalam_window_is_one_equal_eighth():
    sr, ss = 2_450_000.0, 2_450_000.5  # a 12-hour day, no ephemeris
    step = 0.5 / 8
    for part in range(1, 9):
        a, b = kalam_window(sr, ss, part)
        assert a == pytest.approx(sr + (part - 1) * step)
        assert b == pytest.approx(sr + part * step)
        assert b - a == pytest.approx(step)
    assert kalam_window(sr, ss, 1)[0] == sr
    assert kalam_window(sr, ss, 8)[1] == ss
    with pytest.raises(ValueError):
        kalam_window(sr, ss, 0)
    with pytest.raises(ValueError):
        kalam_window(ss, sr, 1)


def test_aparahna_rule_flips_at_three_fifths():
    sr, ss = 100.0, 110.0
    day = date(2026, 8, 17)
    aparahna = sr + APARAHNA_FRACTION * (ss - sr)
    assert APARAHNA_FRACTION == pytest.approx(0.6)
    assert civil_month_start(aparahna, sr, ss, day) == day
    assert civil_month_start(aparahna + 1e-6, sr, ss, day) == date(2026, 8, 18)


def test_weekday_index_is_sunday_zero():
    assert weekday_sun0(date(2026, 11, 14)) == 6  # Saturday
    assert weekday_sun0(date(2024, 4, 14)) == 0  # Sunday


def _parse(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def test_panchanga_transitions_meet_and_change_name():
    r = compute_timings(date(2026, 10, 20), *PLACES["kochi"])
    for kind, segs in r["panchanga"].items():
        assert segs, kind
        for a, b in zip(segs, segs[1:]):
            assert a["ends_local"] == b["starts_local"], kind
            assert a["name_en"] != b["name_en"], kind
            end = _parse(a["ends_local"])
            # The instant just before the shared boundary still has the first name.
            # Checked by the ISO boundary itself: the next segment starts at that instant.
            assert _parse(b["starts_local"]) == end
        for seg in segs:
            assert _parse(seg["ends_local"]) > _parse(seg["starts_local"])
    # A civil day that contains a tithi change lists the following tithi too.
    assert len(r["panchanga"]["tithi"]) >= 2
    assert len(r["panchanga"]["karana"]) >= 2
    # Vara changes at sunrise, so the daytime vara is the civil weekday.
    noon = "2026-10-20T12:00:00"
    vara = [s for s in r["panchanga"]["vara"] if s["starts_local"] <= noon < s["ends_local"]]
    assert [s["name_en"] for s in vara] == ["Tuesday"]


@pytest.mark.parametrize("name", list(PLACES))
@pytest.mark.parametrize("d", PROBE_DATES)
def test_place_date_invariants(name, d):
    lat, lon, tz = PLACES[name]
    r = compute_timings(d, lat, lon, tz)
    assert r["date"] == d.isoformat()
    assert r["place"]["tz_name"] == tz
    assert r["sunrise_convention"] == TIMINGS_SUNRISE_CONVENTION
    assert r["sunrise_local"] and r["sunset_local"] and r["kalams"]
    sr, ss = _parse(r["sunrise_local"]), _parse(r["sunset_local"])
    assert sr < ss
    assert sr.date() == d
    span = (ss - sr).total_seconds()
    sun0 = weekday_sun0(d)
    for key, table in KALAM_PARTS.items():
        row = r["kalams"][key]
        assert row["part"] == table[sun0]
        a, b = _parse(row["start_local"]), _parse(row["end_local"])
        assert sr <= a < b <= ss
        # ISO output is whole seconds, so an eighth can differ by about a second.
        assert (b - a).total_seconds() == pytest.approx(span / 8, abs=1.5)
        if row["part"] == 1:
            assert a == sr
        if row["part"] == 8:
            assert b == ss
    assert r["kollavarsham"]["day"] >= 1
    assert r["kollavarsham"]["month_en"]
    noon = d.isoformat() + "T12:00:00"
    covering = [s for s in r["panchanga"]["vara"] if s["starts_local"] <= noon < s["ends_local"]]
    assert covering and covering[0]["name_en"] == (
        "Sunday Monday Tuesday Wednesday Thursday Friday Saturday".split()[sun0]
    )


def test_kollavarsham_chingam_at_thiruvananthapuram():
    """17 Aug 2026 and 17 Aug 2023 are Chingam 1 at Thiruvananthapuram.

    Those two dates are the ones stated for Thiruvananthapuram by
    https://mysmartcopilot.com/tools/malayalam-calendar/ (Kollam 1202 and
    1199), which attributes them to the Rashtriya Panchang. A direct fetch of
    that page returned HTTP 403, so the agreement is with that published
    statement, not with a stored copy of the page. The rule itself is the
    Malayali aparahna rule in timings.KOLLAVARSHAM_RULE.
    """
    lat, lon, tz = PLACES["tvm"]
    a = compute_timings(date(2026, 8, 17), lat, lon, tz)["kollavarsham"]
    b = compute_timings(date(2023, 8, 17), lat, lon, tz)["kollavarsham"]
    assert (a["year"], a["month_en"], a["day"]) == (1202, "Chingam", 1)
    assert (b["year"], b["month_en"], b["day"]) == (1199, "Chingam", 1)


def test_polar_day_and_night_omit_kalams():
    for d in (date(2000, 12, 21), date(2000, 6, 21)):
        r = compute_timings(d, 69.65, 18.96, "Europe/Oslo")
        assert r["sunrise_local"] is None and r["sunset_local"] is None
        assert r["kalams"] is None and r["kollavarsham"] is None
        assert any("does not rise" in w for w in r["warnings"])
        assert r["panchanga"]["tithi"]  # panchanga does not need a sunrise
        assert r["panchanga"]["vara"][0]["note"]


def _nearest_minute(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    if dt.second >= 30:
        dt += timedelta(minutes=1)
    return dt.strftime("%H:%M")


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def test_fetched_drik_pages_agree_within_a_minute():
    files = sorted(GOLDEN.glob("*.json"))
    assert len(files) >= 5
    for path in files:
        rec = json.loads(path.read_text())
        assert rec.get("url", "").startswith("https://www.drikpanchang.com/")
        assert "error" not in rec, rec
        prefix = rec["id"].rsplit("-", 3)[0]
        dd, mm, yy = rec["date"].split("/")
        r = compute_timings(date(int(yy), int(mm), int(dd)), *PLACES[prefix])
        sh, sm = rec["sunset_hhmm_12h"].split(":")
        expected = {
            "sunrise": rec["sunrise_hhmm"],
            "sunset": f"{int(sh) % 12 + 12:02d}:{sm}",
            "rahu": rec["rahu_kalam"],
            "yamagandam": rec["yamaganda"],
            "gulika": rec["gulikai_kalam"],
        }
        got = {
            "sunrise": _nearest_minute(r["sunrise_local"]),
            "sunset": _nearest_minute(r["sunset_local"]),
            "rahu": [_nearest_minute(r["kalams"]["rahu"]["start_local"]),
                     _nearest_minute(r["kalams"]["rahu"]["end_local"])],
            "yamagandam": [_nearest_minute(r["kalams"]["yamagandam"]["start_local"]),
                           _nearest_minute(r["kalams"]["yamagandam"]["end_local"])],
            "gulika": [_nearest_minute(r["kalams"]["gulika"]["start_local"]),
                       _nearest_minute(r["kalams"]["gulika"]["end_local"])],
        }
        for key, exp in expected.items():
            have = got[key]
            pairs = zip(have, exp) if isinstance(exp, list) else [(have, exp)]
            for a, b in pairs:
                assert abs(_minutes(a) - _minutes(b)) <= 1, (rec["id"], key, a, b, rec["url"])


def test_timings_endpoint_is_get_and_validates():
    client = TestClient(app)
    ok = client.get("/timings", params={"date": "2026-11-14", "lat": 9.94, "lon": 76.26, "tz": "Asia/Kolkata"})
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["kalams"]["rahu"]["part"] == 3
    assert body["sunrise_convention"] == "apparent_upper_limb"
    assert client.get("/timings", params={"date": "2026-11-14", "lat": 99, "lon": 0}).status_code == 422
    assert client.get("/timings", params={"date": "nope", "lat": 9, "lon": 76}).status_code == 422
    bad = client.get("/timings", params={"date": "2026-11-14", "lat": 9.94, "lon": 76.26, "tz": "Mars/Olympus"})
    assert bad.status_code == 422
