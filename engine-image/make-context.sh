#!/usr/bin/env sh
# Assemble the engine-dev Docker build context from this repo.
# Usage: engine-image/make-context.sh <out-dir>   (run from the repo root)
# Layout matches the context used for lagnalab-engine builds since 9 Nov 2026:
#   Dockerfile, .dockerignore, requirements-runtime.txt, ephe/, lagnalab_engine/
set -eu
out="${1:?usage: engine-image/make-context.sh <out-dir>}"
mkdir -p "$out"
cp engine-image/Dockerfile engine-image/.dockerignore engine-image/requirements-runtime.txt "$out"/
cp -R src/lagnalab_engine "$out"/lagnalab_engine
cp -R src/lagnalab_engine/ephe "$out"/ephe
find "$out" -name __pycache__ -type d -prune -exec rm -rf {} +
echo "context ready: $out"
