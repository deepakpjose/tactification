from app import create_app
from app.newsletter.purge import purge_pending_subscribers

"""
Deletes newsletter signups left unconfirmed for over 48 hours.
Scheduled once a day by uWSGI's master-process cron (see app.ini);
can also be run by hand inside the container:
    python /var/www/purge_pending_subscribers.py
"""

app = create_app()


if __name__ == "__main__":
    with app.app_context():
        deleted = purge_pending_subscribers()
    app.logger.info("Purged %d pending newsletter subscribers", deleted)
