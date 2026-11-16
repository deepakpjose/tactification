"""
The admin form for writing a puzzle. The validators enforce the rules from
.claude/skills/daily-puzzle/SKILL.md that a form can check: answer length,
letters only, at least one source URL, no two puzzles on the same day.
Whether the facts are *true* is for the person approving to check.
"""
from urllib.parse import urlparse

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, StringField, SubmitField, TextAreaField
from wtforms import ValidationError, validators

from app.models import FactPuzzle
from . import game


class FactPuzzleForm(FlaskForm):
    answer = StringField(
        "Answer (what players type)",
        [validators.DataRequired()],
        description="A surname, coach, club, country, stadium, nickname: anything in football. "
                    "Accents and spaces are removed automatically: \"Mac Allister\" is saved as MACALLISTER.",
    )
    display = StringField(
        "Display name",
        [validators.DataRequired(), validators.Length(max=64)],
        description="Shown when the puzzle ends, with accents, e.g. \"Pelé\".",
    )
    topic = StringField(
        "Topic",
        [validators.DataRequired(), validators.Length(max=24)],
        description="What kind of answer it is, shown as a label: \"Player\", \"Coach\", \"Club\", \"Stadium\"...",
    )
    fact_1 = TextAreaField(
        "Fact 1 (unlocks after 2 guesses)",
        [validators.DataRequired(), validators.Length(max=300)],
        render_kw={"rows": 2},
        description="The surprising one. First person, and it mustn't give the answer away.",
    )
    fact_2 = TextAreaField(
        "Fact 2 (unlocks after 4 guesses)",
        [validators.DataRequired(), validators.Length(max=300)],
        render_kw={"rows": 2},
        description="More identifying, so a football fan can usually solve it from here.",
    )
    sources = TextAreaField(
        "Sources",
        [validators.DataRequired()],
        render_kw={"rows": 2},
        description="One URL per line. Shown as \"Read more\" links when the puzzle ends.",
    )
    approved = BooleanField(
        "Approved: I've checked every fact against the sources",
        description="Only approved puzzles can run. Unticking also clears the date.",
    )
    day = DateField(
        "Run on (optional)",
        [validators.Optional()],
        description="Leave empty to join the queue, and the next free day picks it up. "
                    "Set a date to pin it, e.g. for an anniversary.",
    )
    submit = SubmitField("Save puzzle")

    def __init__(self, *args, puzzle_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Remembered so the date check below can ignore the puzzle's own row.
        self.puzzle_id = puzzle_id

    def validate_answer(self, field):
        cleaned = game.normalise(field.data)
        if not game.MIN_LENGTH <= len(cleaned) <= game.MAX_LENGTH:
            raise ValidationError("Must be {:d} to {:d} letters once accents and spaces are removed "
                                  "(this is {:d}).".format(game.MIN_LENGTH, game.MAX_LENGTH, len(cleaned)))
        field.data = cleaned

    def validate_sources(self, field):
        lines = [line.strip() for line in field.data.splitlines() if line.strip()]
        for line in lines:
            parts = urlparse(line)
            if parts.scheme not in ("http", "https") or not parts.netloc:
                raise ValidationError("Not a web address: {:s}".format(line))
        field.data = "\n".join(lines)

    def validate_day(self, field):
        if field.data is None:
            return
        if not self.approved.data:
            raise ValidationError("Approve the puzzle before giving it a date.")
        taken = FactPuzzle.query.filter(FactPuzzle.day == field.data, FactPuzzle.id != self.puzzle_id).first()
        if taken:
            raise ValidationError("{:s} is already set for that day.".format(taken.display))
