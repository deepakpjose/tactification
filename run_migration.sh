#!/usr/bin/env bash
set -euo pipefail

# Applies a Flask-Migrate schema migration to a running container.
# Usage: ./run_migration.sh "describe the schema change" [container_name]
#
# migrations/ is not in the persisted volume, so it gets regenerated from
# scratch every time the container is recreated -- but the DB's
# alembic_version marker IS persisted. If a previous run's migration
# history no longer exists on disk, Alembic can't resolve "upgrade from
# <stale revision>" and fails with "Can't locate revision identified by
# '...'". This script detects that specific failure and offers to clear
# just that bookkeeping table (never touches app data) before retrying.

message=${1:?"Usage: $0 \"migration message\" [container_name]"}
container=${2:-tactification-live}

run_migration() {
    docker exec "$container" bash -c "cd /var/www && python db_migrate.py '${message}'"
}

echo "Running migration in container '${container}': ${message}"
if output=$(run_migration 2>&1); then
    echo "$output"
    echo "Migration applied successfully."
    exit 0
fi

echo "$output"

if echo "$output" | grep -q "Can't locate revision"; then
    echo
    echo "Detected a stale alembic_version marker (migration history was lost"
    echo "on a previous container recreation, but the DB still references it)."
    read -r -p "Clear the alembic_version bookkeeping table and retry? [y/N] " reply
    if [[ "$reply" =~ ^[Yy]$ ]]; then
        docker exec "$container" python3 -c "
import sqlite3
con = sqlite3.connect('/var/www/app/docs/tactification.data.sqlite')
try:
    con.execute('drop table alembic_version')
    con.commit()
    print('Dropped alembic_version.')
except sqlite3.OperationalError as exc:
    print('Nothing to drop:', exc)
"
        docker exec "$container" rm -rf /var/www/migrations
        echo "Retrying migration..."
        run_migration
        echo "Migration applied successfully."
        exit 0
    else
        echo "Aborted. No changes made."
        exit 1
    fi
else
    echo "Migration failed for a different reason -- see output above."
    exit 1
fi
