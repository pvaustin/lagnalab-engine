# LagnaLab calculation service

This is the source code of the astrology calculation service behind [LagnaLab](https://lagnalab.com),
published by **TuskerMind LLC**. It computes Vedic (sidereal) birth charts and daily timings:

- `POST /chart`: planets, Lagna, houses (whole sign), nakshatras, vargas (D1-D60), Gulika/Mandi,
  birth panchanga and Vimshottari dasha periods
- `POST /horoscope`: the chart plus rule-based facts (vargottama, yogakaraka, yogas, doshas)
- `GET /timings`: one civil day's sunrise, sunset, panchanga and daily periods for a place
- `GET /health`

Positions come from the [Swiss Ephemeris](https://www.astro.com/swisseph/) by Astrodienst AG
(via [pyswisseph](https://github.com/astrorigin/pyswisseph)), Lahiri ayanamsa by default.
Conventions and their sources are in [docs/METHODS.md](docs/METHODS.md).

## Layout

```
src/lagnalab_engine/   the service (FastAPI); ephe/ = Swiss Ephemeris data files, 1800-2400
tests/engine/          unit, API and golden tests (PyJHora, JPL Horizons, published panchanga pages)
engine-image/          Docker image recipe (Dockerfile, runtime requirements, build-context script)
docs/                  METHODS.md (conventions), GOLDEN_REPORT.md, sources/
```

## Run locally

Python 3.12 or later. `pyswisseph` builds from source where no wheel exists, so install Python
headers and a C/C++ compiler first (Debian/Ubuntu: `apt-get install python3-dev g++`).

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                      # tests
uvicorn --app-dir src lagnalab_engine.api:app --port 8000
```

Example:

```bash
curl -s localhost:8000/chart -H 'content-type: application/json' -d '{
  "date": "2000-01-01", "time": "10:00:00", "tz": "Asia/Kolkata",
  "place": {"name": "Kochi", "lat": 9.9312, "lon": 76.2673}}'
```

When `place` has a name but no coordinates, the service looks it up with OpenStreetMap Nominatim
and caches the result (`LAGNALAB_GEOCODE_CACHE`).

## Build the Docker image

```bash
engine-image/make-context.sh /tmp/ctx
docker build -t lagnalab-engine /tmp/ctx
docker run -p 8000:8000 -v lagnalab-data:/data lagnalab-engine
```

The image contains `lagnalab_engine/` and the `ephe/` data files only. See
[engine-image/README.md](engine-image/README.md).

## Licence

Copyright (C) 2026 TuskerMind LLC.

This program is free software: you can redistribute it and/or modify it under the terms of the
GNU Affero General Public License as published by the Free Software Foundation, version 3 of the
License. It is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
[LICENSE](LICENSE) for the full text.

If you run a modified version of this program as a network service, the AGPL requires you to offer
its users the corresponding source code.

This program uses the Swiss Ephemeris by Astrodienst AG, Zurich, Switzerland, under the GNU Affero
General Public License (AGPL), version 3: <https://www.astro.com/swisseph/>. The Swiss Ephemeris
data files in `src/lagnalab_engine/ephe/` are covered by the same licence. See [NOTICE](NOTICE) for
all third-party credits.

This repository is a published copy of the service code that runs LagnaLab. Each deployed version
of the service is published here.
