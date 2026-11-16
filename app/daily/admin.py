"""
Admin pages for the daily puzzle (administrators only).

  GET       /daily/admin               every puzzle, grouped by where it is in
                                       its lifecycle (see FactPuzzle)
  GET/POST  /daily/admin/new           write a puzzle
  GET/POST  /daily/admin/<id>/edit     check, fix and approve a puzzle
  POST      /daily/admin/<id>/delete   remove a puzzle that hasn't run yet

The weekly routine: draft or import a batch (they arrive unapproved), open
each one, check its facts against the sources, tick Approved and save.
Approved puzzles join the queue and run one a day.
"""
from datetime import timedelta

from flask import abort, flash, redirect, render_template, url_for
from flask_login import login_required

from app import db
from app.auth.decorators import admin_required
from app.models import FactPuzzle
from . import daily, schedule
from .forms import FactPuzzleForm


def _queue_dates(queued, from_day):
    """
    Works out which day each queued puzzle will run, so the admin page can
    show it: the next days from `from_day` on that no pinned puzzle has
    taken. These are a forecast -- nothing is saved until the day comes.
    """
    taken = {day for (day,) in db.session.query(FactPuzzle.day).filter(FactPuzzle.day >= from_day)}
    dates, day = [], from_day
    for _ in queued:
        while day in taken:
            day += timedelta(days=1)
        dates.append(day)
        day += timedelta(days=1)
    return dates


@daily.route("/admin", methods=["GET"])
@login_required
@admin_required
def admin():
    today = schedule.today()
    todays = FactPuzzle.query.filter_by(day=today, approved=True).first()
    pinned = (FactPuzzle.query.filter(FactPuzzle.approved.is_(True), FactPuzzle.day > today)
              .order_by(FactPuzzle.day).all())
    queued = (FactPuzzle.query.filter_by(approved=True, day=None)
              .order_by(FactPuzzle.created_at, FactPuzzle.id).all())
    drafts = FactPuzzle.query.filter_by(approved=False).order_by(FactPuzzle.created_at).all()
    past = (FactPuzzle.query.filter(FactPuzzle.day < today)
            .order_by(FactPuzzle.day.desc()).limit(30).all())

    # If nothing has claimed today yet, the first queued puzzle will.
    first_free = today if todays is None else today + timedelta(days=1)
    return render_template(
        "daily/admin.html",
        today=today,
        todays=todays,
        pinned=pinned,
        queue=list(zip(queued, _queue_dates(queued, first_free))),
        drafts=drafts,
        past=past,
    )


def _save(puzzle, form):
    form.populate_obj(puzzle)
    if not puzzle.approved:
        # A draft can't hold a date, or it would block that day for others.
        puzzle.day = None
    db.session.add(puzzle)
    db.session.commit()


@daily.route("/admin/new", methods=["GET", "POST"])
@login_required
@admin_required
def admin_new():
    form = FactPuzzleForm()
    if form.validate_on_submit():
        puzzle = FactPuzzle()
        _save(puzzle, form)
        flash("Saved {:s} ({:s}).".format(puzzle.display, "approved" if puzzle.approved else "draft"))
        return redirect(url_for("daily.admin"))
    return render_template("daily/edit.html", form=form, puzzle=None, today=schedule.today())


@daily.route("/admin/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edit(id):
    puzzle = FactPuzzle.query.get_or_404(id)
    form = FactPuzzleForm(obj=puzzle, puzzle_id=puzzle.id)
    if form.validate_on_submit():
        _save(puzzle, form)
        flash("Saved {:s} ({:s}).".format(puzzle.display, "approved" if puzzle.approved else "draft"))
        return redirect(url_for("daily.admin"))
    return render_template("daily/edit.html", form=form, puzzle=puzzle, today=schedule.today())


@daily.route("/admin/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete(id):
    puzzle = FactPuzzle.query.get_or_404(id)
    if puzzle.day is not None and puzzle.day <= schedule.today():
        # Players may have shared results for it; deleting would renumber
        # every later puzzle.
        abort(400, "A puzzle that has already run can't be deleted.")
    db.session.delete(puzzle)
    db.session.commit()
    flash("Deleted {:s}.".format(puzzle.display))
    return redirect(url_for("daily.admin"))
