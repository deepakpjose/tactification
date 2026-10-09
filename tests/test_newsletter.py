from datetime import datetime, timedelta

from app import db
from app.models import NewsletterSubscriber
from app.newsletter.purge import purge_pending_subscribers


def _subscriber(email, confirmed, age_hours, now):
    return NewsletterSubscriber(
        email=email,
        token=NewsletterSubscriber.generate_token(),
        confirmed=confirmed,
        created_at=now - timedelta(hours=age_hours),
    )


def test_purge_removes_only_stale_pending(app_instance):
    now = datetime.utcnow()
    with app_instance.app_context():
        db.session.add_all([
            _subscriber("stale@example.com", False, 49, now),
            _subscriber("fresh@example.com", False, 47, now),
            _subscriber("confirmed@example.com", True, 24 * 30, now),
        ])
        db.session.commit()

        assert purge_pending_subscribers(now=now) == 1

        remaining = {s.email for s in NewsletterSubscriber.query.all()}
        assert remaining == {"fresh@example.com", "confirmed@example.com"}


def test_resubscribe_restarts_pending_window(client, app_instance, monkeypatch):
    monkeypatch.setattr("app.newsletter.views.send_email", lambda **kwargs: None)
    now = datetime.utcnow()
    with app_instance.app_context():
        db.session.add(_subscriber("again@example.com", False, 72, now))
        db.session.commit()

    client.post("/newsletter/subscribe", data={"email": "again@example.com"})

    with app_instance.app_context():
        assert purge_pending_subscribers() == 0
        assert NewsletterSubscriber.query.filter_by(email="again@example.com").count() == 1


def test_purge_removes_pending_with_no_created_at(app_instance):
    with app_instance.app_context():
        sub = _subscriber("legacy@example.com", False, 0, datetime.utcnow())
        db.session.add(sub)
        db.session.commit()
        sub.created_at = None
        db.session.commit()

        assert purge_pending_subscribers() == 1
        assert NewsletterSubscriber.query.count() == 0
