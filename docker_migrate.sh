#!/usr/bin/env bash
set -euo pipefail

# Run inside the container to bring the database up to date with the models:
#   ./docker_migrate.sh "add field to Post"
#   ./docker_migrate.sh "add field to Post" --yes   # don't ask before risky steps
#
# Backs up the database, works around the lost migration history after a
# container is recreated ("Can't locate revision identified by ..."), shows
# what will change and asks before anything that drops data. Details in
# db_migrate.py.

message=${1:-"auto migration"}
shift || true

cd /var/www
python3 db_migrate.py "${message}" "$@"
