"""
Public routes for the daily puzzle.

  GET  /daily/          the game page
  POST /daily/guess     the page's JavaScript sends each guess here
  GET  /daily/archive   past puzzles with their answers and facts, newest first

The answer never leaves the server until the game is over. The browser only
ever receives `public_state()`: the colours of each guess, whichever facts are
unlocked, and the full reveal once the game ends.

A player's guesses are kept in Flask's session cookie. Flask signs that cookie
with SECRET_KEY, so a player can't edit it to fake earlier guesses, and a page
refresh carries on where they left off. It lasts until the browser closes;
clearing cookies starts the day's puzzle over, as in other daily word games.
"""
from flask import jsonify, render_template, request, session

from app.main.views import _record_static_visit
from app.models import FactPuzzle
from . import daily, game, schedule, stats

ARCHIVE_PER_PAGE = 10

SESSION_KEY = "daily_puzzle"


def _saved_guesses(puzzle):
    """This player's guesses for `puzzle`, or [] if they last played another day."""
    saved = session.get(SESSION_KEY) or {}
    if saved.get("day") != puzzle.day.isoformat():
        return []
    return list(saved.get("guesses", []))


def _save_guesses(puzzle, guesses):
    # Only today's guesses are kept; yesterday's are simply overwritten.
    session[SESSION_KEY] = {"day": puzzle.day.isoformat(), "guesses": guesses}


def public_state(puzzle, guesses):
    """
    Everything the page needs to draw the game, and nothing that gives away
    the answer early. The page redraws itself entirely from this after each
    guess, so the server is the only place the rules are applied.
    """
    answer = puzzle.answer
    over = game.is_over(guesses, answer)
    state = {
        "number": schedule.puzzle_number(puzzle),
        "length": len(answer),
        "max_guesses": game.max_guesses(answer),
        "topic": puzzle.topic,
        # Only the facts unlocked so far are sent.
        "facts": puzzle.facts()[:game.facts_unlocked(len(guesses), over)],
        "fact_unlock_after": list(game.FACT_UNLOCK_AFTER),
        "rows": [{"guess": g, "marks": game.score(g, answer)} for g in guesses],
        "over": over,
        "won": over and guesses[-1] == answer,
    }
    if over:
        state["reveal"] = {
            "display": puzzle.display,
            "facts": puzzle.facts(),
            "sources": puzzle.source_list(),
        }
    return state


@daily.route("/", methods=["GET"])
def play():
    visit_count = _record_static_visit("daily")
    puzzle = schedule.puzzle_for(schedule.today())
    state = public_state(puzzle, _saved_guesses(puzzle)) if puzzle else None
    return render_template("daily/play.html", state=state, visit_count=visit_count)


@daily.route("/guess", methods=["POST"])
def guess():
    puzzle = schedule.puzzle_for(schedule.today())
    if puzzle is None:
        return jsonify(error="There's no puzzle today. Check back tomorrow."), 404

    guesses = _saved_guesses(puzzle)
    if game.is_over(guesses, puzzle.answer):
        return jsonify(error="You've finished today's puzzle. A new one is up at midnight UTC.",
                       state=public_state(puzzle, guesses)), 409

    payload = request.get_json(silent=True)
    raw = payload.get("guess") if isinstance(payload, dict) else None
    # Anything but text (a number, a list...) counts as an empty guess, which
    # check_guess refuses like any other wrong-length guess.
    attempt = game.normalise(raw if isinstance(raw, str) else "")
    error = game.check_guess(attempt, puzzle.answer)
    if error:
        # A guess that can't be played isn't counted.
        return jsonify(error=error, state=public_state(puzzle, guesses)), 400

    guesses.append(attempt)
    _save_guesses(puzzle, guesses)
    # Totals for the admin page. Each is counted once per game: the first
    # valid guess starts it, and any guess after the end is refused above.
    if len(guesses) == 1:
        stats.record_start(puzzle)
    if game.is_over(guesses, puzzle.answer):
        stats.record_finish(puzzle, won=guesses[-1] == puzzle.answer, guesses=len(guesses))
    return jsonify(state=public_state(puzzle, guesses))


@daily.route("/archive", methods=["GET"])
def archive():
    """
    Every puzzle that has already run, newest first, 10 to a page. Today's
    puzzle is left out until tomorrow so the archive can't spoil it.
    """
    page = request.args.get("page", 1, type=int)
    pagination = (FactPuzzle.query
                  .filter(FactPuzzle.approved.is_(True), FactPuzzle.day.isnot(None),
                          FactPuzzle.day < schedule.today())
                  .order_by(FactPuzzle.day.desc())
                  .paginate(page=page, per_page=ARCHIVE_PER_PAGE, error_out=False))
    # Puzzle numbers count up from the first day, so on a newest-first list
    # they count down from the total. Same numbers as schedule.puzzle_number().
    first = pagination.total - (pagination.page - 1) * ARCHIVE_PER_PAGE
    puzzles = [(first - i, puzzle) for i, puzzle in enumerate(pagination.items)]
    return render_template("daily/archive.html", puzzles=puzzles, pagination=pagination)
