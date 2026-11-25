"""Free-horoscope facts derived from a chart that is already computed.

The chart endpoint is unchanged. This module only reads positions. The rule
tables live in data/kerala_horoscope_rules.json so they can be reviewed
without hunting through this file. horoscope_version is the version of this
analysis, not a change to the chart engine version.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

HOROSCOPE_VERSION = "1"
RULES_PATH = Path(__file__).resolve().parent / "kerala_horoscope_rules.json"

NAK_EN = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishtha", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]
NAK_ML = [
    "അശ്വതി", "ഭരണി", "കാർത്തിക", "രോഹിണി", "മകയിരം", "തിരുവാതിര",
    "പുണർതം", "പൂയം", "ആയില്യം", "മകം", "പൂരം",
    "ഉത്രം", "അത്തം", "ചിത്തിര", "ചോതി", "വിശാഖം", "അനിഴം",
    "തൃക്കേട്ട", "മൂലം", "പൂരാടം", "ഉത്രാടം", "തിരുവോണം",
    "അവിട്ടം", "ചതയം", "പൂരുരുട്ടാതി", "ഉത്രട്ടാതി",
    "രേവതി",
]


@lru_cache(maxsize=1)
def load_rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def _src(block: dict) -> dict:
    s = block.get("source") or {}
    return {"work": s.get("work", "to verify"), "loc": s.get("loc", "to verify"),
            "status": s.get("status", "to_verify"), "note": s.get("note", "")}


def house_from(sign_index: int, ref_index: int) -> int:
    """Whole-sign house. Both indexes are 1..12. The reference sign is house 1."""
    return (sign_index - ref_index) % 12 + 1


def _ord(n: int) -> str:
    if n % 100 in (11, 12, 13):
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def _by_name(norm: dict) -> dict:
    return {g["name"]: g for g in norm["grahas"]}


def _aspects_of(name: str, rules: dict) -> set[int]:
    table = rules["aspects"]
    if name in table and name != "_note":
        return set(table[name])
    return set(table["all"])


def aspects(a: dict, b: dict, rules: dict) -> bool:
    """True when a throws an aspect onto b's sign."""
    return house_from(b["sign_index"], a["sign_index"]) in _aspects_of(a["name"], rules)


def linked(a: dict, b: dict, rules: dict, lords: list[str]) -> str | None:
    if a["sign_index"] == b["sign_index"]:
        return "conjunction"
    # Exchange: each sits in a sign the other rules.
    if lords[a["sign_index"] - 1] == b["name"] and lords[b["sign_index"] - 1] == a["name"]:
        return "exchange"
    if aspects(a, b, rules) and aspects(b, a, rules):
        return "mutual_aspect"
    return None


def normalize_chart(chart) -> dict:
    """Pull the fields the rules need. Accepts a ChartResponse or a dict of the same shape."""
    if hasattr(chart, "model_dump"):
        raw = chart.model_dump()
    else:
        raw = chart
    lagna = raw["lagna"]
    grahas = []
    for g in raw["grahas"]:
        dig = g.get("dignity") or {}
        nak = g.get("nakshatra") or {}
        grahas.append({
            "name": g["name"],
            "sign": g["sign"],
            "sign_index": g["sign_index"],
            "house": g["house"],
            "d9": (g.get("vargas") or {}).get("D9"),
            "exalted": bool(dig.get("exalted")),
            "debilitated": bool(dig.get("debilitated")),
            "sign_relation": dig.get("sign_relation"),
            "combust": g.get("combust") is True,
            "nakshatra_index": nak.get("index"),
            "nakshatra": nak.get("name"),
            "pada": nak.get("pada"),
            "longitude": g.get("longitude"),
        })
    star = raw.get("birth_star") or {}
    settings = ((raw.get("meta") or {}).get("settings")) or {}
    return {
        "lagna": {
            "sign": lagna["sign"],
            "sign_index": lagna["sign_index"],
            "d9": (lagna.get("vargas") or {}).get("D9"),
            "degree_in_sign": lagna.get("degree_in_sign"),
            "nakshatra_index": (lagna.get("nakshatra") or {}).get("index"),
            "nakshatra": (lagna.get("nakshatra") or {}).get("name"),
            "pada": (lagna.get("nakshatra") or {}).get("pada"),
        },
        "grahas": grahas,
        "birth_star_index": star.get("index") or next(g["nakshatra_index"] for g in grahas if g["name"] == "Moon"),
        "node": settings.get("node") or "mean",
    }


def _vg_row(body: str, sign: str, sign_index: int, d9: str | None) -> dict:
    same = bool(sign and d9 and sign == d9)
    return {"body": body, "sign": sign, "sign_index": sign_index, "navamsa": d9, "vargottama": same}


def _vargottama(norm: dict) -> list[dict]:
    lag = norm["lagna"]
    rows = [_vg_row("Lagna", lag["sign"], lag["sign_index"], lag["d9"])]
    rows.extend(_vg_row(g["name"], g["sign"], g["sign_index"], g["d9"]) for g in norm["grahas"])
    return rows


def _lords_of(lagna_index: int, houses: list[int], lords: list[str]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for h in houses:
        sign_index = (lagna_index - 1 + h - 1) % 12
        name = lords[sign_index]
        found.setdefault(name, []).append(h)
    return found


def _yogakaraka(norm: dict, rules: dict) -> dict | None:
    lords = rules["sign_lord"]
    lag = norm["lagna"]["sign_index"]
    kendra = _lords_of(lag, [4, 7, 10], lords)
    trikona = _lords_of(lag, [5, 9], lords)
    both = sorted(set(kendra) & set(trikona))
    if len(both) != 1:
        return None
    name = both[0]
    return {
        "planet": name,
        "kendra_houses": kendra[name],
        "trikona_houses": trikona[name],
        "source": _src(rules["yogakaraka"]),
    }


def _lordship_clause(name: str, kendra_houses: list[int], trikona_houses: list[int]) -> tuple[str, str]:
    """Say only the lordships the planet has. House 1 is marked as the lagna."""
    k = list(kendra_houses or [])
    t = list(trikona_houses or [])
    en_bits = []
    ml_bits = []
    if k:
        en_bits.append("kendra " + ", ".join(str(h) for h in k))
        ml_bits.append("കേന്ദ്രം " + ", ".join(str(h) for h in k))
    if t:
        en_bits.append("trikona " + ", ".join(str(h) for h in t))
        ml_bits.append("ത്രികോണം " + ", ".join(str(h) for h in t))
    lagna = 1 in k or 1 in t
    if not en_bits:
        return name + ".", name + "."
    if len(en_bits) == 1:
        en = f"{name} rules {en_bits[0]}"
        ml = f"{name} {ml_bits[0]} ഭരിക്കുന്നു"
    else:
        en = f"{name} rules {en_bits[0]} and {en_bits[1]}"
        ml = f"{name} {ml_bits[0]} ഉം {ml_bits[1]} ഉം ഭരിക്കുന്നു"
    if lagna:
        en += " (the lagna)"
        ml += " (ലഗ്നം)"
    return en + ".", ml + "."


def _reason(code: str, en: str, ml: str, **extra) -> dict:
    row = {"code": code, "en": en, "ml": ml}
    row.update(extra)
    return row


def _yoga(rule_id, name_en, name_ml, applies, source, reasons, cancelled=False, weakened=False):
    return {
        "id": rule_id,
        "name_en": name_en,
        "name_ml": name_ml,
        "applies": applies,
        "cancelled": cancelled if applies else False,
        "weakened": weakened if applies and not cancelled else False,
        "reasons": reasons,
        "source": source,
    }


def _kemadruma(norm, rules, by):
    spec = rules["kemadruma"]
    moon = by["Moon"]
    exclude = set(spec["occupants_exclude"])
    second = []
    twelfth = []
    for g in norm["grahas"]:
        if g["name"] in exclude or g["name"] == "Moon":
            continue
        h = house_from(g["sign_index"], moon["sign_index"])
        if h == 2:
            second.append(g["name"])
        elif h == 12:
            twelfth.append(g["name"])
    formed = not second and not twelfth
    reasons = []
    if formed:
        reasons.append(_reason(
            "empty_2_12",
            "No planet other than the Sun, Rahu, or Ketu is in the 2nd or the 12th from the Moon.",
            "ചന്ദ്രനിൽ നിന്ന് രണ്ടിലും പന്ത്രണ്ടിലും സൂര്യൻ, രാഹു, കേതു ഒഴികെയുള്ള ഗ്രഹമില്ല.",
        ))
    else:
        who = ", ".join(second + twelfth) or "a planet"
        reasons.append(_reason(
            "occupied_2_12",
            f"The 2nd or the 12th from the Moon is occupied ({who}), so Kemadruma is not formed.",
            f"ചന്ദ്രനിൽ നിന്ന് രണ്ടിലോ പന്ത്രണ്ടിലോ ഗ്രഹമുണ്ട് ({who}). കേമദ്രുമം ഉണ്ടാകുന്നില്ല.",
            planets=second + twelfth,
        ))
    cancels = []
    moon_house = house_from(moon["sign_index"], norm["lagna"]["sign_index"])
    if moon_house in rules["kendra"]:
        cancels.append(_reason(
            "moon_in_kendra_from_lagna",
            f"The Moon is in the {_ord(moon_house)} house from the lagna, which is a kendra.",
            f"ചന്ദ്രൻ ലഗ്നത്തിൽ നിന്ന് {moon_house}-ാം ഭാവത്തിലാണ്. അത് കേന്ദ്രമാണ്.",
            house=moon_house,
        ))
    kendra_names = set(spec["kendra_planets"])
    in_lagna = [g["name"] for g in norm["grahas"]
                if g["name"] in kendra_names and house_from(g["sign_index"], norm["lagna"]["sign_index"]) in rules["kendra"]]
    in_moon = [g["name"] for g in norm["grahas"]
               if g["name"] in kendra_names and g["name"] != "Moon"
               and house_from(g["sign_index"], moon["sign_index"]) in rules["kendra"]]
    if in_lagna:
        cancels.append(_reason(
            "planet_in_kendra_from_lagna",
            "A planet is in a kendra from the lagna (" + ", ".join(in_lagna) + ").",
            "ലഗ്നത്തിൽ നിന്ന് ഒരു കേന്ദ്രത്തിൽ ഗ്രഹമുണ്ട് (" + ", ".join(in_lagna) + ").",
            planets=in_lagna,
        ))
    if in_moon:
        cancels.append(_reason(
            "planet_in_kendra_from_moon",
            "A planet is in a kendra from the Moon (" + ", ".join(in_moon) + ").",
            "ചന്ദ്രനിൽ നിന്ന് ഒരു കേന്ദ്രത്തിൽ ഗ്രഹമുണ്ട് (" + ", ".join(in_moon) + ").",
            planets=in_moon,
        ))
    cancelled = formed and any(c["code"] in spec["cancellations"] for c in cancels)
    if cancelled:
        reasons.extend(cancels)
    return _yoga(spec["id"], spec["name_en"], spec["name_ml"], formed, _src(spec), reasons, cancelled=cancelled)


def _gajakesari(norm, rules, by):
    spec = rules["gajakesari"]
    moon = by["Moon"]
    jup = by["Jupiter"]
    h = house_from(jup["sign_index"], moon["sign_index"])
    applies = h in spec["houses"]
    reasons = [_reason(
        "jupiter_from_moon",
        f"Jupiter is in the {_ord(h)} house from the Moon.",
        f"വ്യാഴം ചന്ദ്രനിൽ നിന്ന് {h}-ാം ഭാവത്തിലാണ്.",
        house=h, planet="Jupiter",
    )]
    weakened = applies and jup["debilitated"] and not spec["debilitation_cancels"]
    if weakened:
        reasons.append(_reason("jupiter_debilitated",
                               "Jupiter is debilitated. The yoga is kept and marked weaker.",
                               "വ്യാഴം നീചമാണ്. യോഗം നിലനിർത്തുന്നു; ദുർബലമെന്ന് കുറിക്കുന്നു."))
    cancelled = applies and jup["debilitated"] and spec["debilitation_cancels"]
    return _yoga(spec["id"], spec["name_en"], spec["name_ml"], applies, _src(spec), reasons,
                 cancelled=cancelled, weakened=weakened)


def _mahapurusha(norm, rules, by):
    spec = rules["pancha_mahapurusha"]
    out = []
    for item in spec["items"]:
        g = by[item["planet"]]
        in_sign = g["sign"] in item["signs"]
        in_kendra = g["house"] in rules["kendra"]
        applies = in_sign and in_kendra
        reasons = [_reason(
            "sign_and_kendra",
            f"{item['planet']} is in {g['sign']}, house {g['house']} from the lagna.",
            f"{item['planet']} {g['sign']} രാശിയിൽ, ലഗ്നത്തിൽ നിന്ന് {g['house']}-ാം ഭാവം.",
            planet=item["planet"], sign=g["sign"], house=g["house"],
        )]
        weakened = applies and g["combust"] and not spec["combust_cancels"]
        cancelled = applies and g["combust"] and spec["combust_cancels"]
        if weakened:
            reasons.append(_reason("combust", "The planet is combust. The yoga is kept and marked weaker.",
                                   "ഗ്രഹം മൗഢ്യമാണ്. യോഗം നിലനിർത്തുന്നു; ദുർബലമെന്ന് കുറിക്കുന്നു."))
        out.append(_yoga(item["id"], item["name_en"], item["name_ml"], applies, _src(spec), reasons,
                         cancelled=cancelled, weakened=weakened))
    return out


def _raja(norm, rules, by):
    spec = rules["raja"]
    lords = rules["sign_lord"]
    lag = norm["lagna"]["sign_index"]
    kendra = _lords_of(lag, [1, 4, 7, 10], lords)
    trikona = _lords_of(lag, [1, 5, 9], lords)
    names = sorted(set(kendra) | set(trikona))
    out = []
    seen = set()
    for i, a_name in enumerate(names):
        for b_name in names[i + 1:]:
            a_k, b_t = kendra.get(a_name, []), trikona.get(b_name, [])
            b_k, a_t = kendra.get(b_name, []), trikona.get(a_name, [])
            # A pair qualifies when one side supplies a kendra and the other a trikona,
            # and the two houses are not the same single house (both claiming only house 1).
            ok = False
            kendra_houses, trikona_houses = [], []
            if a_k and b_t and not (a_k == [1] and b_t == [1]):
                ok = True
                kendra_houses, trikona_houses = a_k, b_t
            if b_k and a_t and not (b_k == [1] and a_t == [1]):
                ok = True
                kendra_houses = sorted(set(kendra_houses + b_k))
                trikona_houses = sorted(set(trikona_houses + a_t))
            if not ok:
                continue
            link = linked(by[a_name], by[b_name], rules, lords)
            if link not in spec["links"]:
                continue
            key = tuple(sorted((a_name, b_name)))
            if key in seen:
                continue
            seen.add(key)

            def role(name):
                return {"planet": name, "kendra_houses": kendra.get(name, []), "trikona_houses": trikona.get(name, [])}

            def clause(name):
                return _lordship_clause(name, kendra.get(name, []), trikona.get(name, []))

            link_en = link.replace("_", " ")
            reasons = [_reason(
                link,
                f"{a_name} and {b_name} are in {link_en}. {clause(a_name)[0]} {clause(b_name)[0]}",
                f"{a_name} ഉം {b_name} ഉം {link_en} ബന്ധത്തിലാണ്. {clause(a_name)[1]} {clause(b_name)[1]}",
                planets=[a_name, b_name], link=link, roles=[role(a_name), role(b_name)],
            )]
            out.append(_yoga(
                "raja_" + "_".join(key).lower(),
                spec["name_en"], spec["name_ml"], True, _src(spec), reasons,
            ))
    return out


def _vipareeta(norm, rules, by):
    spec = rules["vipareeta"]
    lords = rules["sign_lord"]
    lag = norm["lagna"]["sign_index"]
    out = []
    for item in spec["items"]:
        sign_index = (lag - 1 + item["house"] - 1) % 12 + 1
        lord = lords[sign_index - 1]
        placed = by[lord]["house"]
        other = placed in rules["dusthana"] and placed != item["house"]
        own = placed == item["house"]
        applies = other if spec["require_other_dusthana"] else (other or own)
        reasons = [_reason(
            "dusthana_lord",
            f"The lord of house {item['house']} is {lord}, placed in house {placed}.",
            f"{item['house']}-ാം ഭാവാധിപൻ {lord}, {placed}-ാം ഭാവത്തിൽ.",
            planet=lord, house=placed, of_house=item["house"],
        )]
        out.append(_yoga(item["id"], item["name_en"], item["name_ml"], applies, _src(spec), reasons))
    return out


def _budha_aditya(norm, rules, by):
    spec = rules["budha_aditya"]
    sun, mer = by["Sun"], by["Mercury"]
    applies = sun["sign_index"] == mer["sign_index"]
    reasons = [_reason(
        "same_sign" if applies else "different_signs",
        f"The Sun is in {sun['sign']} and Mercury is in {mer['sign']}.",
        f"സൂര്യൻ {sun['sign']}, ബുധൻ {mer['sign']}.",
        planets=["Sun", "Mercury"],
    )]
    weakened = applies and mer["combust"] and not spec["combust_cancels"]
    cancelled = applies and mer["combust"] and spec["combust_cancels"]
    if weakened:
        reasons.append(_reason("combust", "Mercury is combust. The yoga is kept and marked weaker.",
                               "ബുധൻ മൗഢ്യമാണ്. യോഗം നിലനിർത്തുന്നു; ദുർബലമെന്ന് കുറിക്കുന്നു."))
    return _yoga(spec["id"], spec["name_en"], spec["name_ml"], applies, _src(spec), reasons,
                 cancelled=cancelled, weakened=weakened)


def _chandra_mangala(norm, rules, by):
    spec = rules["chandra_mangala"]
    moon, mars = by["Moon"], by["Mars"]
    applies = moon["sign_index"] == mars["sign_index"]
    reasons = [_reason(
        "same_sign" if applies else "different_signs",
        f"The Moon is in {moon['sign']} and Mars is in {mars['sign']}.",
        f"ചന്ദ്രൻ {moon['sign']}, ചൊവ്വ {mars['sign']}.",
        planets=["Moon", "Mars"],
    )]
    return _yoga(spec["id"], spec["name_en"], spec["name_ml"], applies, _src(spec), reasons)


def _neecha(norm, rules, by):
    spec = rules["neecha_bhanga"]
    lords = rules["sign_lord"]
    signs = rules["signs"]
    exalt = rules["exaltation_sign"]
    out = []
    debilitated = [g for g in norm["grahas"] if g["debilitated"]]
    if not debilitated:
        return [_yoga(spec["id"], spec["name_en"], spec["name_ml"], False, _src(spec), [
            _reason("none_debilitated", "No planet is debilitated.", "നീചഗ്രഹമില്ല.")
        ])]
    for g in debilitated:
        disp = lords[g["sign_index"] - 1]
        exalt_sign = exalt[g["name"]]
        exalt_lord = lords[signs.index(exalt_sign)]
        reasons = []
        fired = False
        for kind, lord_name in (("dispositor_in_kendra", disp), ("exaltation_lord_in_kendra", exalt_lord)):
            if kind not in spec["paths"]:
                continue
            lord = by[lord_name]
            from_lagna = house_from(lord["sign_index"], norm["lagna"]["sign_index"])
            from_moon = house_from(lord["sign_index"], by["Moon"]["sign_index"])
            hit = []
            if "lagna" in spec["kendra_from"] and from_lagna in rules["kendra"]:
                hit.append(f"kendra {from_lagna} from the lagna")
            if "Moon" in spec["kendra_from"] and from_moon in rules["kendra"]:
                hit.append(f"kendra {from_moon} from the Moon")
            if hit:
                fired = True
                reasons.append(_reason(
                    kind,
                    f"{g['name']} is debilitated in {g['sign']}. {lord_name} is in " + " and ".join(hit) + ".",
                    f"{g['name']} {g['sign']}യിൽ നീചം. {lord_name} കേന്ദ്രത്തിൽ.",
                    planet=g["name"], lord=lord_name,
                    house_from_lagna=from_lagna, house_from_moon=from_moon,
                ))
        if not fired:
            reasons.append(_reason(
                "no_cancellation",
                f"{g['name']} is debilitated in {g['sign']}, and neither cancellation is in a kendra.",
                f"{g['name']} നീചമാണ്. ഭംഗം കേന്ദ്രത്തിൽ കണ്ടില്ല.",
                planet=g["name"],
            ))
        out.append(_yoga(
            spec["id"] + "_" + g["name"].lower(),
            spec["name_en"], spec["name_ml"], fired, _src(spec), reasons,
        ))
    return out


def _ref_index(norm, by, ref: str) -> int:
    if ref == "lagna":
        return norm["lagna"]["sign_index"]
    return by[ref]["sign_index"]


def _kuja(norm, rules, by):
    spec = rules["kuja"]
    mars = by["Mars"]
    rows = []
    for ref in spec["references"]:
        ref_i = _ref_index(norm, by, ref)
        h = house_from(mars["sign_index"], ref_i)
        indicated = h in spec["houses"]
        matched = []
        for ex in spec["exceptions"]:
            if mars["sign"] in ex["signs"] and h in ex["houses"]:
                matched.append({
                    "id": ex["id"],
                    "applied": bool(spec["apply_listed_exceptions"]),
                    "en": ex["en"],
                    "ml": ex["ml"],
                    "review": "K03",
                })
        status = "not_indicated"
        if indicated and spec["apply_listed_exceptions"] and matched:
            status = "exception_applied"
        elif indicated:
            status = "indicated"
        rows.append({
            "from": ref,
            "house": h,
            "sign": mars["sign"],
            "sign_index": mars["sign_index"],
            "indicated": indicated,
            "status": status,
            "exceptions": matched,
        })
    return {
        "id": spec["id"],
        "name_en": spec["name_en"],
        "name_ml": spec["name_ml"],
        "also_en": spec["also_en"],
        "also_ml": spec["also_ml"],
        "houses": spec["houses"],
        "report": spec["report"],
        "combine_into_one_verdict": spec["combine_into_one_verdict"],
        "apply_listed_exceptions": spec["apply_listed_exceptions"],
        "references": rows,
        "not_applied_on_one_chart": spec["not_applied_on_one_chart"],
        "source": _src(spec),
        "review": "K01-K05 open in kuja-review-2026-11-07. Exceptions are listed and not applied.",
    }


def _kala_sarpa(norm, rules, by):
    spec = rules["kala_sarpa"]
    rahu = by["Rahu"]["longitude"]
    ketu = by["Ketu"]["longitude"]
    if rahu is None or ketu is None:
        return {"id": spec["id"], "name_en": spec["name_en"], "name_ml": spec["name_ml"],
                "present": False, "arc": None,
                "reason_en": "Node longitudes are not in this chart, so Kala Sarpa is not scored.",
                "reason_ml": "രാഹു-കേതു രേഖാംശം ഈ ഗ്രഹനിലയിൽ ഇല്ല. കാലസർപ്പം കണക്കാക്കിയില്ല.",
                "source": _src(spec)}

    def inside(lon, start, end):
        # Open arc going forward from start to end. A point on either end is outside.
        span = (end - start) % 360
        at = (lon - start) % 360
        return 0 < at < span

    sides = {"rahu_to_ketu": [], "ketu_to_rahu": [], "on_node": []}
    for name in spec["planets"]:
        lon = by[name]["longitude"]
        if lon is None:
            sides["on_node"].append(name)
            continue
        if abs((lon - rahu + 180) % 360 - 180) < 1e-6 or abs((lon - ketu + 180) % 360 - 180) < 1e-6:
            sides["on_node"].append(name)
        elif inside(lon, rahu, ketu):
            sides["rahu_to_ketu"].append(name)
        elif inside(lon, ketu, rahu):
            sides["ketu_to_rahu"].append(name)
        else:
            sides["on_node"].append(name)
    present = (len(sides["rahu_to_ketu"]) == 7 or len(sides["ketu_to_rahu"]) == 7) and not sides["on_node"]
    arc = None
    if present:
        arc = "rahu_to_ketu" if len(sides["rahu_to_ketu"]) == 7 else "ketu_to_rahu"
    if present:
        en = "All seven planets lie in one semicircle between Rahu and Ketu."
        ml = "ഏഴ് ഗ്രഹങ്ങളും രാഹുവിനും കേതുവിനും ഇടയിലെ ഒരു പകുതിയിലാണ്."
    else:
        en = "The seven planets are not all in one semicircle between Rahu and Ketu."
        ml = "ഏഴ് ഗ്രഹങ്ങളും രാഹുവിനും കേതുവിനും ഇടയിലെ ഒരു പകുതിയിലല്ല."
    return {"id": spec["id"], "name_en": spec["name_en"], "name_ml": spec["name_ml"],
            "present": present, "arc": arc, "sides": sides,
            "reason_en": en, "reason_ml": ml, "source": _src(spec)}


def _papa(norm, rules, by):
    spec = rules["papasamyam"]
    rows = []
    total = 0
    for ref in spec["references"]:
        ref_i = _ref_index(norm, by, ref)
        hits = []
        points = 0
        for name, weight in spec["planets"].items():
            h = house_from(by[name]["sign_index"], ref_i)
            if h in spec["houses"]:
                hits.append({"planet": name, "house": h, "points": weight})
                points += weight
        total += points
        rows.append({"from": ref, "points": points, "hits": hits})
    return {
        "id": spec["id"], "name_en": spec["name_en"], "name_ml": spec["name_ml"],
        "references": rows, "total": total, "one_chart_only": True,
        "verdict": None,
        "source": _src(spec),
    }


def _chandrashtama(norm, rules):
    spec = rules["chandrashtama"]
    birth = norm["birth_star_index"]
    if spec["count_birth_as_one"]:
        index = (birth - 1 + spec["offset"] - 1) % 27 + 1
    else:
        index = (birth - 1 + spec["offset"]) % 27 + 1
    return {
        "id": spec["id"],
        "name_en": spec["name_en"],
        "name_ml": spec["name_ml"],
        "birth_index": birth,
        "nakshatra_index": index,
        "nakshatra_en": NAK_EN[index - 1],
        "nakshatra_ml": NAK_ML[index - 1],
        "count": "birth star counted as 1" if spec["count_birth_as_one"] else "offset added past the birth star",
        "source": _src(spec),
    }


def build_horoscope(chart, rules: dict | None = None) -> dict:
    rules = rules or load_rules()
    norm = normalize_chart(chart)
    by = _by_name(norm)
    yogas = [
        _kemadruma(norm, rules, by),
        _gajakesari(norm, rules, by),
        *_mahapurusha(norm, rules, by),
        *_raja(norm, rules, by),
        *_vipareeta(norm, rules, by),
        _budha_aditya(norm, rules, by),
        _chandra_mangala(norm, rules, by),
        *_neecha(norm, rules, by),
    ]
    node = norm["node"] if norm["node"] in ("mean", "true") else "mean"
    return {
        "horoscope_version": HOROSCOPE_VERSION,
        "rules_version": rules.get("version", "1"),
        "node": node,
        "node_label_en": "Rahu/Ketu: mean node" if node == "mean" else "Rahu/Ketu: true node",
        "node_label_ml": "രാഹു/കേതു: മീൻ നോഡ്" if node == "mean" else "രാഹു/കേതു: ട്രൂ നോഡ്",
        "vargottama": _vargottama(norm),
        "yogakaraka": _yogakaraka(norm, rules),
        "yogas": yogas,
        "doshas": {
            "kuja": _kuja(norm, rules, by),
            "kala_sarpa": _kala_sarpa(norm, rules, by),
            "papasamyam": _papa(norm, rules, by),
        },
        "chandrashtama": _chandrashtama(norm, rules),
    }
