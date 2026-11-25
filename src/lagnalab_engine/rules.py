"""Deterministic rule matcher (M1 pilot).

Takes a chart from the engine (a ChartResponse or its JSON dict) and a directory of rule YAML
files (the corpus repo's rules/ tree) and returns the rules whose condition holds, each with its
citations and the facts that made it fire. No scoring, no LLM: a rule fires or it does not.

Facts are read from the engine output; a few are derived here from it and documented:
- sign of every graha, of Lagna, Gulika and Mandi (sign_index 1..12)
- house of X from Y: whole-sign count, 1 = same sign
- full aspects (graha drishti) as in Brihat Jataka 2.13: every graha the 7th; Mars also the
  4th and 8th, Jupiter the 5th and 9th, Saturn the 3rd and 10th. Partial (1/4, 1/2, 3/4) sight is
  not modelled. Rahu, Ketu, Gulika and Mandi cast no aspect.
- conjunction: same sign
- vargottama: the D9 sign equals the rasi sign
- natural benefics as in BJ 2.5: Jupiter, Venus; Mercury unless in the same sign as a malefic;
  the Moon when waxing (Shukla paksha). Malefics: Sun, Mars, Saturn, waning Moon (and Mercury
  with them).
- friends: the engine's naisargika table (constants.NAISARGIKA)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

from .constants import NAISARGIKA, SIGN_LORD, RASIS, SEVEN

ASPECT_EXTRA = {"Mars": (4, 8), "Jupiter": (5, 9), "Saturn": (3, 10)}
DEFAULT_RULES_DIR = Path(os.environ.get("LAGNALAB_RULES",
                                        Path(__file__).resolve().parents[1] / "corpus" / "rules"))


class RuleError(ValueError):
    pass


@dataclass
class Facts:
    sign: dict[str, int]                       # name -> 1..12 (incl. Lagna, Gulika, Mandi)
    d9: dict[str, int]                         # name -> D9 sign 1..12 (grahas + Lagna)
    dignity: dict[str, dict]
    waxing: bool
    day_birth: bool | None

    @classmethod
    def from_chart(cls, chart) -> "Facts":
        d = chart.model_dump(mode="json") if hasattr(chart, "model_dump") else chart
        idx = {n: i + 1 for i, n in enumerate(RASIS)}
        sign = {"Lagna": d["lagna"]["sign_index"]}
        d9 = {"Lagna": idx[d["lagna"]["vargas"]["D9"]]}
        dig = {}
        for g in d["grahas"]:
            sign[g["name"]] = g["sign_index"]; d9[g["name"]] = idx[g["vargas"]["D9"]]; dig[g["name"]] = g["dignity"]
        for u in d.get("upagrahas", []):
            sign[u["name"]] = u["sign_index"]
        paksha = (d["panchanga"].get("tithi") or {}).get("paksha")
        return cls(sign=sign, d9=d9, dignity=dig, waxing=paksha == "Shukla",
                   day_birth=d["panchanga"].get("is_day_birth"))

    # ---- derived facts
    def house(self, x: str, ref: str = "Lagna") -> int:
        return (self.sign[x] - self.sign[self._ref(ref)]) % 12 + 1

    @staticmethod
    def _ref(ref: str) -> str:
        return {"lagna": "Lagna", "moon": "Moon", "sun": "Sun"}.get(ref, ref)

    def aspects(self, a: str, target: str) -> bool:
        if a not in SEVEN or a == target:
            return False
        h = (self.sign[target] - self.sign[a]) % 12 + 1
        return h == 7 or h in ASPECT_EXTRA.get(a, ())

    def conjunct(self, a: str, b: str) -> bool:
        return a != b and self.sign[a] == self.sign[b]

    def is_malefic(self, g: str) -> bool:
        if g in ("Sun", "Mars", "Saturn"):
            return True
        if g == "Moon":
            return not self.waxing
        if g == "Mercury":
            return any(self.conjunct("Mercury", m) for m in ("Sun", "Mars", "Saturn")) or \
                (not self.waxing and self.conjunct("Mercury", "Moon"))
        return False

    def is_benefic(self, g: str) -> bool:
        return g in ("Jupiter", "Venus") or (g in ("Mercury", "Moon") and not self.is_malefic(g))

    def lord_of_house(self, n: int, ref: str = "Lagna") -> str:
        return SIGN_LORD[(self.sign[self._ref(ref)] - 1 + n - 1) % 12]

    def dig_is(self, g: str, what: str) -> bool:
        d = self.dignity.get(g)
        if d is None:
            return False
        rel = d.get("sign_relation")
        return {"exalted": d["exalted"], "debilitated": d["debilitated"],
                "own": rel == "own", "friend": rel == "friend", "neutral": rel == "neutral",
                "enemy": rel == "enemy",
                "exalted_or_own": d["exalted"] or rel == "own",
                "strong": (d["exalted"] or rel in ("own", "friend")) and not d["debilitated"],
                }[what]


def _as_list(v) -> list:
    return v if isinstance(v, list) else [v]


def _sub(node, g: str):
    """Replace the placeholder '$g' with a graha name inside a condition template."""
    if isinstance(node, str):
        return g if node == "$g" else node
    if isinstance(node, list):
        return [_sub(x, g) for x in node]
    if isinstance(node, dict):
        return {k: _sub(v, g) for k, v in node.items()}
    return node


def evaluate(cond: dict, f: Facts, ev: list[str]) -> bool:
    """Evaluate one condition node. Appends a short fact string to ev for each true leaf."""
    if not isinstance(cond, dict) or len(cond) != 1:
        raise RuleError(f"condition node must have exactly one key: {cond!r}")
    (op, a), = cond.items()
    if op == "all":
        sub = []; ok = all(evaluate(c, f, sub) for c in a)
        if ok: ev.extend(sub)
        return ok
    if op == "any":
        for c in a:
            sub = []
            if evaluate(c, f, sub):
                ev.extend(sub); return True
        return False
    if op == "not":
        ok = not evaluate(a, f, [])
        if ok: ev.append(f"not({_short(a)})")
        return ok
    if op == "in_house":
        h = f.house(a["graha"], a.get("from", "Lagna"))
        ok = h in _as_list(a["house"])
        if ok: ev.append(f"{a['graha']} in house {h} from {f._ref(a.get('from', 'Lagna'))}")
        return ok
    if op == "in_sign":
        s = f.sign[a["graha"]]; ok = s in _as_list(a["sign"])
        if ok: ev.append(f"{a['graha']} in {RASIS[s - 1]}")
        return ok
    if op == "dignity":
        ok = f.dig_is(a["graha"], a["is"])
        if ok: ev.append(f"{a['graha']} {a['is']}")
        return ok
    if op == "conjunct":
        gs = a["grahas"]; ok = all(f.sign[g] == f.sign[gs[0]] for g in gs[1:])
        if ok: ev.append(f"{' + '.join(gs)} in {RASIS[f.sign[gs[0]] - 1]}")
        return ok
    if op == "aspects":
        ok = f.aspects(a["graha"], a["target"])
        if ok: ev.append(f"{a['graha']} aspects {a['target']}")
        return ok
    if op == "vargottama":
        g = a["graha"]; ok = f.sign[g] == f.d9[g]
        if ok: ev.append(f"{g} vargottama ({RASIS[f.sign[g] - 1]})")
        return ok
    if op == "lord_in_house":
        lord = f.lord_of_house(a["of_house"], a.get("from", "Lagna"))
        h = f.house(lord, a.get("lord_from", "Lagna")); ok = h in _as_list(a["house"])
        if ok: ev.append(f"lord of house {a['of_house']} from {f._ref(a.get('from', 'Lagna'))} ({lord}) in house {h}")
        return ok
    if op == "d9_dispositor_of_lord":
        lord = f.lord_of_house(a["of_house"], a.get("from", "Lagna"))
        disp = SIGN_LORD[f.d9[lord] - 1]; ok = disp == a["is"]
        if ok: ev.append(f"lord of house {a['of_house']} = {lord}, in D9 {RASIS[f.d9[lord] - 1]}, whose lord is {disp}")
        return ok
    if op == "house_occupied":
        ref = a.get("from", "Lagna")
        occ = [g for g in a["by"] if f.house(g, ref) == a["house"]]
        if occ: ev.append(f"house {a['house']} from {f._ref(ref)} holds {', '.join(occ)}")
        return bool(occ)
    if op == "benefic":
        ok = f.is_benefic(a["graha"])
        if ok: ev.append(f"{a['graha']} benefic")
        return ok
    if op == "friend_contact":
        g = a["graha"]; fr = NAISARGIKA.get(g, {}).get("friends", [])
        hit = [x for x in fr if (f.conjunct(g, x) if a["by"] == "conjunction" else f.aspects(x, g))]
        if hit: ev.append(f"{g} {'with' if a['by'] == 'conjunction' else 'aspected by'} friend {', '.join(hit)}")
        return bool(hit)
    if op == "moon_waxing":
        ok = f.waxing == a
        if ok: ev.append("Moon waxing" if a else "Moon waning")
        return ok
    if op == "day_birth":
        ok = f.day_birth == a
        if ok: ev.append("day birth" if a else "night birth")
        return ok
    if op == "count":
        hits = []
        for g in a["grahas"]:
            sub = []
            if evaluate(_sub(a["satisfy"], g), f, sub):
                hits.append((g, sub))
        n = len(hits); ok = n >= a.get("min", 0) and (a.get("max") is None or n <= a["max"])
        if ok: ev.append(f"{n} of {a['grahas']} satisfy: " + "; ".join(f"{g}: {', '.join(s)}" for g, s in hits))
        return ok
    raise RuleError(f"unknown condition operator {op!r}")


def _short(c) -> str:
    s = repr(c); return s if len(s) < 80 else s[:77] + "..."


@dataclass
class Rule:
    rule_id: str
    data: dict
    path: Path

    @property
    def condition(self) -> dict:
        return self.data["condition"]


def load_rules(rules_dir: str | Path | None = None) -> list[Rule]:
    root = Path(rules_dir or DEFAULT_RULES_DIR)
    if not root.is_dir():
        raise RuleError(f"rules directory not found: {root}")
    out = []
    for p in sorted(root.rglob("*.yaml")):
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(d, dict) or "rule_id" not in d or "condition" not in d:
            raise RuleError(f"{p}: not a rule file")
        out.append(Rule(d["rule_id"], d, p))
    ids = [r.rule_id for r in out]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise RuleError(f"duplicate rule ids: {sorted(dup)}")
    return out


def match(chart, rules: Iterable[Rule] | None = None, applies_to: Iterable[str] = ("natal", "both")) -> list[dict]:
    """Return the rules that fire on this chart, in rule-id order, each with citations and evidence."""
    rules = list(rules) if rules is not None else load_rules()
    f = Facts.from_chart(chart)
    fired = []
    for r in sorted(rules, key=lambda r: r.rule_id):
        if r.data.get("applies_to") not in applies_to:
            continue
        ev: list[str] = []
        if evaluate(r.condition, f, ev):
            fired.append(dict(rule_id=r.rule_id, title=r.data.get("title"), topic=r.data.get("topic"),
                              citations=r.data.get("citations", []), applies_to=r.data.get("applies_to"),
                              effect_en=r.data.get("effect_en"), safety_flags=r.data.get("safety_flags", []),
                              evidence=ev))
    return fired
