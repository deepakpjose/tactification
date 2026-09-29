import csv
import sys

from app import create_app, db
from app.models import Club

"""
One-off/rerunnable seed for the Club table backing /socialmedia.
Reads data/clubs_youtube.csv (league,club_name,youtube_handle,youtube_channel_id)
and upserts by (name, league) -- rerunning just refreshes the handle/channel id
for existing clubs and adds new ones. youtube_channel_id is optional, used to
pin clubs whose forHandle lookup is ambiguous or fails.
"""

app = create_app()


def seed(csv_path):
    added = 0
    updated = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            league = row["league"].strip()
            name = row["club_name"].strip()
            handle = (row.get("youtube_handle") or "").strip() or None
            channel_id = (row.get("youtube_channel_id") or "").strip() or None

            club = Club.query.filter_by(name=name, league=league).first()
            if club is None:
                club = Club(name=name, league=league, youtube_handle=handle, youtube_channel_id=channel_id)
                db.session.add(club)
                added += 1
            elif club.youtube_handle != handle or club.youtube_channel_id != channel_id:
                club.youtube_handle = handle
                club.youtube_channel_id = channel_id
                updated += 1

    db.session.commit()
    return added, updated


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/clubs_youtube.csv"
    with app.app_context():
        added, updated = seed(csv_path)
        print("Added {:d} clubs, updated {:d} clubs.".format(added, updated))


if __name__ == "__main__":
    main()
