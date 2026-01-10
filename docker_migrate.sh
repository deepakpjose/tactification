#!/usr/bin/env bash
set -euo pipefail

# Run inside the container. Optionally pass a message:
# ./docker_migrate.sh "add field to Post"

message=${1:-"auto migration"}

cd /var/www
python db_migrate.py "${message}"
