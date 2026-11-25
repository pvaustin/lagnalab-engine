"""Unit tests of documented rules. Expected values here follow directly from the rule texts in
docs/METHODS.md (worked by hand), or from the cited tzdata source excerpt."""
import random
from datetime import date, time

import pytest

from lagnalab_engine import core as C, timeutil
from lagnalab_engine.constants import MANDI_GHATIKA_DAY, karana_record, tithi_record, yoga_record
from lagnalab_engine.vargas import d2, d3, d7, d9, d10, d12, d30

EPS = 1e-6


# ---------------------------------------------------------------- vargas
def test_d9_rule_and_continuity():
    assert d9(0) == 0               # Mesha (movable) starts from itself
    assert d9(30 + EPS) == 9        # Vrishabha (fixed) starts from the 9th = Makara
    assert d9(60 + EPS) == 6        # Mithuna (dual) starts from the 5th = Tula
    assert d9(90 + EPS) == 3        # Karka starts from itself
    assert d9(10 / 3 + EPS) == 1
    rnd = random.Random(1)
    for _ in range(5000):
        lon = rnd.uniform(0, 360)
        assert d9(lon) == int(lon // (10 / 3)) % 12


def test_d2_d3_d12():
    assert d2(1) == 4 and d2(16) == 3          # odd sign: Sun's hora then Moon's
    assert d2(31) == 3 and d2(46) == 4         # even sign: Moon's then Sun's
    assert d3(5) == 0 and d3(15) == 4 and d3(25) == 8
    assert d12(30 + 2.5 + EPS) == 2


def test_d7_d10_even_signs():
    assert d7(30 + EPS) == 7         # Vrishabha starts from its 7th, Vrischika
    assert d7(EPS) == 0
    assert d10(30 + EPS) == 9        # Vrishabha starts from its 9th, Makara
    assert d10(EPS) == 0


def test_d30_boundaries_are_half_open():
    assert d30(4.999) == 0 and d30(5.0) == 10 and d30(10.0) == 8 and d30(18.0) == 2 and d30(25.0) == 6
    assert d30(30 + 4.999) == 1 and d30(35.0) == 5 and d30(42.0) == 11 and d30(50.0) == 9 and d30(55.0) == 7


# ---------------------------------------------------------------- time zones
def test_kolkata_history_from_tzdata():
    # docs/sources/tzdb_asia_india_excerpt.txt: MMT +5:21:10 to 1906; +6:30 war time 1942-09..1945-10-15
    r = timeutil.resolve(date(1901, 3, 12), time(5, 40), "Asia/Kolkata")
    assert r.utc_offset_seconds == 5 * 3600 + 21 * 60 + 10 and r.timezone_unverified
    r = timeutil.resolve(date(1943, 7, 17), time(3, 25), "Asia/Kolkata")
    assert r.utc_offset_seconds == 6.5 * 3600 and r.timezone_unverified
    r = timeutil.resolve(date(1960, 1, 1), time(12), "Asia/Kolkata")
    assert r.utc_offset_seconds == 5.5 * 3600 and not r.timezone_unverified


def test_pre1955_flag_by_coordinates_even_with_override():
    r = timeutil.resolve(date(1950, 1, 1), time(12), None, 19.07, 72.88, utc_offset_override_hours=4 + 51 / 60)
    assert r.timezone_unverified and r.offset_source == "override" and r.utc_offset_seconds == 4 * 3600 + 51 * 60


def test_dst_gap_and_ambiguity_warn():
    gap = timeutil.resolve(date(2021, 3, 14), time(2, 30), "America/New_York")
    assert any("does not exist" in w for w in gap.warnings)
    amb0 = timeutil.resolve(date(2021, 11, 7), time(1, 30), "America/New_York", fold=0)
    amb1 = timeutil.resolve(date(2021, 11, 7), time(1, 30), "America/New_York", fold=1)
    assert any("ambiguous" in w for w in amb0.warnings)
    assert amb0.utc_offset_seconds == -4 * 3600 and amb1.utc_offset_seconds == -5 * 3600


def test_lmt():
    r = timeutil.resolve(date(1900, 1, 1), time(12), None, 9.93, 76.26, use_lmt=True)
    assert r.utc_offset_seconds == round(76.26 * 240)


def test_tz_inferred_from_coordinates():
    r = timeutil.resolve(date(2000, 1, 1), time(12), None, -33.87, 151.21)
    assert r.tz_name == "Australia/Sydney"


# ---------------------------------------------------------------- Gulika / Mandi
def _dn(is_day, wd):
    return C.DayNight(is_day, wd, 0.0, 1.0, 0.0, 1.0)


def test_segment_lords_raman_examples():
    # Friday day: Venus then Saturn (Gulika at the end of the 2nd part = 7.5 ghatis of 30)
    assert C.segment_lords(_dn(True, 5))[:2] == ["Venus", "Saturn"]
    assert C.gulika_time(_dn(True, 5), "end") == pytest.approx(7.5 / 30)
    # Night lords start from the lord of the 5th weekday: Sunday night starts with Jupiter
    assert C.segment_lords(_dn(False, 0))[:3] == ["Jupiter", "Venus", "Saturn"]
    assert C.segment_lords(_dn(True, 0))[7] is None


def test_mandi_ghatika_table():
    assert C.mandi_time(_dn(True, 5), "prasna_marga_ghatika") == pytest.approx(6 / 30)  # Friday 6 gh
    assert C.mandi_time(_dn(False, 6), "prasna_marga_ghatika") == pytest.approx(14 / 30)  # Saturday night 14
    assert MANDI_GHATIKA_DAY[0] == 26


# ---------------------------------------------------------------- dasha, dignity, combustion
def test_vimshottari_structure():
    v = C.vimshottari(100.0, 2450000.0, 365.25)
    total = sum(md[3] for md in v["mahadashas"])
    assert total == 120
    for md, a, b, yrs, bh in v["mahadashas"]:
        assert bh[0][1] == pytest.approx(a) and bh[-1][2] == pytest.approx(b)
        assert sum(x[3] for x in bh) == pytest.approx(yrs)
    first = v["mahadashas"][0]
    assert (first[2] - 2450000.0) / 365.25 == pytest.approx(v["balance"])


def test_vimshottari_ymd_truncates_the_day():
    # 16.588 years -> 7.056 months -> 1.69 days. Truncate to 1, do not round to 2.
    assert C.years_to_ymd_parts(16.588054) == (16, 7, 1)
    assert C.years_to_ymd_parts(16 + 7 / 12 + 1.7 / 360) == (16, 7, 1)
    assert C.years_to_ymd_parts(16 + 8 / 12) == (16, 8, 0)  # exact month boundary
    assert C.years_to_ymd_parts(17.0) == (17, 0, 0)
    assert C.years_to_ymd(16.588054) == "16y 7m 1.7d"


def test_panchanga_name_tables():
    # 1..60 half-tithis collapse onto 11 names. 1 and 58..60 are the four fixed karanas.
    assert karana_record(1)["name_en"] == "Kimstughna"
    assert [karana_record(n)["name_en"] for n in range(2, 9)] == [
        "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]
    assert karana_record(9)["name_en"] == "Bava"
    assert karana_record(42)["name_ml"] == "വണിജം"
    assert [karana_record(n)["name_en"] for n in (57, 58, 59, 60)] == [
        "Vishti", "Shakuni", "Chatushpada", "Naga"]
    assert len({karana_record(n)["name_en"] for n in range(1, 61)}) == 11
    shashthi = tithi_record(21)
    assert (shashthi["paksha"], shashthi["name_en"], shashthi["name_iast"], shashthi["name_ml"]) == (
        "krishna", "Shashthi", "Ṣaṣṭhī", "ഷഷ്ഠി")
    assert tithi_record(15)["name_en"] == "Purnima" and tithi_record(15)["paksha"] == "shukla"
    assert tithi_record(30)["name_en"] == "Amavasya" and tithi_record(30)["paksha"] == "krishna"
    assert yoga_record(16) == {"number": 16, "name_en": "Siddhi", "name_iast": "Siddhi", "name_ml": "സിദ്ധി"}
    assert yoga_record(1)["name_en"] == "Vishkambha" and yoga_record(27)["name_en"] == "Vaidhriti"


def test_dignity_and_combustion():
    d = C.dignity("Sun", 0, 10)
    assert d["exalted"] and d["dig_bala"] and d["sign_relation"] == "friend"
    assert C.dignity("Saturn", 0, 1)["debilitated"]
    assert C.dignity("Rahu", 0, 1)["sign_relation"] is None
    assert C.combustion("Venus", 9.0, 0.0, True) == (False, 8.0)
    assert C.combustion("Venus", 9.0, 0.0, False) == (True, 10.0)
    assert C.combustion("Moon", 5.0, 0.0, False, moon_combustion=False) == (None, None)
