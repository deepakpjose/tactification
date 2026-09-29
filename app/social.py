"""
Fetches YouTube subscriber counts for tracked clubs and stores a snapshot
for the current (year, month). Triggered on demand from the admin
dashboard -- see app/auth/views.py:refresh_social_media.
"""
import logging
from datetime import datetime

import requests

from app import app, db
from app.models import Club, YoutubeFollowerStat

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/channels"


def _fetch_channel_stats(handle, channel_id):
    params = {"part": "statistics", "key": app.config["YOUTUBE_API_KEY"]}
    if channel_id:
        params["id"] = channel_id
    elif handle:
        params["forHandle"] = handle
    else:
        return None

    response = requests.get(YOUTUBE_API_URL, params=params, timeout=10)
    response.raise_for_status()
    items = response.json().get("items") or []
    if not items:
        return None

    item = items[0]
    return {
        "channel_id": item["id"],
        "subscriber_count": int(item["statistics"]["subscriberCount"]),
    }


def refresh_all_clubs():
    """
    Fetches current subscriber counts for every tracked club and
    upserts a YoutubeFollowerStat row for this year/month.
    Returns {"updated": int, "failed": [(club_name, reason), ...]}.
    """
    if not app.config.get("YOUTUBE_API_KEY"):
        raise RuntimeError("YOUTUBE_API_KEY is not configured")

    now = datetime.utcnow()
    year, month = now.year, now.month
    updated = 0
    failed = []

    for club in Club.query.all():
        if not club.youtube_handle and not club.youtube_channel_id:
            failed.append((club.name, "no youtube handle/channel id on file"))
            continue

        try:
            stats = _fetch_channel_stats(club.youtube_handle, club.youtube_channel_id)
        except requests.RequestException as exc:
            logging.warning("YouTube fetch failed for %s: %s", club.name, exc)
            failed.append((club.name, str(exc)))
            continue

        if stats is None:
            failed.append((club.name, "no data returned"))
            continue

        if not club.youtube_channel_id:
            club.youtube_channel_id = stats["channel_id"]

        snapshot = YoutubeFollowerStat.query.filter_by(
            club_id=club.id, year=year, month=month
        ).first()
        if snapshot is None:
            snapshot = YoutubeFollowerStat(club_id=club.id, year=year, month=month)
            db.session.add(snapshot)
        snapshot.subscriber_count = stats["subscriber_count"]
        snapshot.fetched_at = now

        # Commit per club rather than batching one commit at the end --
        # this refresh makes ~100 sequential network calls, and holding a
        # single open transaction for all of it holds SQLite's write lock
        # the whole time, blocking unrelated writes (e.g. page visit
        # counters) elsewhere in the app until they time out.
        db.session.commit()
        updated += 1

    return {"updated": updated, "failed": failed}
