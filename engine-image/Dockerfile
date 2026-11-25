# syntax=docker/dockerfile:1
# LagnaLab chart engine. Multi-stage: compile wheels (pyswisseph has no py3.12 Linux wheel,
# none at all for arm64) in a build stage, ship a lean runtime. Works on amd64 and arm64.
ARG PY=3.12
# Full python image already ships gcc/g++/make and Python headers (= build-essential + python3-dev),
# so no apt step is needed (also avoids apt-mirror flakiness).
FROM python:${PY}-bookworm AS build
WORKDIR /src
COPY requirements-runtime.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements-runtime.txt

FROM python:${PY}-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    LAGNALAB_EPHE_PATH=/app/ephe \
    LAGNALAB_GEOCODE_CACHE=/data/geocode.json
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir --no-index /wheels/*.whl && rm -rf /wheels \
    && useradd -r -u 10001 -d /app lagna && mkdir -p /data && chown lagna /data
WORKDIR /app
COPY ephe/ ./ephe/
COPY lagnalab_engine/ ./lagnalab_engine/
USER lagna
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=4).status==200 else 1)"
CMD ["uvicorn", "lagnalab_engine.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
