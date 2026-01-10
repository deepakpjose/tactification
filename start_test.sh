#!/usr/bin/env bash
set -euo pipefail

app="docker.tactification"
SECRET_KEY=${SECRET_KEY:-${1:-change-me}}

# Build test image (installs test deps and includes tests directory).
docker build -f Dockerfile.test --build-arg SECRET_KEY="${SECRET_KEY}" -t "${app}:test" .

# Test container runs pytest only; no volumes are mounted so data is ephemeral.
docker run --rm --name tactification-test \
  --entrypoint "" \
  -e SECRET_KEY="${SECRET_KEY}" \
  "${app}:test" python -m pytest /var/www/tests
