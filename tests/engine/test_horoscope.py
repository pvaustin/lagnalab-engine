"""Free horoscope facts. POST /chart stays byte-identical.

Synthetic chart (not a real person): 1 Jan 2000, 10:30 IST, Kochi
(9.9312 N, 76.2673 E), Lahiri, mean node. Rule behaviour on specific placements is
covered by the hand-built charts in golden/horoscope_parity.json.
"""
import json
from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from lagnalab_engine.api import app
from lagnalab_engine.chart import compute_chart
from lagnalab_engine.horoscope import HOROSCOPE_VERSION, build_horoscope, load_rules
from lagnalab_engine.schema import ChartRequest

KOCHI = {"name": "Kochi", "lat": 9.9312, "lon": 76.2673}
WHEN = dict(date=date(2000, 1, 1), time=time(10, 30), tz="Asia/Kolkata")
client = TestClient(app)


def chart():
    return compute_chart(ChartRequest(place=KOCHI, **WHEN))


def facts():
    return build_horoscope(chart())


def test_yogakaraka_for_the_six_lagnas():
    rules = load_rules()
    # The derivation uses sign lords, not a private table. These are the six
    # lagnas where one planet rules both a kendra (4/7/10) and a trikona (5/9).
    expect = {2: "Saturn", 4: "Mars", 5: "Mars", 7: "Saturn", 10: "Venus", 11: "Venus"}
    from lagnalab_engine.horoscope import _yogakaraka
    for sign_index, planet in expect.items():
        norm = {"lagna": {"sign_index": sign_index}, "grahas": []}
        assert _yogakaraka(norm, rules)["planet"] == planet
    for sign_index in (1, 3, 6, 8, 9, 12):
        norm = {"lagna": {"sign_index": sign_index}, "grahas": []}
        assert _yogakaraka(norm, rules) is None


def test_chart_endpoint_has_no_horoscope_key_and_horoscope_endpoint_is_versioned():
    body = {"date": "2000-01-01", "time": "10:30:00", "place": KOCHI, "tz": "Asia/Kolkata"}
    chart_body = client.post("/chart", json=body).json()
    assert "horoscope" not in chart_body
    assert "vargottama" not in chart_body
    assert chart_body["lagna"]["sign"] == "Kumbha"
    assert chart_body["meta"]["engine_version"] == "0.1.1"
    h = client.post("/horoscope", json=body)
    assert h.status_code == 200, h.text
    payload = h.json()
    assert payload["horoscope_version"] == "1"
    assert payload["node"] == "mean"
    assert {row["body"] for row in payload["vargottama"] if row["vargottama"]} == {"Jupiter", "Lagna"}


def _project(h):
    return {
        "vargottama": [r["body"] for r in h["vargottama"] if r["vargottama"]],
        "yogakaraka": None if not h["yogakaraka"] else h["yogakaraka"]["planet"],
        "yogas": [{"id": y["id"], "applies": y["applies"], "cancelled": y["cancelled"],
                   "reasons": [r["code"] for r in y["reasons"]]} for y in h["yogas"]],
        "kuja": [{"from": r["from"], "house": r["house"], "status": r["status"],
                  "exceptions": [e["id"] for e in r["exceptions"]]}
                 for r in h["doshas"]["kuja"]["references"]],
        "kala_sarpa": h["doshas"]["kala_sarpa"]["present"],
        "papasamyam": h["doshas"]["papasamyam"]["total"],
        "chandrashtama": h["chandrashtama"]["nakshatra_index"],
    }


def test_parity_golden_matches_the_engine():
    from pathlib import Path
    data = json.loads((Path(__file__).resolve().parent / "golden" / "horoscope_parity.json").read_text())
    assert set(data["charts"]) == {
        "cancer", "libra", "capricorn", "aries_kemadruma", "leo_kala_sarpa"}
    for cid, chart in data["charts"].items():
        assert _project(build_horoscope(chart)) == data["expected"][cid], cid
    kem = next(y for y in data["expected"]["aries_kemadruma"]["yogas"] if y["id"] == "kemadruma")
    assert kem["applies"] is True and kem["cancelled"] is False
    assert data["expected"]["leo_kala_sarpa"]["kala_sarpa"] is True
    assert data["expected"]["cancer"]["yogakaraka"] == "Mars"
    assert data["expected"]["libra"]["yogakaraka"] == "Saturn"
    assert data["expected"]["capricorn"]["yogakaraka"] == "Venus"


def test_rules_file_names_the_open_kuja_review():
    rules = load_rules()
    assert rules["kuja"]["apply_listed_exceptions"] is False
    assert rules["kuja"]["houses"] == [2, 4, 7, 8, 12]
    assert rules["kuja"]["references"] == ["lagna", "Moon", "Venus"]
    assert "K01" in rules["_doc"]["kuja_review"]
    assert rules["kuja"]["not_applied_on_one_chart"]
