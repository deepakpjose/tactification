"""
Purges newsletter signups that were never confirmed. Spam bots fill the
subscribe form but never click the double opt-in link, so unconfirmed rows
older than PENDING_MAX_AGE are deleted. Runs once a day via uWSGI cron --
see purge_pending_subscribers.py and app.ini.
"""
from datetime import datetime, timedelta

from sqlalchemy import or_

from app import db
from app.models import NewsletterSubscriber

PENDING_MAX_AGE = timedelta(hours=48)


def purge_pending_subscribers(now=None):
    """
    Deletes unconfirmed subscribers created more than PENDING_MAX_AGE ago.
    Returns the number of rows deleted.
    """
    cutoff = (now or datetime.utcnow()) - PENDING_MAX_AGE
    deleted = NewsletterSubscriber.query.filter(
        NewsletterSubscriber.confirmed.is_(False),
        # NULL created_at only exists on rows predating the column default,
        # so those are well past the window too.
        or_(
            NewsletterSubscriber.created_at < cutoff,
            NewsletterSubscriber.created_at.is_(None),
        ),
    ).delete(synchronize_session=False)
    db.session.commit()
    return deleted
