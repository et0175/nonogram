"""CARD-154 — Print setup stores the plan and the trim together, and refuses "nan".

    AC-1  TestTrimValidation_RefusesNonFiniteValues
    AC-2  TestPrintSetup_PlanAndTrimCommitTogether
    AC-3  TestPrintSetup_NanWidthChangesNothing
    (3)   TestMarginValidation_RefusesNonFiniteValues — the margin half of the
          same NaN gap ("What to do", item 3)

``float("nan")`` fails every ``<``/``>`` comparison, so ``validate_trim_size``
used to accept ``"nan"`` (and ``"inf"`` past the minimum check); Print setup
then committed the plan in one transaction and had the trim refused by
``set_print_spec`` in a second one, leaving the book on the new plan and the old
trim.

Storage tests run against **three** stores: in memory, a real SQLite file
(``sqlite_session_scope``, always available) and the real ``nonogram_test``
Postgres database through ``tests/conftest.py``'s ``db_session`` fixture (which
skips, visibly, only when that database is unreachable). Every stored value is
read back through a fresh session — a new ``BookManager`` call, and for AC-2 a
raw ``books`` row query as well, an observation that shares no code with the
writer under test.
"""

from __future__ import annotations

import random
from contextlib import contextmanager

import pytest
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_manager import BookManager, plan_to_json
from nonogram.admin.book_plan import BUCKETS, DEFAULT_PLAN, TIERS, Split, prefill
from nonogram.admin.print_specs import PrintSpec, PrintSpecValidator
from nonogram.admin.puzzle_review import PuzzleReviewService
from tests.helpers.db import sqlite_session_scope

STORES = ("memory", "sqlite", "postgres")

#: A non-default trim the book is put on before each test, so "the trim did not
#: change" cannot be satisfied by a write of the profile's defaults.
SIX_BY_NINE_CM = ("15.24", "22.86")

#: A valid plan that differs from DEFAULT_PLAN (150 at 40/40/20).
NEW_PLAN = prefill(120, Split(30, 45, 25))

#: The message ``validate_trim_size`` gives a value that is not a number at all
#: — the shape AC-1 asks every non-finite value to share.
NOT_NUMERIC = "Trim size must be numeric values"

#: Spellings that parse to a non-finite float. ``float`` strips whitespace and
#: ignores case, and "1e999" overflows to inf.
NON_FINITE = ("nan", "inf", "-inf", "NaN", "NAN", " inf ", "Infinity", "-Infinity", "+nan",
              "1e999", "-1e999")


# --------------------------------------------------------------------------
# Stores
# --------------------------------------------------------------------------


@contextmanager
def _committing(factory):
    """``session_scope``'s shape over an arbitrary sessionmaker."""
    db = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _session_scope_for(store, request, tmp_path, monkeypatch):
    """The session factory ``store`` names, or ``None`` for memory-only mode."""
    if store == "memory":
        return None
    if store == "sqlite":
        return sqlite_session_scope(tmp_path, "card-154.db")
    # Real Postgres (nonogram_test): the conftest fixture refuses any database
    # not ending in _test, rebuilds the schema once and truncates per test.
    factory = request.getfixturevalue("db_session")
    return lambda: _committing(factory)


@pytest.fixture(params=STORES)
def store(request):
    return request.param


@pytest.fixture
def scope(store, request, tmp_path, monkeypatch):
    return _session_scope_for(store, request, tmp_path, monkeypatch)


@pytest.fixture
def books(scope) -> BookManager:
    if scope is None:
        return BookManager(session_factory=None)
    return BookManager(session_factory=scope, puzzle_store=PuzzleReviewService(session_factory=scope))


def _book_on_six_by_nine(books: BookManager) -> str:
    book_id = books.create_book("Winter", "Twenty winter pictures.", "generic", "adults")
    assert books.set_print_spec(book_id, PrintSpec(*SIX_BY_NINE_CM)) is True
    assert books.get_plan(book_id) == DEFAULT_PLAN
    return book_id


def _stored(books: BookManager, book_id: str):
    """Plan, trim, status and ink mode as storage holds them, read afresh."""
    book = books.get_book(book_id)
    return (
        books.get_plan(book_id),
        (book.trim_width_cm, book.trim_height_cm),
        book.status,
        book.interior_ink_mode,
    )


def _raw_row(scope, book_id: str):
    """The ``books`` row straight from a new session — not through BookManager."""
    import uuid

    from nonogram.db.models import Book as DBBook

    with scope() as db:
        row = db.get(DBBook, uuid.UUID(book_id))
        return dict(row.distribution_plan), row.trim_width_cm, row.trim_height_cm, row.status


# --------------------------------------------------------------------------
# AC-1
# --------------------------------------------------------------------------


class TestTrimValidation_RefusesNonFiniteValues:
    """AC-1 — "nan", "inf", "-inf" (and friends) refused for either dimension."""

    @pytest.mark.parametrize("dimension", ["width", "height"])
    @pytest.mark.parametrize("value", NON_FINITE)
    def test_each_spelling_is_refused_in_each_dimension(self, value, dimension) -> None:
        width, height = ("15.24", "22.86")
        if dimension == "width":
            width = value
        else:
            height = value

        assert PrintSpecValidator.validate_trim_size(width, height) == (False, NOT_NUMERIC)
        # And create_spec, the route's entry, builds nothing from it.
        assert PrintSpecValidator.create_spec(width_cm=width, height_cm=height) == (None, NOT_NUMERIC)

    def test_the_message_is_the_one_other_invalid_input_gets(self) -> None:
        assert PrintSpecValidator.validate_trim_size("abc", "22.86") == (False, NOT_NUMERIC)
        assert PrintSpecValidator.validate_trim_size("nan", "22.86") == (False, NOT_NUMERIC)

    def test_both_dimensions_non_finite(self) -> None:
        assert PrintSpecValidator.validate_trim_size("nan", "inf") == (False, NOT_NUMERIC)

    def test_seeded_corpus_finite_values_keep_their_old_verdict(self) -> None:
        """G-1: every finite trim gets exactly the verdict the bounds give it.

        The oracle is the KDP bounds stated as literals here, not the
        validator's constants, so a change to either side is caught.
        """
        rng = random.Random(154)
        cases = 0
        for _ in range(2000):
            width = round(rng.uniform(0.0, 60.0), 2)
            height = round(rng.uniform(0.0, 80.0), 2)
            expected = 10.0 <= width <= 30.0 and 10.0 <= height <= 48.0
            ok, _message = PrintSpecValidator.validate_trim_size(str(width), str(height))
            assert ok is expected, (width, height)
            cases += 1
        assert cases >= 2000

    def test_the_bounds_and_the_profile_are_still_accepted(self) -> None:
        for width, height in [("10", "10"), ("30", "48"), ("21.59", "27.94")]:
            assert PrintSpecValidator.validate_trim_size(width, height) == (True, None)


# --------------------------------------------------------------------------
# What to do, item 3 — the margins
# --------------------------------------------------------------------------


class TestMarginValidation_RefusesNonFiniteValues:
    """create_spec used to take any margin string as given — "nan" included."""

    @pytest.mark.parametrize(
        "field, label",
        [("gutter_margin_cm", "Gutter margin"), ("outside_margin_cm", "Outside margin"),
         ("outside_margin_bleed_cm", "Outside margin with bleed")],
    )
    @pytest.mark.parametrize("value", NON_FINITE + ("abc",))
    def test_a_non_finite_margin_is_refused(self, field, label, value) -> None:
        spec, error = PrintSpecValidator.create_spec(**{field: value})
        assert spec is None
        assert error == f"{label} must be a numeric value"

    def test_valid_and_absent_margins_are_unchanged(self) -> None:
        """G-1: the defaults and an explicit finite margin come through as before."""
        spec, error = PrintSpecValidator.create_spec()
        assert error is None
        assert (spec.gutter_margin_cm, spec.outside_margin_cm) == ("1.27", "0.95")
        spec, error = PrintSpecValidator.create_spec(gutter_margin_cm="", outside_margin_cm=None)
        assert error is None
        assert (spec.gutter_margin_cm, spec.outside_margin_cm) == ("1.27", "0.95")
        spec, error = PrintSpecValidator.create_spec(
            gutter_margin_cm="1.60", outside_margin_cm="1.00", outside_margin_bleed_cm="1.30"
        )
        assert error is None
        assert (spec.gutter_margin_cm, spec.outside_margin_cm, spec.outside_margin_bleed_cm) == (
            "1.60", "1.00", "1.30")


# --------------------------------------------------------------------------
# AC-2
# --------------------------------------------------------------------------


@contextmanager
def _trim_write_fails_at_flush():
    """Make any flush that writes a book's trim fail, inside its transaction.

    The plan is accepted (it is a valid DistributionPlan, and the spec passes
    every check), so the failure happens *after* the plan has been accepted and
    while it is pending in the same session: the one way to tell one commit
    from two. With two commits, the plan's flush carries no trim change and
    commits; only the second fails.
    """
    from nonogram.db.models import Book as DBBook

    def refuse(session, _flush_context, _instances):
        for obj in session.dirty:
            if isinstance(obj, DBBook) and inspect(obj).attrs.trim_width_cm.history.has_changes():
                raise RuntimeError("simulated failure writing the trim")

    event.listen(Session, "before_flush", refuse)
    try:
        yield
    finally:
        event.remove(Session, "before_flush", refuse)


class TestPrintSetup_PlanAndTrimCommitTogether:
    """AC-2 — a trim write that fails after the plan was accepted stores nothing."""

    # Memory-only mode has no flush to fail; its all-or-nothing is the
    # refused-spec test below.
    @pytest.mark.parametrize("store", ["sqlite", "postgres"])
    def test_a_failure_inside_the_transaction_rolls_the_plan_back(self, store, scope, books) -> None:
        book_id = _book_on_six_by_nine(books)
        row_before = _raw_row(scope, book_id)

        with _trim_write_fails_at_flush(), pytest.raises(RuntimeError, match="simulated"):
            books.save_plan(book_id, NEW_PLAN, print_spec=PrintSpec("20.32", "25.40"))

        assert _raw_row(scope, book_id) == row_before
        assert row_before[0] == plan_to_json(DEFAULT_PLAN)
        assert books.get_plan(book_id) == DEFAULT_PLAN

    @pytest.mark.parametrize(
        "bad",
        [PrintSpec("nan", "22.86"), PrintSpec("15.24", "inf"), PrintSpec("-inf", "nan"),
         PrintSpec("999", "22.86"), PrintSpec("15.24", "22.86", interior_ink_mode="sepia")],
        ids=["nan-width", "inf-height", "both", "out-of-bounds", "unknown-ink"],
    )
    def test_a_spec_refused_at_the_storage_boundary_stores_no_plan(self, store, scope, books, bad) -> None:
        """A spec that bypassed the validator straight into the combined writer."""
        book_id = _book_on_six_by_nine(books)
        before = _stored(books, book_id)

        with pytest.raises(ValueError):
            books.save_plan(book_id, NEW_PLAN, print_spec=bad)

        assert _stored(books, book_id) == before
        assert before[0] == DEFAULT_PLAN and before[1] == SIX_BY_NINE_CM
        if scope is not None:
            assert _raw_row(scope, book_id)[0] == plan_to_json(DEFAULT_PLAN)

    def test_a_valid_pair_stores_both(self, store, scope, books) -> None:
        """G-1: the combined write stores what the two writers stored."""
        book_id = _book_on_six_by_nine(books)

        assert books.save_plan(
            book_id, NEW_PLAN, print_spec=PrintSpec("20.32", "25.40", interior_ink_mode="colour")
        ) is True

        plan, trim, status, ink = _stored(books, book_id)
        assert (plan, trim, status, ink) == (NEW_PLAN, ("20.32", "25.40"), "draft", "colour")
        if scope is not None:
            assert _raw_row(scope, book_id) == (plan_to_json(NEW_PLAN), "20.32", "25.40", "draft")

    def test_an_unknown_book_stores_nothing(self, store, books) -> None:
        import uuid

        missing = str(uuid.uuid4()) if books._session_factory else "book_999999"
        assert books.save_plan(missing, NEW_PLAN, print_spec=PrintSpec(*SIX_BY_NINE_CM)) is False


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


def _form(plan, *, width, height, unit="cm") -> dict:
    form = {"unit": unit, "width": width, "height": height, "plan_count": str(plan.count)}
    for tier, share in zip(TIERS, (plan.split.easy, plan.split.medium, plan.split.hard)):
        form[f"split_{tier.value}"] = str(share)
    for b, bucket in enumerate(BUCKETS):
        for tier in TIERS:
            form[f"cell_{b}_{tier.value}"] = str(plan.cell(bucket, tier))
    return form


@pytest.fixture
def panel(store, scope, monkeypatch):
    """The admin app over ``store``."""
    from nonogram.admin.app import create_app

    monkeypatch.setenv("TESTING", "true")
    if store == "memory":
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setattr(book_manager_module, "_book_manager", BookManager(session_factory=None))
    elif store == "sqlite":
        import nonogram.db

        monkeypatch.setenv("DATABASE_URL", "sqlite:///card-154-test-only")
        monkeypatch.setattr(nonogram.db, "session_scope", scope)
    # postgres: db_session (pulled in by ``scope``) already points DATABASE_URL
    # at nonogram_test, and create_app uses nonogram.db.session_scope on it.
    app = create_app()
    app.config["TESTING"] = True
    return app


class TestPrintSetup_NanWidthChangesNothing:
    """AC-3 — "nan" as the width re-renders the refusal; plan and trim stay put."""

    @pytest.mark.parametrize(
        "unit, width, height",
        [("cm", "nan", "22.86"), ("cm", "inf", "22.86"), ("cm", "15.24", "-inf"),
         ("inches", "nan", "9"), ("inches", "NaN", "inf")],
    )
    def test_the_form_is_refused_and_nothing_is_stored(self, store, panel, unit, width, height) -> None:
        books = panel.book_manager
        book_id = _book_on_six_by_nine(books)
        before = _stored(books, book_id)
        client = panel.test_client()

        response = client.post(
            f"/book/{book_id}/setup-print",
            data=_form(NEW_PLAN, width=width, height=height, unit=unit),
        )

        assert response.status_code == 200  # re-rendered, not redirected on
        html = response.get_data(as_text=True)
        assert "alert-danger" in html
        assert f"Error: {NOT_NUMERIC}" in html
        assert "Print specs set" not in html
        assert _stored(books, book_id) == before
        assert before[0] == DEFAULT_PLAN and before[1] == SIX_BY_NINE_CM

    def test_a_valid_submission_still_stores_both(self, store, panel) -> None:
        """G-1: the same form with a real width saves the plan and the trim."""
        books = panel.book_manager
        book_id = _book_on_six_by_nine(books)

        response = panel.test_client().post(
            f"/book/{book_id}/setup-print", data=_form(NEW_PLAN, width="20.32", height="25.40")
        )

        assert response.status_code == 302
        plan, trim, _status, _ink = _stored(books, book_id)
        # Compared by content: a plan read off the form marks its cells edited.
        assert (plan.count, plan.split, plan.cells) == (NEW_PLAN.count, NEW_PLAN.split, NEW_PLAN.cells)
        assert trim == ("20.32", "25.40")
