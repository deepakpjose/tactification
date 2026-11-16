"""
Which puzzle runs on which day.

There's no scheduled job. The first visit of each day calls puzzle_for(today):
  1. If an approved puzzle is already set for that day (pinned from the admin,
     or picked by an earlier visit), that's the one.
  2. Otherwise the oldest approved puzzle without a day is given this day.
     From then on it's fixed, so everyone gets the same puzzle all day.
  3. If the queue is empty there's no puzzle that day, and the page says so.

"Today" is the UTC date, so the puzzle changes at midnight UTC for everyone.
"""
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app import db
from app.models import FactPuzzle


def today():
    return datetime.utcnow().date()


def puzzle_for(day):
    """Returns the approved FactPuzzle for `day`, assigning one if needed, or None."""
    puzzle = FactPuzzle.query.filter_by(day=day, approved=True).first()
    if puzzle is not None:
        return puzzle

    # Take the oldest approved puzzle that has no day yet. Drafts never run,
    # and a puzzle pinned to another date keeps that date.
    queued = (
        FactPuzzle.query.filter_by(approved=True, day=None)
        .order_by(FactPuzzle.created_at, FactPuzzle.id)
        .first()
    )
    if queued is None:
        return None

    queued.day = day
    try:
        db.session.commit()
    except IntegrityError:
        # Two first-visits of the day raced and the other one saved its pick
        # first (day is unique). Use whatever it chose.
        db.session.rollback()
    return FactPuzzle.query.filter_by(day=day, approved=True).first()


def puzzle_number(puzzle):
    """
    The number shown to players, "Tactification Daily #14": how many approved
    puzzles have run up to and including this one's day. Past days never
    change, so a puzzle keeps its number.
    """
    return FactPuzzle.query.filter(
        FactPuzzle.approved.is_(True), FactPuzzle.day.isnot(None), FactPuzzle.day <= puzzle.day,
    ).count()
