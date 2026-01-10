import os
import sys
from flask_migrate import Migrate, init, migrate, upgrade
from app import create_app, db

"""
This script applies model changes using Flask-Migrate.
It initializes the migrations repo if missing, then runs migrate + upgrade.
"""

app = create_app()
migrate_ext = Migrate(app, db)


def ensure_repo():
    if not os.path.isdir("migrations"):
        init()


def main():
    message = sys.argv[1] if len(sys.argv) > 1 else "auto migration"
    with app.app_context():
        ensure_repo()
        migrate(message=message)
        upgrade()


if __name__ == "__main__":
    main()
