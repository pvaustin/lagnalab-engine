"""Independent checks against published panchanga pages (prokerala.com, drikpanchang.com).

Published times are printed to the minute. prokerala appears to truncate (our times fall 0-1 min
after theirs for tithi/karana, which do not depend on the ayanamsa). Nakshatra and yoga also
depend on the site's ayanamsa, so their window is wider. Tolerances:
  tithi/karana start and end: -0.2 .. +1.2 min;  nakshatra/yoga: |d| <= 2 min;
  sunrise/sunset/Gulika-kalam start with the convention the site uses: |d| <= 1.5 min.
"""
import pytest

from published_compare import compare_drikpanchang, compare_prokerala

PK = compare_prokerala()
DP = compare_drikpanchang()


def test_prokerala_coverage():
    ok_pages = {r["page"] for r in PK if r["kind"] == "tithi"}
    assert len(ok_pages) >= 10


@pytest.mark.parametrize("row", [r for r in PK if r["kind"] in ("tithi", "nakshatra", "karana", "yoga")],
                         ids=lambda r: f"{r['page']}-{r['kind']}-{r['theirs']}")
def test_prokerala_element(row):
    assert row["name_ok"], row
    lo, hi = (-0.2, 1.2) if row["kind"] in ("tithi", "karana") else (-2.0, 2.0)
    assert lo <= row["d_start_min"] <= hi, row
    assert lo <= row["d_end_min"] <= hi, row


@pytest.mark.parametrize("row", [r for r in PK if "[hindu]" in r["kind"]], ids=lambda r: f"{r['page']}-{r['kind']}")
def test_prokerala_sunrise_hindu_convention(row):
    # prokerala's sunrise matches the Hindu (disc-centre, no refraction) convention
    assert abs(row["d_min"]) <= 1.5, row


def test_drikpanchang_page():
    rows = {r["kind"]: r for r in DP}
    assert rows["tz_offset"]["ok"], rows["tz_offset"]
    for k in ("tithi", "nakshatra", "yoga", "karana"):
        r = rows[f"{k}_end_min"]
        assert r["name_ok"] and abs(r["d"]) <= 1.5, r
    # drikpanchang's sunrise matches the civil (upper limb + refraction) convention
    assert abs(rows["sunrise_min[apparent_upper_limb]"]["d"]) <= 1.5
    assert abs(rows["sunset_min[apparent_upper_limb]"]["d"]) <= 1.5
    assert abs(rows["gulika_kalam_start_min[apparent_upper_limb]"]["d"]) <= 1.5
    # their printed Lahiri ayanamsha is ~16" larger than Swiss SIDM_LAHIRI; keep the gap visible
    assert abs(rows["ayanamsa_arcsec"]["d"]) < 30, rows["ayanamsa_arcsec"]
