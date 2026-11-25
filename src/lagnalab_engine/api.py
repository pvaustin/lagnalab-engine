"""FastAPI service: POST /chart and GET /timings."""
from datetime import date as Date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from . import __version__
from .chart import compute_chart
from .horoscope import build_horoscope
from .schema import ChartRequest, ChartResponse
from .timings import compute_timings

app = FastAPI(title="LagnaLab chart engine", version=__version__)


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}


@app.get("/timings")
def timings(
    date: Date = Query(..., description="Local civil date, YYYY-MM-DD"),
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    tz: Optional[str] = Query(None, description="IANA time zone; inferred from lat/lon when omitted"),
):
    """Read-only daily timings. The same place and date always return the same body."""
    try:
        return compute_timings(date, lat, lon, tz)
    except (ValueError, LookupError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/chart", response_model=ChartResponse)
def chart(req: ChartRequest):
    try:
        return compute_chart(req)
    except (ValueError, LookupError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/horoscope")
def horoscope(req: ChartRequest):
    """Chart facts plus horoscope_version 1. Does not change POST /chart."""
    try:
        return build_horoscope(compute_chart(req))
    except (ValueError, LookupError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/chart/rules")
def chart_rules(req: ChartRequest):
    """Compute the chart and return the pilot rules that fire on it (deterministic matcher)."""
    from .rules import RuleError, load_rules, match
    try:
        c = compute_chart(req)
        return {"rules_fired": match(c, load_rules())}
    except RuleError as e:
        raise HTTPException(status_code=500, detail=f"rule base: {e}")
    except (ValueError, LookupError) as e:
        raise HTTPException(status_code=422, detail=str(e))
