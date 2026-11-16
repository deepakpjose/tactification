from datetime import date, datetime, timedelta

import pytest

from app import db
from app.daily import game, schedule
from app.models import FactPuzzle, Role, User

DAY = date(2026, 11, 16)


def _puzzle(answer="LINEKER", display="Gary Lineker", approved=True, day=None, created=None, **kwargs):
    fields = dict(
        answer=answer, display=display, topic="Player",
        fact_1="Never booked.", fact_2="1986 Golden Boot.", sources="https://example.com/lineker",
        approved=approved, day=day,
    )
    fields.update(kwargs)
    puzzle = FactPuzzle(**fields)
    if created:
        puzzle.created_at = created
    db.session.add(puzzle)
    db.session.commit()
    return puzzle


@pytest.fixture
def today_is(monkeypatch):
    """Pins schedule.today() so tests don't depend on the real date."""
    def set_day(day):
        monkeypatch.setattr(schedule, "today", lambda: day)
    set_day(DAY)
    return set_day


# ---- Rules (app/daily/game.py) ----------------------------------------------

def test_normalise_strips_accents_spaces_and_case():
    assert game.normalise("Ødegaard") == "ODEGAARD"
    assert game.normalise("Mac Allister") == "MACALLISTER"
    assert game.normalise("Pelé") == "PELE"
    assert game.normalise("Čech") == "CECH"
    assert game.normalise(None) == ""


def test_score_handles_repeated_letters():
    assert game.score("LINEKER", "LINEKER") == [game.HIT] * 7
    # Only one L in LAMB, so only one L can be coloured.
    assert game.score("LLLL", "LAMB") == [game.HIT, game.MISS, game.MISS, game.MISS]
    # GIGGS has three Gs: the misplaced ones are yellow while copies remain.
    assert game.score("SGGIG", "GIGGS") == [game.CLOSE, game.CLOSE, game.HIT, game.CLOSE, game.CLOSE]
    assert game.score("SALAH", "SAKAH") == [game.HIT, game.HIT, game.MISS, game.HIT, game.HIT]


def test_guess_limits_and_checks():
    assert game.max_guesses("PELE") == 6
    assert game.max_guesses("ZIDANE") == 6
    assert game.max_guesses("LINEKER") == 7
    assert game.check_guess("", "PELE") == "Type a name first."
    assert game.check_guess("PEL", "PELE") == "Needs 4 letters."
    assert game.check_guess("ABCD", "PELE") is None  # no name list: any letters count


def test_facts_unlock_after_two_and_four_guesses():
    assert [game.facts_unlocked(n, False) for n in range(6)] == [0, 0, 1, 1, 2, 2]
    assert game.facts_unlocked(0, True) == 2


def test_is_over_on_win_or_out_of_guesses():
    assert not game.is_over([], "PELE")
    assert game.is_over(["KAKA", "PELE"], "PELE")
    assert game.is_over(["KAKA"] * 6, "PELE")
    assert not game.is_over(["KAKA"] * 5, "PELE")


# ---- Scheduling (app/daily/schedule.py) --------------------------------------

def test_pinned_puzzle_wins_over_queue(app_instance):
    with app_instance.app_context():
        _puzzle("KLOSE", "Miroslav Klose", created=datetime(2026, 1, 1))
        pinned = _puzzle("PELE", "Pelé", day=DAY)
        assert schedule.puzzle_for(DAY).id == pinned.id


def test_queue_runs_oldest_approved_and_skips_drafts(app_instance):
    with app_instance.app_context():
        _puzzle("DRAFT", "A draft", approved=False, created=datetime(2026, 1, 1))
        newer = _puzzle("KLOSE", "Miroslav Klose", created=datetime(2026, 3, 1))
        older = _puzzle("PELE", "Pelé", created=datetime(2026, 2, 1))

        first = schedule.puzzle_for(DAY)
        assert first.id == older.id and first.day == DAY
        # Same day again: the pick is fixed, not re-drawn.
        assert schedule.puzzle_for(DAY).id == older.id
        assert schedule.puzzle_for(DAY + timedelta(days=1)).id == newer.id
        # Queue now empty (the draft never runs).
        assert schedule.puzzle_for(DAY + timedelta(days=2)) is None


def test_puzzle_number_counts_days_run(app_instance):
    with app_instance.app_context():
        first = _puzzle("PELE", "Pelé", day=DAY)
        second = _puzzle("KLOSE", "Miroslav Klose", day=DAY + timedelta(days=1))
        assert schedule.puzzle_number(first) == 1
        assert schedule.puzzle_number(second) == 2


# ---- Playing (app/daily/views.py) --------------------------------------------

def test_page_without_puzzle_says_so(client, app_instance, today_is):
    response = client.get("/daily/")
    assert response.status_code == 200
    assert b"no puzzle today" in response.data


def test_page_never_contains_answer_or_locked_facts(client, app_instance, today_is):
    with app_instance.app_context():
        _puzzle(fact_1="UNIQUEFACTONE", fact_2="UNIQUEFACTTWO")
    page = client.get("/daily/").get_data(as_text=True)
    assert "LINEKER" not in page and "Gary Lineker" not in page
    assert "UNIQUEFACTONE" not in page and "UNIQUEFACTTWO" not in page
    assert "Player" in page  # only the topic is shown at the start


def _guess(client, text):
    return client.post("/daily/guess", json={"guess": text})


def test_guess_flow_unlocks_facts_and_reveals_at_the_end(client, app_instance, today_is):
    with app_instance.app_context():
        _puzzle()

    # Wrong length is refused and not counted.
    response = _guess(client, "KEEGAN")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Needs 7 letters."
    assert response.get_json()["state"]["rows"] == []

    first = _guess(client, "GERRARD").get_json()["state"]
    assert first["facts"] == [] and "reveal" not in first
    assert first["rows"][0]["marks"][0] == game.MISS

    second = _guess(client, "LAMPARD").get_json()["state"]
    assert second["facts"] == ["Never booked."]

    _guess(client, "SCHOLES")
    fourth = _guess(client, "BECKHAM").get_json()["state"]
    assert fourth["facts"] == ["Never booked.", "1986 Golden Boot."]
    assert "reveal" not in fourth and not fourth["over"]

    won = _guess(client, "line ker").get_json()["state"]  # case and spaces don't matter
    assert won["over"] and won["won"]
    assert won["reveal"]["display"] == "Gary Lineker"
    assert won["reveal"]["sources"] == ["https://example.com/lineker"]

    # Finished: more guesses are refused.
    assert _guess(client, "GERRARD").status_code == 409


def test_progress_survives_reload_and_resets_next_day(client, app_instance, today_is):
    with app_instance.app_context():
        _puzzle("PELE", "Pelé", day=DAY)
        _puzzle("KAKA", "Kaká", day=DAY + timedelta(days=1))

    _guess(client, "KAKA")
    page = client.get("/daily/").get_data(as_text=True)
    assert '"guess": "KAKA"' in page or '"guess":"KAKA"' in page

    today_is(DAY + timedelta(days=1))
    state = _guess(client, "PELE").get_json()["state"]
    assert len(state["rows"]) == 1 and state["number"] == 2


def test_running_out_of_guesses_reveals_answer(client, app_instance, today_is):
    with app_instance.app_context():
        _puzzle("PELE", "Pelé")
    for _ in range(5):
        assert "reveal" not in _guess(client, "KAKA").get_json()["state"]
    state = _guess(client, "KAKA").get_json()["state"]
    assert state["over"] and not state["won"] and state["reveal"]["display"] == "Pelé"


# ---- Admin (app/daily/admin.py) ----------------------------------------------

def _login_as_admin(client, app_instance):
    with app_instance.app_context():
        role = Role.query.filter_by(name="Administrator").first()
        user = User(email="admin@example.com", username="admin", role=role)
        user.password = "secret"
        db.session.add(user)
        db.session.commit()
    client.post("/auth/login", data={"email": "admin@example.com", "password": "secret"})


def _form(**overrides):
    data = {
        "answer": "Mac Allister", "display": "Alexis Mac Allister", "topic": "Player",
        "fact_1": "Fact one.", "fact_2": "Fact two.",
        "sources": "https://example.com/a\n\nhttps://example.com/b", "day": "",
    }
    data.update(overrides)
    return data


def test_admin_requires_login(client, app_instance):
    response = client.get("/daily/admin")
    assert response.status_code == 302 and "/auth/login" in response.headers["Location"]


def test_admin_creates_draft_with_cleaned_answer(client, app_instance, today_is):
    _login_as_admin(client, app_instance)
    assert client.get("/daily/admin").status_code == 200

    response = client.post("/daily/admin/new", data=_form())
    assert response.status_code == 302
    with app_instance.app_context():
        puzzle = FactPuzzle.query.one()
        assert puzzle.answer == "MACALLISTER"
        assert not puzzle.approved and puzzle.day is None
        assert puzzle.source_list() == ["https://example.com/a", "https://example.com/b"]


def test_admin_rejects_bad_input(client, app_instance, today_is):
    _login_as_admin(client, app_instance)
    page = client.post("/daily/admin/new", data=_form(answer="Son")).get_data(as_text=True)
    assert "Must be 4 to 12 letters" in page
    page = client.post("/daily/admin/new", data=_form(sources="not a link")).get_data(as_text=True)
    assert "Not a web address" in page
    page = client.post("/daily/admin/new", data=_form(day="2026-12-01")).get_data(as_text=True)
    assert "Approve the puzzle before giving it a date" in page
    with app_instance.app_context():
        assert FactPuzzle.query.count() == 0


def test_admin_blocks_two_puzzles_on_one_day_and_unapproving_clears_day(client, app_instance, today_is):
    _login_as_admin(client, app_instance)
    with app_instance.app_context():
        _puzzle("PELE", "Pelé", day=date(2026, 12, 1))
        other = _puzzle("KLOSE", "Miroslav Klose").id

    page = client.post("/daily/admin/new", data=_form(approved="y", day="2026-12-01")).get_data(as_text=True)
    assert "Pelé is already set for that day" in page

    client.post("/daily/admin/{:d}/edit".format(other),
                data=_form(answer="KLOSE", display="Miroslav Klose", day=""))  # approved unticked
    with app_instance.app_context():
        klose = FactPuzzle.query.get(other)
        assert not klose.approved and klose.day is None


def test_admin_cannot_delete_a_puzzle_that_has_run(client, app_instance, today_is):
    _login_as_admin(client, app_instance)
    with app_instance.app_context():
        ran = _puzzle("PELE", "Pelé", day=DAY - timedelta(days=1)).id
        draft = _puzzle("KLOSE", "Miroslav Klose", approved=False).id
    assert client.post("/daily/admin/{:d}/delete".format(ran)).status_code == 400
    assert client.post("/daily/admin/{:d}/delete".format(draft)).status_code == 302
    with app_instance.app_context():
        assert [p.answer for p in FactPuzzle.query.all()] == ["PELE"]


def test_any_football_topic_is_shown_as_written(client, app_instance, today_is):
    with app_instance.app_context():
        _puzzle("ANFIELD", "Anfield", topic="Stadium", day=DAY)
        db.session.commit()
    page = client.get("/daily/").get_data(as_text=True)
    assert "Stadium" in page
    assert "ANFIELD" not in page.upper()  # the answer stays hidden


def test_guess_that_is_not_text_is_refused_not_crashed(client, app_instance, today_is):
    with app_instance.app_context():
        _puzzle(day=DAY)
        db.session.commit()
    for body in ({"guess": 1234567}, {"guess": ["LINEKER"]}, {"guess": {"a": 1}}, ["LINEKER"], {}):
        response = client.post("/daily/guess", json=body)
        assert response.status_code == 400, body
        assert response.get_json()["state"]["rows"] == []  # not counted
