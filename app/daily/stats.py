"""
Totals for each daily puzzle: how many started, won and lost, and the
average number of guesses for a win. Stored as counters in DailyStats.

The counters are bumped with a single SQL statement each ("insert the row,
or add 1 if it's there"), so two players finishing at the same moment can't
overwrite each other's count.
"""
from sqlalchemy.dialects.sqlite import insert

from app import db
from app.models import DailyStats

COUNTERS = ("started", "won", "lost", "won_guesses")


def _bump(puzzle, **amounts):
    values = {name: amounts.get(name, 0) for name in COUNTERS}
    statement = insert(DailyStats).values(puzzle_id=puzzle.id, **values)
    statement = statement.on_conflict_do_update(
        index_elements=[DailyStats.puzzle_id],
        set_={name: getattr(DailyStats, name) + amount for name, amount in amounts.items()},
    )
    db.session.execute(statement)
    db.session.commit()


def record_start(puzzle):
    """A player's first valid guess on this puzzle."""
    _bump(puzzle, started=1)


def record_finish(puzzle, won, guesses):
    """A game ended: solved in `guesses`, or out of guesses."""
    if won:
        _bump(puzzle, won=1, won_guesses=guesses)
    else:
        _bump(puzzle, lost=1)


def summarise(puzzles):
    """{puzzle.id: totals} for the given puzzles; zeros for a puzzle nobody has played."""
    ids = [puzzle.id for puzzle in puzzles]
    rows = {row.puzzle_id: row for row in DailyStats.query.filter(DailyStats.puzzle_id.in_(ids))} if ids else {}
    summary = {}
    for puzzle in puzzles:
        row = rows.get(puzzle.id)
        started, won, lost, won_guesses = (row.started, row.won, row.lost, row.won_guesses) if row else (0, 0, 0, 0)
        summary[puzzle.id] = {
            "started": started,
            "won": won,
            "lost": lost,
            "unfinished": max(started - won - lost, 0),
            "win_rate": round(100 * won / started) if started else None,
            "average": round(won_guesses / won, 1) if won else None,
        }
    return summary
