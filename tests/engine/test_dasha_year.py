"""Vimshottari year modes.

solar_365_25 is the default (365.25-day year) and must keep the synthetic Kochi chart JSON
byte-identical to the committed snapshot (golden/synthetic_default.json). savana_360 is the
Kerala traditional year, 12 months × 30 days. Same-lord apahāra lengths at 360
days are the Kanippayyur-style table values: Rahu–Rahu 2y 8m 12d (972 d),
Saturn–Saturn 3y 0m 3d, Venus–Venus 3y 4m 0d, Sun–Sun 3m 18d (108 d),
Moon–Moon 10m (300 d).
"""
from __future__ import annotations

import json
from datetime import date, datetime, time, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lagnalab_engine.api import app
from lagnalab_engine.chart import compute_chart
from lagnalab_engine.constants import NAK_SPAN, VIMSHOTTARI_YEARS
from lagnalab_engine.core import proportional_years, vimshottari, years_to_ymd_parts
from lagnalab_engine.schema import ChartRequest

KOCHI = {"name": "Kochi", "lat": 9.9312, "lon": 76.2673}
# Synthetic birth (not a real person): 1 Jan 2000, 10:00 IST, Kochi.
WHEN = dict(date=date(2000, 1, 1), time=time(10, 0), tz="Asia/Kolkata",
            transit_at=datetime(2026, 10, 20, tzinfo=timezone.utc))
GOLDEN = Path(__file__).resolve().parent / "golden" / "synthetic_default.json"

# Same-lord apahāra at a 360-day year. The day count is mahadasha years² × 3.
SAVANA_APAHARA = {
    "Rahu": ((2, 8, 12), 972),
    "Saturn": ((3, 0, 3), 1083),
    "Venus": ((3, 4, 0), 1200),
    "Sun": ((0, 3, 18), 108),
    "Moon": ((0, 10, 0), 300),
}


def chart(**settings):
    return compute_chart(ChartRequest(place=KOCHI, settings=settings or {}, **WHEN))


def _same_lord(c, lord):
    md = next(m for m in c.vimshottari.mahadashas if m.lord == lord)
    bh = md.bhuktis[0]
    assert bh.lord == lord
    return bh


def test_default_kochi_json_is_byte_identical():
    raw = chart().model_dump_json()
    assert raw == GOLDEN.read_text(encoding="utf-8")
    explicit = chart(dasha_year="solar_365_25").model_dump_json()
    assert explicit == raw
    body = json.loads(raw)
    assert "dasha_year" not in body["meta"]["settings"]
    assert body["meta"]["settings"]["dasha_year_days"] == 365.25
    assert body["vimshottari"]["year_days"] == 365.25
    assert "365.25" in body["vimshottari"]["year_length_convention"]
    assert "savana_360" not in body["vimshottari"]["year_length_convention"]


def test_savana_echoes_the_mode_and_the_table_lengths():
    c = chart(dasha_year="savana_360")
    settings = c.model_dump()["meta"]["settings"]
    assert settings["dasha_year"] == "savana_360"
    assert settings["dasha_year_days"] == 360
    assert c.vimshottari.year_days == 360
    assert "savana_360" in c.vimshottari.year_length_convention
    assert "solar_365_25" in c.vimshottari.year_length_convention
    for lord, (ymd, days) in SAVANA_APAHARA.items():
        bh = _same_lord(c, lord)
        assert years_to_ymd_parts(bh.years) == ymd
        assert (bh.end_utc - bh.start_utc).total_seconds() == days * 86400
        assert proportional_years(VIMSHOTTARI_YEARS[lord], VIMSHOTTARI_YEARS[lord]) == pytest.approx(bh.years)


def test_default_same_lord_span_stays_on_365_25():
    c = chart()
    bh = _same_lord(c, "Rahu")
    span = (bh.end_utc - bh.start_utc).total_seconds() / 86400
    assert span == pytest.approx(2.7 * 365.25)
    assert span != 972


def test_named_mode_wins_over_the_float_and_the_float_alone_still_works():
    forced = chart(dasha_year="solar_365_25", dasha_year_days=360)
    assert forced.vimshottari.year_days == 365.25
    assert forced.model_dump_json() == chart().model_dump_json()

    legacy = chart(dasha_year_days=360)
    named = chart(dasha_year="savana_360")
    assert legacy.vimshottari.year_days == 360
    assert "dasha_year" not in legacy.model_dump()["meta"]["settings"]
    assert legacy.vimshottari.year_length_convention.startswith(
        "A Vimshottari year is 360 days (a request override; the project default is 365.25")
    pairs = zip(legacy.vimshottari.mahadashas, named.vimshottari.mahadashas)
    for old, new in pairs:
        assert (old.start_utc, old.end_utc) == (new.start_utc, new.end_utc)
        for a, b in zip(old.bhuktis, new.bhuktis):
            assert (a.start_utc, a.end_utc, a.years) == (b.start_utc, b.end_utc, b.years)


def test_birth_balance_converts_in_12x30_units():
    # 2.7 years is the Rahu–Rahu proportion: 2×360 + 8×30 + 12 = 972.
    assert years_to_ymd_parts(18 * 18 / 120) == (2, 8, 12)
    assert 2 * 360 + 8 * 30 + 12 == 972
    # A quarter of Ardra (Rahu) is already elapsed, so three quarters of 18 years remain.
    moon = 5 * NAK_SPAN + 0.25 * NAK_SPAN
    v = vimshottari(moon, 2451545.0, 360.0)
    assert years_to_ymd_parts(v["balance"]) == (13, 6, 0)
    assert 13 * 360 + 6 * 30 + 0 == 4860
    assert v["balance"] * 360 == pytest.approx(4860)
    # Birth to the end of that opening daśā is the balance, in 360-day calendar days.
    assert v["mahadashas"][0][2] - 2451545.0 == pytest.approx(v["balance"] * 360)

    for mode in (None, "solar_365_25", "savana_360"):
        c = chart(**({} if mode is None else {"dasha_year": mode}))
        bal = c.vimshottari.balance_at_birth
        assert (bal.years, bal.months, bal.days) == (5, 9, 16)
        printed = bal.years * 360 + bal.months * 30 + bal.days
        raw_days = c.vimshottari.balance_at_birth_years * 360
        assert printed <= raw_days < printed + 1
        span = (c.vimshottari.mahadashas[0].end_utc - c.time.utc).total_seconds() / 86400
        assert span == pytest.approx(c.vimshottari.balance_at_birth_years * c.vimshottari.year_days)
    solar_span = (chart().vimshottari.mahadashas[0].end_utc - chart().time.utc).total_seconds()
    savana_span = (chart(dasha_year="savana_360").vimshottari.mahadashas[0].end_utc
                   - chart(dasha_year="savana_360").time.utc).total_seconds()
    assert savana_span < solar_span


def test_chidra_uses_the_same_amsa_proportion():
    # Not emitted on the chart. Rahu–Rahu–Rahu = 18³ / 120² years = 145.8 days at 360.
    # The 12×30 print truncates 145.8 toward zero, the same rule as the birth balance.
    y = proportional_years(18, 18, 18)
    assert y * 360 == pytest.approx(145.8)
    assert years_to_ymd_parts(y) == (0, 4, 25)
    assert 4 * 30 + 25 == 145


def test_http_dasha_year():
    body = {"date": "2000-01-01", "time": "10:00:00", "place": KOCHI, "tz": "Asia/Kolkata",
            "transit_at": "2026-10-20T00:00:00Z"}
    client = TestClient(app)
    default = client.post("/chart", json=body)
    assert default.status_code == 200, default.text
    assert "dasha_year" not in default.json()["meta"]["settings"]
    assert default.json()["vimshottari"]["year_days"] == 365.25

    savana = client.post("/chart", json=dict(body, settings={"dasha_year": "savana_360"}))
    assert savana.status_code == 200, savana.text
    payload = savana.json()
    assert payload["meta"]["settings"]["dasha_year"] == "savana_360"
    assert payload["meta"]["settings"]["dasha_year_days"] == 360
    assert payload["vimshottari"]["year_days"] == 360
    rahu = next(m for m in payload["vimshottari"]["mahadashas"] if m["lord"] == "Rahu")
    own = rahu["bhuktis"][0]
    assert own["lord"] == "Rahu"
    start = datetime.fromisoformat(own["start_utc"])
    end = datetime.fromisoformat(own["end_utc"])
    assert (end - start).total_seconds() == 972 * 86400

    rejected = client.post("/chart", json=dict(body, settings={"dasha_year": "sidereal_365_2564"}))
    assert rejected.status_code == 422


def _pair(c, lord):
    return next(m for m in c.vimshottari.year_compare.mahadashas if m.lord == lord)


def test_compare_is_opt_in_and_default_stays_byte_identical():
    golden = GOLDEN.read_text(encoding="utf-8")
    assert chart().model_dump_json() == golden
    assert chart(compare_dasha_years=False).model_dump_json() == golden
    assert chart(dasha_year="solar_365_25", compare_dasha_years=False).model_dump_json() == golden
    body = json.loads(golden)
    assert "compare_dasha_years" not in body["meta"]["settings"]
    assert "year_compare" not in body["vimshottari"]

    savana = chart(dasha_year="savana_360")
    dumped = savana.model_dump()
    assert "compare_dasha_years" not in dumped["meta"]["settings"]
    assert "year_compare" not in dumped["vimshottari"]


def test_compare_kochi_rahu_rahu_and_shukra_lengths():
    # Synthetic chart, Kochi 2000-01-01 10:00 IST. Spans are the period's own length.
    # Rahu–Rahu is 18×18/120 years: 972 days at 360, 986.175 at 365.25.
    # A full Śukra mahādaśā is 20 years: 7,200 days at 360, 7,305 at 365.25.
    solar = chart(compare_dasha_years=True)
    assert solar.vimshottari.year_compare.selected == "solar_365_25"
    assert solar.vimshottari.year_days == 365.25
    assert "compare_dasha_years" in solar.model_dump()["meta"]["settings"]
    plain = chart()
    assert [m.end_utc for m in solar.vimshottari.mahadashas] == [
        m.end_utc for m in plain.vimshottari.mahadashas]

    rahu = _pair(solar, "Rahu")
    own = rahu.bhuktis[0]
    assert own.lord == "Rahu"
    assert own.span_days_savana == pytest.approx(972)
    assert own.span_days_solar == pytest.approx(986.175)
    assert own.span_days_savana - own.span_days_solar == pytest.approx(972 - 986.175)
    primary = _same_lord(solar, "Rahu")
    assert primary.end_utc == own.end_utc_solar
    assert (primary.end_utc - primary.start_utc).total_seconds() / 86400 == pytest.approx(986.175)

    shukra = _pair(solar, "Venus")
    assert shukra.span_days_savana == pytest.approx(7200)
    assert shukra.span_days_solar == pytest.approx(7305)
    assert shukra.span_days_solar - shukra.span_days_savana == pytest.approx(105)
    venus = next(m for m in solar.vimshottari.mahadashas if m.lord == "Venus")
    assert venus.end_utc == shukra.end_utc_solar
    assert venus.end_local_date == shukra.end_local_date_solar
    assert (venus.end_utc - venus.start_utc).total_seconds() / 86400 == pytest.approx(7305)
    # The end-date gap is the cumulative shift, not always the period's own 105 days.
    assert shukra.delta_days == pytest.approx(
        (shukra.end_utc_savana - shukra.end_utc_solar).total_seconds() / 86400, abs=1e-4)

    savana = chart(dasha_year="savana_360", compare_dasha_years=True)
    assert savana.vimshottari.year_compare.selected == "savana_360"
    savana_own = _pair(savana, "Rahu").bhuktis[0]
    assert savana_own.span_days_savana == pytest.approx(972)
    assert savana_own.span_days_solar == pytest.approx(986.175)
    rahu_own = _same_lord(savana, "Rahu")
    assert rahu_own.end_utc == savana_own.end_utc_savana
    assert (rahu_own.end_utc - rahu_own.start_utc).total_seconds() == 972 * 86400
    for md, pair in zip(savana.vimshottari.mahadashas, savana.vimshottari.year_compare.mahadashas):
        assert md.end_utc == pair.end_utc_savana
        assert md.end_local_date == pair.end_local_date_savana
        for bh, bp in zip(md.bhuktis, pair.bhuktis):
            assert bh.end_utc == bp.end_utc_savana
            assert bh.lord == bp.lord


def test_compare_custom_length_keeps_both_named_ends():
    custom = chart(dasha_year_days=365.2425, compare_dasha_years=True)
    assert custom.vimshottari.year_days == 365.2425
    assert custom.vimshottari.year_compare.selected == "custom"
    assert "dasha_year" not in custom.model_dump()["meta"]["settings"]
    shukra = _pair(custom, "Venus")
    assert shukra.span_days_solar == pytest.approx(7305)
    assert shukra.span_days_savana == pytest.approx(7200)
    venus = next(m for m in custom.vimshottari.mahadashas if m.lord == "Venus")
    assert venus.end_utc != shukra.end_utc_solar
    assert venus.end_utc != shukra.end_utc_savana


def test_http_compare_flag_is_byte_identical_until_opt_in():
    body = {"date": "2000-01-01", "time": "10:00:00", "place": KOCHI, "tz": "Asia/Kolkata",
            "transit_at": "2026-10-20T00:00:00Z"}
    client = TestClient(app)
    default = client.post("/chart", json=body)
    assert default.status_code == 200, default.text
    off = client.post("/chart", json=dict(body, settings={"compare_dasha_years": False}))
    assert off.status_code == 200, off.text
    assert off.content == default.content
    named = client.post("/chart", json=dict(body, settings={"dasha_year": "solar_365_25"}))
    assert named.content == default.content
    assert b"year_compare" not in default.content
    assert b"compare_dasha_years" not in default.content

    on = client.post("/chart", json=dict(body, settings={"compare_dasha_years": True}))
    assert on.status_code == 200, on.text
    payload = on.json()
    assert payload["meta"]["settings"]["compare_dasha_years"] is True
    assert "dasha_year" not in payload["meta"]["settings"]
    assert payload["vimshottari"]["year_compare"]["selected"] == "solar_365_25"
    assert [m["end_utc"] for m in payload["vimshottari"]["mahadashas"]] == [
        m["end_utc"] for m in default.json()["vimshottari"]["mahadashas"]]
    venus = next(m for m in payload["vimshottari"]["year_compare"]["mahadashas"] if m["lord"] == "Venus")
    assert venus["span_days_solar"] == pytest.approx(7305)
    assert venus["span_days_savana"] == pytest.approx(7200)
    rahu = next(m for m in payload["vimshottari"]["year_compare"]["mahadashas"] if m["lord"] == "Rahu")
    assert rahu["bhuktis"][0]["lord"] == "Rahu"
    assert rahu["bhuktis"][0]["span_days_savana"] == pytest.approx(972)
    assert rahu["bhuktis"][0]["span_days_solar"] == pytest.approx(986.175)
    assert "bhuktis" not in rahu["bhuktis"][0]
