"""
Tactification Daily: the fact-clue name-guessing puzzle.

How the pieces fit together:
  game.py      -- the rules (letter colours, guess limits, when facts unlock).
                  Plain functions with no database, so they're easy to test.
  schedule.py  -- which puzzle runs on which day.
  views.py     -- the public page (/daily) and the guess endpoint the page's
                  JavaScript calls (/daily/guess).
  admin.py     -- pages for writing, approving and scheduling puzzles
                  (/daily/admin), for administrators only.
  forms.py     -- the admin puzzle form and its validation.

The rules themselves are written up in .claude/skills/daily-puzzle/SKILL.md;
keep the code and that file in step.
"""
from flask import Blueprint

daily = Blueprint("daily", __name__)  # pylint: disable=invalid-name

from . import views, admin  # noqa: E402,F401  (registers the routes)
