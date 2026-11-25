import pytest

from golden_compare import compare_all


@pytest.fixture(scope="module")
def tallies():
    return compare_all()


def test_golden_count(tallies):
    t, _ = tallies
    assert t.n["tithi"] >= 50


@pytest.mark.parametrize("field", [
    "graha_longitude", "graha_sign", "lagna_longitude", "lagna_sign", "lagna_nakshatra_pada",
    "moon_nakshatra", "moon_pada", "tithi", "yoga_at_birth", "karana_at_birth", "vara",
    "sunrise_seconds(<=60s)", "retrograde_set", "varga_D2", "varga_D3", "varga_D7", "varga_D9",
    "varga_D10", "varga_D12", "varga_D30", "gulika_start_day_birth", "dasha_sequence",
    "dasha_start_dates(<=1d)", "birth_dasha_lord"])
def test_field_matches_pyjhora(tallies, field):
    t, _ = tallies
    assert t.n[field] > 0
    assert not t.fail[field], t.fail[field][:10]
