"""CARD-154 — Print setup stores the plan and the trim together, and refuses "nan".

    AC-1  TestTrimValidation_RefusesNonFiniteValues
    AC-2  TestPrintSetup_PlanAndTrimCommitTogether
    AC-3  TestPrintSetup_NanWidthChangesNothing
    (3)   TestMarginValidation_RefusesNonFiniteValues — the margin half of the
          same NaN gap ("What to do", item 3)

CARD-174 (inch refusals; the cm wording unchanged):

    AC-3     TestTrimRefusal_StatedInchLimitIsAccepted
    AC-4/5   TestTrimRefusal_CmWordingUnchanged

CARD-178 (the inch figure a stored trim reopens with):

    AC-3/4/5 TestPropertyTest_TrimInchesShown_InsideLimitsAndAccepted (the
             card's PropertyTest_TrimInchesShown_InsideLimitsAndAccepted;
             prefixed Test so pytest collects the class)

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

    # Review cycle 1, F-001: the defect lived in the route, so the AC's named
    # test drives the route itself. A VALID trim passes the validator and both
    # writers' checks; the store then refuses the trim's flush. With the
    # route's old two-commit shape (save_plan, then set_print_spec) the plan
    # commits first and survives; with one write neither does. Observed on the
    # raw row in a fresh session, not through a return value.
    @pytest.mark.parametrize("store", ["sqlite", "postgres"])
    def test_print_setup_route_stores_neither_when_the_trim_write_fails(self, store, scope, panel) -> None:
        books = panel.book_manager
        book_id = _book_on_six_by_nine(books)
        row_before = _raw_row(scope, book_id)
        assert row_before[0] == plan_to_json(DEFAULT_PLAN)
        assert row_before[1:3] == SIX_BY_NINE_CM

        # TESTING mode propagates the route's exception through the client.
        with _trim_write_fails_at_flush(), pytest.raises(RuntimeError, match="simulated"):
            panel.test_client().post(
                f"/book/{book_id}/setup-print",
                data=_form(NEW_PLAN, width="20.32", height="25.40"),
            )

        plan_json, width, height, status = _raw_row(scope, book_id)
        assert plan_json == plan_to_json(DEFAULT_PLAN), "the plan was stored while the trim was refused"
        assert (width, height) == SIX_BY_NINE_CM
        assert status == row_before[3]


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


# --------------------------------------------------------------------------
# CARD-174 — trim refusals worded in the unit typed; the cm wording unchanged
# --------------------------------------------------------------------------

#: CARD-174 AC-3/AC-6: the inch limits the refusals and the Limits box state,
#: worked out by hand — 10 / 2.54 = 3.937 rounded up, 30 / 2.54 = 11.811 and
#: 48 / 2.54 = 18.898 rounded down — not read back from the code under test.
STATED_INCH_LIMITS = {"min": "3.94", "max_width": "11.81", "max_height": "18.89"}


class TestTrimRefusal_StatedInchLimitIsAccepted:
    """CARD-174 AC-3 — every inch limit a refusal states is accepted when typed.

    18.90 in, the figure the Limits box used to print, converts to 48.01 cm
    and is refused; the limits are cut inward so this cannot happen.
    """

    def test_the_shared_source_states_the_hand_worked_limits(self) -> None:
        limits = PrintSpecValidator.trim_limits()
        assert (limits.min_in, limits.max_width_in, limits.max_height_in) == (
            STATED_INCH_LIMITS["min"],
            STATED_INCH_LIMITS["max_width"],
            STATED_INCH_LIMITS["max_height"],
        )
        assert (limits.min_cm, limits.max_width_cm, limits.max_height_cm) == (10.0, 30.0, 48.0)

    @pytest.mark.parametrize(
        "inches",
        [
            (STATED_INCH_LIMITS["max_width"], STATED_INCH_LIMITS["max_height"]),
            (STATED_INCH_LIMITS["min"], STATED_INCH_LIMITS["min"]),
        ],
    )
    def test_each_stated_limit_converts_to_an_accepted_trim(self, inches) -> None:
        width_cm, height_cm = (PrintSpecValidator.inches_to_cm(v) for v in inches)
        assert PrintSpecValidator.validate_trim_size(width_cm, height_cm) == (True, None)
        assert PrintSpecValidator.validate_trim_size(
            width_cm, height_cm, entered_inches=inches
        ) == (True, None)

    @pytest.mark.parametrize(
        "inches, prefix",
        [
            (("11.82", "11"), "Trim width cannot exceed 11.81 in"),
            (("8.5", "18.90"), "Trim height cannot exceed 18.89 in"),
            (("3.93", "11"), "Trim size must be at least 3.94 in"),
            (("8.5", "3.93"), "Trim size must be at least 3.94 in"),
        ],
    )
    def test_one_hundredth_beyond_each_limit_is_refused_naming_it(self, inches, prefix) -> None:
        """The boundary just past each stated figure is refused — so it is the edge."""
        width_cm, height_cm = (PrintSpecValidator.inches_to_cm(v) for v in inches)
        ok, message = PrintSpecValidator.validate_trim_size(
            width_cm, height_cm, entered_inches=inches
        )
        assert ok is False
        assert message.startswith(prefix), message

    def test_seeded_corpus_of_hundredth_cm_bounds_states_only_accepted_inches(self, monkeypatch) -> None:
        """The inward rounding holds for cm bounds on a 0.01 cm grid, not just KDP's three.

        Only such bounds are drawn (rounded to 2 dp); for a bound off that grid,
        e.g. 15.875 cm, the stated 6.25 in converts to 15.88 cm and is refused,
        so the claim is not made for it. For each bound the class constants are moved, and the inch figures
        trim_limits() then states are typed back through inches_to_cm: each
        must pass validate_trim_size against the very bounds it was cut from.
        """
        rng = random.Random(174)
        cases = 0
        for _ in range(1500):
            low = round(rng.uniform(1.0, 20.0), 2)
            high_w = round(rng.uniform(low + 1.0, 60.0), 2)
            high_h = round(rng.uniform(low + 1.0, 80.0), 2)
            monkeypatch.setattr(PrintSpecValidator, "MIN_TRIM_CM", low)
            monkeypatch.setattr(PrintSpecValidator, "MAX_TRIM_WIDTH_CM", high_w)
            monkeypatch.setattr(PrintSpecValidator, "MAX_TRIM_HEIGHT_CM", high_h)
            limits = PrintSpecValidator.trim_limits()
            for inches in ((limits.max_width_in, limits.max_height_in), (limits.min_in, limits.min_in)):
                width_cm, height_cm = (PrintSpecValidator.inches_to_cm(v) for v in inches)
                assert PrintSpecValidator.validate_trim_size(width_cm, height_cm) == (True, None), (
                    low, high_w, high_h, inches
                )
                cases += 1
        assert cases >= 3000

    @pytest.mark.parametrize(
        "inches, cm",
        [
            ((STATED_INCH_LIMITS["max_width"], STATED_INCH_LIMITS["max_height"]), ("30.00", "47.98")),
            ((STATED_INCH_LIMITS["min"], STATED_INCH_LIMITS["min"]), ("10.01", "10.01")),
        ],
    )
    def test_the_route_stores_each_stated_limit(self, store, panel, inches, cm) -> None:
        books = panel.book_manager
        book_id = _book_on_six_by_nine(books)

        response = panel.test_client().post(
            f"/book/{book_id}/setup-print",
            data={"unit": "inches", "width": inches[0], "height": inches[1]},
        )

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/select-puzzles")
        assert _stored(books, book_id)[1] == cm


#: CARD-174 review F-001: inch entries that convert to exactly the cm bound
#: (10.00 / 30.00 / 48.00 cm, hand-checked: 3.937 x 2.54 = 9.99998,
#: 11.811 x 2.54 = 29.99994, 18.8976 x 2.54 = 48.0) — accepted on main, so
#: G-1 requires they stay accepted — and the entries 0.01 in beyond them
#: (9.97 / 30.03 / 48.03 cm), which stay refused. One axis per case, so each
#: bound comparison is pinned at equality on its own.
EXACT_BOUNDARY_INCHES = {
    ("3.937", "11"): ("10.00", "27.94"),
    ("8.5", "3.937"): ("21.59", "10.00"),
    ("11.811", "11"): ("30.00", "27.94"),
    ("8.5", "18.8976"): ("21.59", "48.00"),
}
BEYOND_BOUNDARY_INCHES = {
    ("3.927", "11"): ("Trim size must be at least 3.94 in", "Trim size must be at least 10.0 cm"),
    ("8.5", "3.927"): ("Trim size must be at least 3.94 in", "Trim size must be at least 10.0 cm"),
    ("11.821", "11"): ("Trim width cannot exceed 11.81 in", "Trim width cannot exceed 30.0 cm"),
    ("8.5", "18.9076"): ("Trim height cannot exceed 18.89 in", "Trim height cannot exceed 48.0 cm"),
}


class TestTrimRefusal_ExactCmBoundaryInInchesIsAccepted:
    """CARD-174 review F-001 / G-1 — a trim at exactly a KDP bound is accepted in either wording.

    The inch wording must not move the verdict at equality: each bound is a
    strict comparison, so an entry converting to exactly 10.00 / 30.00 /
    48.00 cm is accepted with and without ``entered_inches``, and through
    the route; 0.01 in beyond it is refused in both.
    """

    @pytest.mark.parametrize("inches", list(EXACT_BOUNDARY_INCHES))
    def test_the_exact_bound_is_accepted_with_and_without_entered_inches(self, inches) -> None:
        width_cm, height_cm = (PrintSpecValidator.inches_to_cm(v) for v in inches)
        assert (width_cm, height_cm) == EXACT_BOUNDARY_INCHES[inches]
        assert PrintSpecValidator.validate_trim_size(width_cm, height_cm) == (True, None)
        assert PrintSpecValidator.validate_trim_size(
            width_cm, height_cm, entered_inches=inches
        ) == (True, None)

    @pytest.mark.parametrize("inches", list(BEYOND_BOUNDARY_INCHES))
    def test_one_hundredth_of_an_inch_beyond_is_refused_in_both_wordings(self, inches) -> None:
        inch_prefix, cm_prefix = BEYOND_BOUNDARY_INCHES[inches]
        width_cm, height_cm = (PrintSpecValidator.inches_to_cm(v) for v in inches)
        ok, message = PrintSpecValidator.validate_trim_size(width_cm, height_cm)
        assert ok is False and message.startswith(cm_prefix), message
        ok, message = PrintSpecValidator.validate_trim_size(
            width_cm, height_cm, entered_inches=inches
        )
        assert ok is False and message.startswith(inch_prefix), message

    @pytest.mark.parametrize("inches", list(EXACT_BOUNDARY_INCHES))
    def test_the_route_stores_the_exact_bound(self, store, panel, inches) -> None:
        books = panel.book_manager
        book_id = _book_on_six_by_nine(books)

        response = panel.test_client().post(
            f"/book/{book_id}/setup-print",
            data={"unit": "inches", "width": inches[0], "height": inches[1]},
        )

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/select-puzzles")
        assert _stored(books, book_id)[1] == EXACT_BOUNDARY_INCHES[inches]

    @pytest.mark.parametrize("inches", list(BEYOND_BOUNDARY_INCHES))
    def test_the_route_refuses_one_hundredth_beyond_and_stores_nothing(self, store, panel, inches) -> None:
        books = panel.book_manager
        book_id = _book_on_six_by_nine(books)
        before = _stored(books, book_id)

        response = panel.test_client().post(
            f"/book/{book_id}/setup-print",
            data={"unit": "inches", "width": inches[0], "height": inches[1]},
        )

        assert response.status_code == 200
        assert f"Error: {BEYOND_BOUNDARY_INCHES[inches][0]}" in response.get_data(as_text=True)
        assert _stored(books, book_id) == before


#: CARD-174 AC-4/AC-5: today's three cm refusals, byte for byte — written out,
#: not rebuilt from the constants, so a change of wording or format is caught.
CM_REFUSALS = {
    ("31", "20"): "Trim width cannot exceed 30.0 cm (Amazon KDP limit)",
    ("20", "49"): "Trim height cannot exceed 48.0 cm (Amazon KDP limit)",
    ("9", "20"): "Trim size must be at least 10.0 cm in both dimensions",
}


class TestTrimRefusal_CmWordingUnchanged:
    """CARD-174 AC-4/AC-5 — a cm submission, and BookManager, keep today's wording."""

    @pytest.mark.parametrize("trim, message", list(CM_REFUSALS.items()))
    def test_validate_trim_size_without_a_unit_says_cm(self, trim, message) -> None:
        """AC-5: called as BookManager calls it — two cm strings, no keyword."""
        assert PrintSpecValidator.validate_trim_size(*trim) == (False, message)
        assert PrintSpecValidator.create_spec(width_cm=trim[0], height_cm=trim[1]) == (None, message)

    @pytest.mark.parametrize("trim, message", list(CM_REFUSALS.items()))
    def test_the_route_flashes_the_cm_message_for_a_cm_submission(self, store, panel, trim, message) -> None:
        """AC-4: through Print setup in cm; nothing stored."""
        books = panel.book_manager
        book_id = _book_on_six_by_nine(books)
        before = _stored(books, book_id)

        response = panel.test_client().post(
            f"/book/{book_id}/setup-print", data={"unit": "cm", "width": trim[0], "height": trim[1]}
        )

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert f"Error: {message}\n" in html
        assert "you entered" not in html
        assert _stored(books, book_id) == before

    def test_a_storage_refusal_still_reads_in_cm(self, books) -> None:
        """AC-5: BookManager's storage-boundary refusal quotes the cm message."""
        book_id = _book_on_six_by_nine(books)

        with pytest.raises(ValueError) as refused:
            books.set_print_spec(book_id, PrintSpec("31", "20"))

        assert str(refused.value).startswith(
            "a book's trim cannot be stored: Trim width cannot exceed 30.0 cm (Amazon KDP limit) (got "
        )
        assert books.get_book(book_id).trim_width_cm == SIX_BY_NINE_CM[0]


# --------------------------------------------------------------------------
# CARD-178 — the inch figure a stored trim reopens with
# --------------------------------------------------------------------------


def _hundredths(low_cm: float, high_cm: float) -> list[str]:
    """Every cm value from ``low_cm`` to ``high_cm`` inclusive on a 0.01 grid, as text.

    Built from whole hundredths, so no float step can skip or repeat a value.
    """
    return [f"{n // 100}.{n % 100:02d}" for n in range(round(low_cm * 100), round(high_cm * 100) + 1)]


def _shown_is_inside_and_accepted(stored: str, axis: str) -> tuple[bool, str]:
    """AC-3's two properties for one stored value, judged by trim_limits() and the validator.

    The other side is set to the minimum cm bound, which the validator always
    accepts, so a refusal can only be about ``axis``.
    """
    limits = PrintSpecValidator.trim_limits()
    shown = PrintSpecValidator.trim_inches_shown(stored, axis)
    high_in = limits.max_width_in if axis == "width" else limits.max_height_in
    inside = float(limits.min_in) <= float(shown) <= float(high_in)
    converted = PrintSpecValidator.inches_to_cm(shown)
    other = f"{limits.min_cm:.2f}"
    trim = (converted, other) if axis == "width" else (other, converted)
    accepted = PrintSpecValidator.validate_trim_size(*trim) == (True, None)
    return inside and accepted, shown


class TestPropertyTest_TrimInchesShown_InsideLimitsAndAccepted:
    """CARD-178 AC-3/AC-4/AC-5 — a stored trim inside the limits reopens in inches inside them.

    ``cm_to_inches`` rounds to the nearest hundredth, so 48.00 cm showed as
    18.90 in beside a Limits box stating 18.89 in, and 18.90 in converts to
    48.01 cm, which is refused. ``trim_inches_shown`` holds the figure at the
    stated limit for a stored value inside the cm limits, and only then.
    """

    def test_every_stored_hundredth_inside_kdp_bounds_shows_an_accepted_figure(self) -> None:
        """AC-3: the whole 0.01 cm grid of both axes, on KDP's bounds."""
        limits = PrintSpecValidator.trim_limits()
        cases = 0
        for axis, high_cm in (("width", limits.max_width_cm), ("height", limits.max_height_cm)):
            for stored in _hundredths(limits.min_cm, high_cm):
                ok, shown = _shown_is_inside_and_accepted(stored, axis)
                assert ok, (axis, stored, shown)
                cases += 1
        assert cases >= 5800

    def test_only_forty_eight_cm_high_differs_from_cm_to_inches(self) -> None:
        """AC-4: every other value on the grid shows exactly what cm_to_inches gives."""
        limits = PrintSpecValidator.trim_limits()
        differing = []
        cases = 0
        for axis, high_cm in (("width", limits.max_width_cm), ("height", limits.max_height_cm)):
            for stored in _hundredths(limits.min_cm, high_cm):
                shown = PrintSpecValidator.trim_inches_shown(stored, axis)
                if shown != PrintSpecValidator.cm_to_inches(stored):
                    differing.append((axis, stored, shown))
                cases += 1
        assert cases >= 5800
        # 48 / 2.54 = 18.8976: the stated limit, 18.89, rather than the nearest 18.90.
        assert differing == [("height", "48.00", STATED_INCH_LIMITS["max_height"])]

    @pytest.mark.parametrize(
        "stored, axis, plain",
        [
            # Worked by hand: 50 / 2.54 = 19.685, 9 / 2.54 = 3.543,
            # 48.01 / 2.54 = 18.9016, 30.01 / 2.54 = 11.8150, 9.99 / 2.54 = 3.9331.
            ("50.00", "height", "19.69"),
            ("9.00", "width", "3.54"),
            ("48.01", "height", "18.90"),
            ("30.01", "width", "11.81"),
            ("9.99", "width", "3.93"),
            ("9.99", "height", "3.93"),
        ],
    )
    def test_a_stored_value_outside_the_limits_shows_the_plain_figure(self, stored, axis, plain) -> None:
        """AC-4: a legacy out-of-range trim is not pulled inward to look valid.

        48.01 and 9.99 are one hundredth outside a bound, so the "inside"
        comparison is pinned at its edge on both sides.
        """
        assert PrintSpecValidator.trim_inches_shown(stored, axis) == plain
        assert PrintSpecValidator.cm_to_inches(stored) == plain

    def test_moved_bounds_on_a_hundredth_grid_keep_both_properties(self, monkeypatch) -> None:
        """AC-5: the held figure follows trim_limits(), not a literal.

        For each seeded draw the class bounds are moved and the values where a
        clamp can matter (each bound and its inside neighbour) plus a seeded
        sample of inside values are checked for AC-3's two properties. The
        corpus must reach both the maximum and the minimum clamp, counted as
        values whose shown figure differs from cm_to_inches.
        """
        rng = random.Random(178)
        cases = clamped_high = clamped_low = 0
        for _ in range(400):
            low = round(rng.uniform(1.0, 20.0), 2)
            high_w = round(rng.uniform(low + 1.0, 60.0), 2)
            high_h = round(rng.uniform(low + 1.0, 80.0), 2)
            monkeypatch.setattr(PrintSpecValidator, "MIN_TRIM_CM", low)
            monkeypatch.setattr(PrintSpecValidator, "MAX_TRIM_WIDTH_CM", high_w)
            monkeypatch.setattr(PrintSpecValidator, "MAX_TRIM_HEIGHT_CM", high_h)
            for axis, high in (("width", high_w), ("height", high_h)):
                grid = _hundredths(low, high)
                for stored in grid[:2] + grid[-2:] + rng.sample(grid, 10):
                    ok, shown = _shown_is_inside_and_accepted(stored, axis)
                    assert ok, (low, high_w, high_h, axis, stored, shown)
                    if shown != PrintSpecValidator.cm_to_inches(stored):
                        if float(stored) > (low + high) / 2:
                            clamped_high += 1
                        else:
                            clamped_low += 1
                    cases += 1
        assert cases >= 11000
        assert clamped_high >= 20 and clamped_low >= 20, (clamped_high, clamped_low)
