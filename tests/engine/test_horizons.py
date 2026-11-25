"""Independent check of planetary positions against NASA/JPL Horizons (stored, with query URLs)."""
import json
import os

import pytest
import swisseph as swe

from golden_compare import GOLDEN, angdiff, engine_chart, load

H = json.load(open(os.path.join(GOLDEN, "horizons", "horizons_expected.json")))
INPUTS = {c["id"]: c for c in load()[0]}


@pytest.mark.parametrize("cid", sorted(H["tropical_longitude"]))
def test_tropical_longitudes_match_horizons(cid):
    ch = engine_chart(INPUTS[cid])
    assert abs(ch.time.julian_day_ut - H["jd_ut"][cid]) < 1e-9
    # sidereal = tropical(apparent, of date) - ayanamsa; Swiss reports the ayanamsa including nutation
    ayan = ch.meta.ayanamsa_deg
    for g in ch.grahas:
        if g.name in H["tropical_longitude"][cid]:
            trop = (g.longitude + ayan) % 360
            dv = angdiff(trop, H["tropical_longitude"][cid][g.name]) * 3600
            assert dv < 1.0, f"{cid} {g.name} differs from Horizons by {dv:.3f} arcsec"
