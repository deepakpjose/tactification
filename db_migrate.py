"""
Brings the database schema up to date with the models, using Flask-Migrate.
Run inside the container (docker_migrate.sh calls it):

    python3 db_migrate.py "describe the change"          # asks before risky steps
    python3 db_migrate.py "describe the change" --yes    # no questions

Why it starts from a fresh history every time: migrations/ lives inside the
container and is lost whenever the container is recreated, but the database
(on the persisted volume) remembers the last revision in alembic_version.
Alembic then fails with "Can't locate revision identified by '...'". So this
script:

  1. backs up the database (SQLite's own backup, safe while the site runs)
     and keeps the newest few backups;
  2. drops alembic_version (only the revision marker, never app data) and
     removes the old migrations/;
  3. generates a migration by comparing the models with the real database;
  4. prints what upgrade() will do, and stops to ask if it drops or alters
     anything -- that would mean the database has something the code
     doesn't, and applying could delete data;
  5. applies it.
"""
import contextlib
import glob
import io
import os
import re
import shutil
import sqlite3
import sys
import time

from flask_migrate import Migrate, init, migrate, upgrade

from app import create_app, db

KEEP_BACKUPS = 5
# Operations that can lose data. Creating tables, columns and indexes is safe.
RISKY = re.compile(r"\b(drop_table|drop_column|alter_column|drop_constraint)\b")

app = create_app()
Migrate(app, db)


def database_path():
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if not uri.startswith("sqlite:///"):
        sys.exit("Only SQLite is supported by this script (got {:s}).".format(uri.split(":")[0]))
    return uri[len("sqlite:///"):]


def back_up(path):
    target = "{:s}.bak.{:s}".format(path, time.strftime("%Y%m%d%H%M%S"))
    source, copy = sqlite3.connect(path), sqlite3.connect(target)
    with copy:
        source.backup(copy)
    source.close()
    copy.close()
    # Keep only the newest few, so backups don't fill the volume.
    for old in sorted(glob.glob(path + ".bak.*"))[:-KEEP_BACKUPS]:
        os.remove(old)
    print("1. Backed up the database to {:s}".format(target))


def reset_history(path):
    connection = sqlite3.connect(path)
    with connection:
        connection.execute("DROP TABLE IF EXISTS alembic_version")
    connection.close()
    shutil.rmtree("migrations", ignore_errors=True)
    print("2. Cleared the old migration history (alembic_version and migrations/)")


def upgrade_steps():
    """The operations in the generated migration's upgrade(), one per line."""
    files = glob.glob("migrations/versions/*.py")
    if not files:
        return []
    source = open(files[0], encoding="utf-8").read()
    body = source.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]
    return [line.strip() for line in body.splitlines() if "op." in line]


def confirmed(steps, assume_yes):
    risky = [step for step in steps if RISKY.search(step)]
    if not risky:
        return True
    print("\n   WARNING: these steps can delete or change existing data:")
    for step in risky:
        print("     " + step)
    if assume_yes:
        print("   Applying anyway (--yes).")
        return True
    if not sys.stdin.isatty():
        print("   Not applied. Run it in a terminal to confirm, or pass --yes.")
        return False
    answer = input("   Apply anyway? Only if you expected these. [y/N] ")
    return answer.strip().lower() == "y"


def main():
    args = [arg for arg in sys.argv[1:] if arg != "--yes"]
    message = args[0] if args else "auto migration"
    assume_yes = "--yes" in sys.argv[1:]

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    path = database_path()
    with app.app_context():
        back_up(path)
        reset_history(path)

        # init() prints a page of setup noise, including a misleading
        # "Please edit configuration" line; nothing needs editing.
        with contextlib.redirect_stdout(io.StringIO()):
            init()
        migrate(message=message)
        steps = upgrade_steps()
        print("\n3. Generated migration. upgrade() will:")
        for step in steps or ["(nothing: the database already matches the models)"]:
            print("     " + step)

        if not confirmed(steps, assume_yes):
            sys.exit(1)

        upgrade()
        print("\n4. Done. The database matches the models.")


if __name__ == "__main__":
    main()
