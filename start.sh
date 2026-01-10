#!/usr/bin/env bash
set -euo pipefail

app="docker.tactification"

# Build the image (same steps as start.sh)
docker build --build-arg SECRET_KEY=$1 -t ${app} .

# Dev container keeps volume-mounted uploads/db for persistence.
docker run -d -p 80:80 -v insidecode:/var/www/app/docs ${app}
