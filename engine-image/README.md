# engine-image

Docker image recipe for the LagnaLab calculation service (image `lagnalab-engine:<sha>`).

## Build context

```sh
engine-image/make-context.sh /tmp/ctx-<sha>     # run from the repo root
docker build -t lagnalab-engine:<sha> /tmp/ctx-<sha>
```

This copies the recipe plus `src/lagnalab_engine/` (as `lagnalab_engine/`) and its
`ephe/` Swiss Ephemeris files (as `ephe/`). The image runs as an unprivileged user, listens
on port 8000, and keeps its geocode cache in `/data`. No secrets are needed to build or run it.

`requirements-runtime.txt` pins the runtime subset of the root `requirements.txt`
(no test dependencies). Keep the two in step when a runtime pin changes.
