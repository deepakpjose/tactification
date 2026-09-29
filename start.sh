#!/usr/bin/env bash
set -euo pipefail

app="techtok_tactification"

# Usage: ./start.sh <SECRET_KEY> [YOUTUBE_API_KEY]
youtube_api_key=${2:-}

# Build the image (same steps as start.sh)
docker build --build-arg SECRET_KEY=$1 --build-arg YOUTUBE_API_KEY="${youtube_api_key}" -t ${app} .

# Dev container keeps volume-mounted uploads/db for persistence.
docker run -d -p 80:80 -v insidecode:/var/www/app/docs ${app}
