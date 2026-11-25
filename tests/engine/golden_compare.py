"""Compare engine output with the stored PyJHora reference (tests/golden/pyjhora_expected.json).

Shared by tests/test_golden_pyjhora.py and tools/golden_report.py. Tolerances are M1 exit
criterion (b): longitudes <= 1 arcmin; lagna sign, nakshatra and tithi exact; dasha dates <= 1 day.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone

from lagnalab_engine.chart import compute_chart
from lagnalab_engine.constants import GRAHAS, RASIS
from lagnalab_engine.schema import ChartRequest

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, "golden")
ARCMIN = 1 / 60
FIXED_TRANSIT = datetime(2026, 10, 20, tzinfo=timezone.utc)


def load():
    inputs = json.load(open(os.path.join(GOLDEN, "inputs.json")))["charts"]
    ref = json.load(open(os.path.join(GOLDEN, "pyjhora_expected.json")))
    return inputs, ref


def engine_chart(c, **settings):
    req = ChartRequest(date=c["date"], time=c["time"], place={"name": c["city"], "lat": c["lat"], "lon": c["lon"]},
                       tz=c["tz"], transit_at=FIXED_TRANSIT, settings=settings)
    return compute_chart(req)


def angdiff(a, b):
    return abs((a - b + 180) % 360 - 180)


class Tally:
    def __init__(self):
        self.n = defaultdict(int)
        self.fail = defaultdict(list)
        self.maxdev = defaultdict(float)

    def check(self, field, ok, cid, detail="", dev=None):
        self.n[field] += 1
        if not ok:
            self.fail[field].append(f"{cid}: {detail}")
        if dev is not None:
            self.maxdev[field] = max(self.maxdev[field], dev)


def compare_all(only=None):
    inputs, ref = load()
    res = ref["results"]
    t = Tally()
    info = Tally()  # informational comparisons (known convention differences), not pass/fail gates
    for c in inputs:
        cid = c["id"]
        if only and cid not in only:
            continue
        r = res[cid]
        ch = engine_chart(c)
        jd_local_shift = c["utc_offset_hours"] / 24
        g = {x.name: x for x in ch.grahas}
        for name in GRAHAS:
            dv = angdiff(g[name].longitude, r["longitudes"][name])
            t.check("graha_longitude", dv <= ARCMIN, cid, f"{name} {dv*3600:.2f}\"", dv * 3600)
            t.check("graha_sign", g[name].sign_index - 1 == int(r["longitudes"][name] // 30), cid, name)
        dv = angdiff(ch.lagna.longitude, r["lagna"]["longitude"])
        t.check("lagna_longitude", dv <= ARCMIN, cid, f"{dv*3600:.2f}\"", dv * 3600)
        t.check("lagna_sign", ch.lagna.sign_index - 1 == r["lagna"]["sign"], cid,
                f"{ch.lagna.sign} vs {RASIS[r['lagna']['sign']]}")
        t.check("lagna_nakshatra_pada", (ch.lagna.nakshatra.index, ch.lagna.nakshatra.pada) ==
                (r["lagna"]["nakshatra"], r["lagna"]["pada"]), cid)
        mn = g["Moon"].nakshatra
        t.check("moon_nakshatra", mn.index == r["moon_nakshatra"]["index"], cid,
                f"{mn.index} vs {r['moon_nakshatra']['index']}")
        t.check("moon_pada", mn.pada == r["moon_nakshatra"]["pada"], cid)
        p = ch.panchanga
        t.check("tithi", p.tithi["number"] == r["tithi"], cid, f"{p.tithi['number']} vs {r['tithi']}")
        t.check("yoga_at_birth", p.yoga["number"] == r["yoga_at_birth"], cid,
                f"{p.yoga['number']} vs {r['yoga_at_birth']}")
        t.check("karana_at_birth", p.karana["number"] == r["karana_from_phase_at_birth"], cid,
                f"{p.karana['number']} vs {r['karana_from_phase_at_birth']}")
        info.check("karana_vs_pyjhora_karana_fn", p.karana["number"] == r["karana"], cid,
                   f"{p.karana['number']} vs {r['karana']}")
        info.check("yoga_vs_pyjhora_yogam_fn(sunrise)", p.yoga["number"] == r["yoga_drik_yogam_fn"], cid,
                   f"{p.yoga['number']} vs {r['yoga_drik_yogam_fn']}")
        t.check("vara", p.vara["index"] == r["vaara"], cid, f"{p.vara['index']} vs {r['vaara']}")
        sr_local = p.sunrise_local
        ours_h = sr_local.hour + sr_local.minute / 60 + (sr_local.second + sr_local.microsecond / 1e6) / 3600
        # PyJHora returns sunrise for the civil date; ours is the sunrise of the Vedic day
        if p.vara["civil_weekday"] == p.vara["weekday"]:
            dv = abs(ours_h - r["sunrise_local_hours"]) * 3600
            t.check("sunrise_seconds(<=60s)", dv <= 60, cid, f"{dv:.1f}s", dv)
        retro = {x.name for x in ch.grahas if x.retrograde}
        t.check("retrograde_set", retro == set(r["retrograde"]), cid, f"{sorted(retro)} vs {sorted(r['retrograde'])}")
        for vk, vals in r["vargas"].items():
            for pt, sgn in vals.items():
                ours = ch.lagna.vargas[vk] if pt == "Lagna" else g[pt].vargas[vk]
                t.check(f"varga_{vk}", ours == RASIS[sgn], cid, f"{pt} {ours} vs {RASIS[sgn]}")
        ours_c = sorted(x.name for x in ch.grahas if x.combust)
        info.check("combustion_vs_pyjhora(orb indexing differs)", ours_c == sorted(r["combustion_pyjhora"]), cid,
                   f"{ours_c} vs {sorted(r['combustion_pyjhora'])}")
        # Shipped Gulika is the Prasna Marga ghatika table. This gate checks the
        # selectable start-of-Saturn's-part against PyJHora's begin-of-part longitude.
        gul = next(u for u in engine_chart(c, gulika_point="start").upagrahas if u.name == "Gulika")
        dv = angdiff(gul.longitude, r["gulika_begin_of_saturn_part"])
        key = "gulika_start_day_birth" if p.is_day_birth else "gulika_start_night_birth"
        (t if p.is_day_birth else info).check(key, dv <= ARCMIN, cid, f"{dv*60:.2f}'", dv * 60)
        # Vimshottari bhukti start dates (local JD), first 81 periods
        v = ch.vimshottari
        ours = []
        for m in v.mahadashas:
            for b in m.bhuktis:
                jd_utc = b.start_utc.timestamp() / 86400 + 2440587.5
                ours.append((m.lord, b.lord, jd_utc + jd_local_shift))
        theirs = r["vimshottari_365_25"]["bhuktis"]
        n = min(len(ours), len(theirs))
        t.check("dasha_sequence", [(a, b) for a, b, _ in ours[:n]] == [(x["md"], x["ad"]) for x in theirs[:n]], cid)
        mx = max(abs(ours[i][2] - theirs[i]["start_jd_local"]) for i in range(n))
        t.check("dasha_start_dates(<=1d)", mx <= 1.0, cid, f"{mx:.4f} d", mx)
        t.check("birth_dasha_lord", v.birth_nakshatra_lord == r["vimshottari_first_md"], cid)
        # informational: PyJHora with its own defaults (true positions + true nodes)
        dflt = r["pyjhora_defaults"]
        for name in GRAHAS:
            alt = engine_chart(c, node="true") if name in ("Rahu", "Ketu") else None
            ourv = alt and {x.name: x for x in alt.grahas}[name].longitude or g[name].longitude
            dv = angdiff(ourv, dflt["longitudes"][name])
            info.check(f"defaults_true_positions_{name}", dv <= ARCMIN, cid, f"{dv*3600:.1f}\"", dv * 3600)
    return t, info
