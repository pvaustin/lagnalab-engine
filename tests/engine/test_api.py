from fastapi.testclient import TestClient

from lagnalab_engine import chart as chart_mod
from lagnalab_engine import geocode as geo
from lagnalab_engine.api import app

client = TestClient(app)
BODY = {"date": "1990-05-14", "time": "04:30:00", "place": {"name": "Kochi", "lat": 9.9312, "lon": 76.2673},
        "tz": "Asia/Kolkata", "transit_at": "2026-10-20T00:00:00Z"}


def test_chart_endpoint():
    r = client.post("/chart", json=BODY)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["time"]["utc_offset"] == "+05:30"
    assert len(d["grahas"]) == 9 and {u["name"] for u in d["upagrahas"]} == {"Gulika", "Mandi"}
    assert d["panchanga"]["vara"]["weekday"] == "Sunday"     # 04:30 is before sunrise on a Monday
    assert d["panchanga"]["vara"]["civil_weekday"] == "Monday"
    assert set(d["grahas"][0]["vargas"]) == {"D2", "D3", "D7", "D9", "D10", "D12", "D30"}
    assert len(d["vimshottari"]["mahadashas"]) == 9
    moon = next(g for g in d["grahas"] if g["name"] == "Moon")
    assert d["birth_star"]["index"] == moon["nakshatra"]["index"]
    assert d["birth_star"]["pada"] == moon["nakshatra"]["pada"]
    assert d["birth_panchanga"]["nakshatra"] == d["birth_star"]
    assert d["birth_panchanga"]["vara"]["name_en"] == d["panchanga"]["vara"]["weekday"]
    bal = d["vimshottari"]["balance_at_birth"]
    assert bal["lord"] == d["vimshottari"]["birth_nakshatra_lord"]
    assert {"lord_en", "lord_ml", "years", "months", "days"} <= bal.keys()
    gul = next(u for u in d["upagrahas"] if u["name"] == "Gulika")
    assert gul["alias"] == "Mandi" and gul["name_ml"] == "മാന്ദി"
    assert "Prasna Marga" in gul["convention"] and isinstance(gul["longitude"], float)
    assert all("upagrahas" in h and isinstance(h["grahas"], list) for h in d["houses"])
    assert d["transits"]["at_utc"].startswith("2026-10-20")
    assert d["meta"]["ephemeris"] == "swiss", d["meta"]["warnings"]   # worker thread must load the .se1 files


def test_settings_change_output():
    b = dict(BODY, settings={"ayanamsa": "kp", "node": "true", "gulika_point": "middle"})
    d = client.post("/chart", json=b).json()
    assert d["meta"]["settings"]["ayanamsa"] == "kp"


def test_validation_errors():
    assert client.post("/chart", json=dict(BODY, place={"lat": 9.9})).status_code == 422
    assert client.post("/chart", json=dict(BODY, tz="Mars/Olympus")).status_code == 422


def test_geocode_cache(tmp_path, monkeypatch):
    class Loc:
        latitude, longitude, address = 9.9312, 76.2673, "Kochi, Kerala, India"

    class Fake:
        calls = 0

        def geocode(self, q):
            Fake.calls += 1
            return Loc()

    monkeypatch.setattr(geo, "CACHE_PATH", str(tmp_path / "g.json"))
    f = Fake()
    a = geo.geocode("Kochi ", geocoder=f)
    b = geo.geocode("kochi", geocoder=f)
    assert not a["cached"] and b["cached"] and Fake.calls == 1
    monkeypatch.setattr(chart_mod, "geocode", lambda name: {**a, "display_name": a["display_name"]})
    d = client.post("/chart", json=dict(BODY, place={"name": "Kochi"})).json()
    assert d["place"]["geocoded"] and any("geocoded" in w for w in d["meta"]["warnings"])


def test_polar_night_does_not_crash():
    b = dict(BODY, date="2000-12-21", time="12:00:00", place={"name": "Tromso", "lat": 69.65, "lon": 18.96}, tz="Europe/Oslo")
    r = client.post("/chart", json=b)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["upagrahas"] == [] and d["panchanga"]["sunrise_local"] is None
    assert any("does not rise" in w for w in d["meta"]["warnings"])


def test_concurrent_requests_do_not_mix_settings():
    from concurrent.futures import ThreadPoolExecutor
    bodies = [dict(BODY, settings={"ayanamsa": a}) for a in ["lahiri", "kp", "raman", "true_chitra"] * 6]
    serial = [client.post("/chart", json=b).json()["meta"]["ayanamsa_deg"] for b in bodies]
    with ThreadPoolExecutor(8) as ex:
        par = list(ex.map(lambda b: client.post("/chart", json=b).json()["meta"]["ayanamsa_deg"], bodies))
    assert par == serial and len(set(serial)) == 4
