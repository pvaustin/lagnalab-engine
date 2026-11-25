"""Rule matcher tests: derived facts, each operator, synthetic charts for rare yogas, the corpus
rule set on the golden charts, and hand-verified chart/rule pairs (docs/RULES_PILOT.md)."""
from pathlib import Path

import pytest

from lagnalab_engine.constants import RASIS, SIGN_LORD
from lagnalab_engine.core import dignity
from lagnalab_engine.rules import DEFAULT_RULES_DIR, Facts, Rule, RuleError, evaluate, load_rules, match
from golden_compare import engine_chart, load

ALL9 = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def synth(lagna, pos, d9=None, paksha="Shukla", gulika=1, day=True):
    """Minimal chart dict. pos: graha -> sign (1..12). d9: name -> D9 sign (default = rasi sign)."""
    d9 = d9 or {}
    def var(name, s): return {"D9": RASIS[d9.get(name, s) - 1]}
    grahas = []
    for g in ALL9:
        s = pos.get(g, 1); h = (s - lagna) % 12 + 1
        grahas.append(dict(name=g, sign_index=s, sign=RASIS[s - 1], house=h, vargas=var(g, s),
                           dignity=dignity(g, s - 1, h)))
    return dict(lagna=dict(sign_index=lagna, vargas=var("Lagna", lagna)), grahas=grahas,
                upagrahas=[dict(name="Gulika", sign_index=gulika, house=(gulika - lagna) % 12 + 1)],
                panchanga=dict(tithi=dict(paksha=paksha), is_day_birth=day))


def rule(rid, cond, applies="natal"):
    return Rule(rid, dict(rule_id=rid, condition=cond, applies_to=applies, citations=["BJ.01.01"]), Path("x"))


# ------------------------------------------------------------------ derived facts
def test_aspects_follow_bj_2_13():
    f = Facts.from_chart(synth(1, {"Mars": 1, "Jupiter": 1, "Saturn": 1, "Sun": 1}))
    for s, who in [(7, {"Mars", "Jupiter", "Saturn", "Sun"}), (4, {"Mars"}), (8, {"Mars"}), (5, {"Jupiter"}),
                   (9, {"Jupiter"}), (3, {"Saturn"}), (10, {"Saturn"}), (2, set()), (1, set())]:
        f.sign["Moon"] = s
        assert {g for g in ("Mars", "Jupiter", "Saturn", "Sun") if f.aspects(g, "Moon")} == who, s
    assert not f.aspects("Rahu", "Moon")


def test_benefic_rules_bj_2_5():
    f = Facts.from_chart(synth(1, {"Mercury": 3, "Sun": 3, "Moon": 5}, paksha="Krishna"))
    assert not f.is_benefic("Mercury")      # with the Sun
    assert not f.is_benefic("Moon")         # waning
    assert f.is_benefic("Jupiter") and f.is_benefic("Venus")
    f = Facts.from_chart(synth(1, {"Mercury": 4, "Sun": 3, "Moon": 5}, paksha="Shukla"))
    assert f.is_benefic("Mercury") and f.is_benefic("Moon")


def test_house_and_lord():
    f = Facts.from_chart(synth(2, {"Moon": 9, "Saturn": 2}))
    assert f.house("Saturn") == 1 and f.house("Moon") == 8 and f.house("Saturn", "Moon") == 6
    assert f.lord_of_house(10) == SIGN_LORD[10] == "Saturn"


def test_vargottama_and_d9_dispositor():
    c = synth(2, {"Saturn": 2}, d9={"Saturn": 6, "Lagna": 2})
    ev = []
    assert evaluate({"vargottama": {"graha": "Lagna"}}, Facts.from_chart(c), ev)
    assert evaluate({"d9_dispositor_of_lord": {"of_house": 10, "is": "Mercury"}}, Facts.from_chart(c), ev)
    assert "whose lord is Mercury" in ev[-1]


def test_count_min_max_and_template():
    c = synth(1, {"Mars": 1, "Venus": 2, "Saturn": 10})   # Mars, Venus, Saturn all own sign
    f = Facts.from_chart(c)
    three = {"count": {"grahas": ["Mars", "Venus", "Saturn", "Sun"], "min": 3, "max": 3,
                       "satisfy": {"dignity": {"graha": "$g", "is": "own"}}}}
    assert evaluate(three, f, [])
    three["count"]["max"] = 2
    assert not evaluate(three, f, [])


def test_bad_rules_raise():
    f = Facts.from_chart(synth(1, {}))
    with pytest.raises(RuleError):
        evaluate({"in_house": {"graha": "Sun", "house": 1}, "not": {}}, f, [])
    with pytest.raises(RuleError):
        evaluate({"bogus": {}}, f, [])


def test_applies_to_filter():
    r = [rule("A", {"in_house": {"graha": "Sun", "house": 1}}, "prashna")]
    assert match(synth(1, {"Sun": 1}), r) == []
    assert [x["rule_id"] for x in match(synth(1, {"Sun": 1}), r, applies_to=("prashna",))] == ["A"]


# ------------------------------------------------------------------ corpus rules
corpus = pytest.mark.skipif(not Path(DEFAULT_RULES_DIR).is_dir(), reason="corpus rules not checked out next to engine")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


@pytest.fixture(scope="module")
def golden():
    inputs, _ = load()
    return {c["id"]: engine_chart(c) for c in inputs}


def fired(chart, rules):
    return {f["rule_id"]: f for f in match(chart, rules)}


@corpus
def test_corpus_loads(rules):
    assert len(rules) >= 50
    assert all(r.data["citations"] for r in rules)


@corpus
def test_rare_raja_yogas_fire_on_synthetic_charts(rules):
    # BJ 11.2: Sun exalted rising in Mesha, Mars exalted in Makara, Jupiter exalted in Karka
    assert "BJ-11-three-exalted-one-rising" in fired(synth(1, {"Sun": 1, "Mars": 10, "Jupiter": 4, "Saturn": 2}), rules)
    # BJ 11.2 second half: Jupiter exalted rising in Karka, Moon in Karka
    assert "BJ-11-exalted-rising-moon-karka" in fired(synth(4, {"Jupiter": 4, "Moon": 4, "Sun": 3, "Mars": 3, "Saturn": 3}), rules)
    # BJ 11.8: Mesha rising with Mars, Jupiter in Karka
    assert "BJ-11-mars-mesha-rising-jupiter-karka" in fired(synth(1, {"Mars": 1, "Jupiter": 4}), rules)
    # BJ 11.20: Jupiter rising, Saturn 7th, Sun 10th
    assert "BJ-11-benefic-rising-saturn-7-sun-10" in fired(synth(3, {"Jupiter": 3, "Saturn": 9, "Sun": 12}), rules)
    # BJ 11.16: Mercury rising in Kanya (exalted, own), Venus in the 9th in her own Vrishabha
    assert "BJ-11-mercury-rising-benefic-9th" in fired(synth(6, {"Mercury": 6, "Venus": 2}), rules)
    # BJ 11.3: vargottama lagna aspected by 4 planets from the 7th
    assert "BJ-11-lagna-vargottama-aspected" in fired(synth(1, {"Sun": 7, "Mars": 7, "Venus": 7, "Saturn": 7, "Moon": 2}), rules)
    # BJ 21.1: four planets in own signs
    assert "BJ-21-own-sign-four-plus" in fired(synth(1, {"Mars": 1, "Venus": 2, "Mercury": 3, "Moon": 4}), rules)


@corpus
def test_chandra_yogas_partition(rules, golden):
    """Sunapha, Anapha, Durudhura and Kemadruma (base definition) are mutually exclusive and exhaustive."""
    four = {"BJ-13-sunapha", "BJ-13-anapha", "BJ-13-durudhura", "BJ-13-kemadruma"}
    for cid, ch in golden.items():
        assert len(four & set(fired(ch, rules))) == 1, cid


@corpus
def test_livelihood_exactly_one(rules, golden):
    for cid, ch in golden.items():
        assert len([r for r in fired(ch, rules) if r.startswith("BJ-10-livelihood-")]) == 1, cid


@corpus
def test_firing_is_deterministic(rules, golden):
    ch = golden["A07"]
    assert match(ch, rules) == match(ch, rules)


# Hand-verified pairs; the reasoning is written out in docs/RULES_PILOT.md.
HAND = [
    ("A02", "BJ-13-kemadruma", True),        # Moon in Tula with four planets; Vrischika and Kanya empty (base definition)
    # Default Gulika is the Prasna Marga ghatika table: Makara, 12th from Kumbha.
    # gulika_point=start still puts it in Dhanu, the 11th (RULES_PILOT.md).
    ("A02", "PM-14-gulika-h11", False),
    ("A03", "BJ-11-three-strong-planets", True),  # Saturn exalted in Tula, Mercury own in Mithuna, Jupiter own in Dhanu
    ("A07", "BJ-10-livelihood-mercury", True),    # Vrishabha lagna, 10th lord Saturn at 27°52' Vrishabha -> D9 Kanya (Mercury)
    ("A07", "BJ-21-exalted-aspected-by-friend", True),  # Jupiter exalted in Karka, Mars in Mesha aspects the 4th
    ("A09", "BJ-13-adhi-yoga", True),        # Moon Meena; Mercury Tula (8th), Jupiter and Venus Kanya (7th)
    ("E10", "BJ-11-moon-vargottama-aspected", True),  # Moon 1°01' Tula (D9 Tula); Mars, Mercury, Jupiter, Venus in Mesha aspect her
    ("A02", "BJ-13-sunapha", False),         # 2nd from Moon (Vrischika) empty
]


@corpus
@pytest.mark.parametrize("cid,rid,expect", HAND)
def test_hand_verified(rules, golden, cid, rid, expect):
    assert (rid in fired(golden[cid], rules)) is expect


@corpus
def test_api_endpoint():
    from fastapi.testclient import TestClient
    from lagnalab_engine.api import app
    r = TestClient(app).post("/chart/rules", json={"date": "1943-07-17", "time": "03:25", "tz": "Asia/Kolkata",
                                                   "place": {"lat": 11.2588, "lon": 75.7804}})
    assert r.status_code == 200
    ids = [f["rule_id"] for f in r.json()["rules_fired"]]
    assert ids == sorted(ids) and all(f["citations"] for f in r.json()["rules_fired"])
