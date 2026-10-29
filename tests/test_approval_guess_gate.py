"""CARD-291 (FR-046) — approval refuses a puzzle whose solve needed guessing.

Tests, by node id (FR-046, ADR-0032/R3)
=======================================
Written out in full — path and name on one line each — because the
architecture validator resolves a check ref by ``git grep -lw`` of the WHOLE
``path::name`` string over tracked, non-Markdown code. **A ref whose string
appears nowhere reads as a DEAD check ref however green the test is**, so
writing the tests does not by itself revive the five refs the model carries:
measured on this branch, with all five collected and passing, the validator
still reported them dead until this table existed. The precedent and the
mechanism are CARD-294's (``tests/test_public_player.py``'s own table), and
``test_the_registrys_check_refs_for_this_card_all_resolve`` below holds this
table to the registry in both directions, so it cannot outlive a rename.

* AC-393 — ``tests/test_approval_guess_gate.py::test_approve_refuses_a_branching_puzzle``
* AC-394 — ``tests/test_approval_guess_gate.py::test_batch_approve_holds_back_branching_puzzles``
* AC-395 — ``tests/test_approval_guess_gate.py::test_unknown_verdict_fails_closed``
* AC-396 — ``tests/test_approval_guess_gate.py::test_edit_refuses_a_branching_grid_behind_the_approved_door``
* EC-051 — ``tests/test_approval_guess_gate.py::test_every_approved_writer_passes_the_gate``

ADR-0032/R3's own check names the last of those, by the same whole string.

**What this file is about.** Unique (CON-005, ADR-0032/R1) is not the same fact
as humanly derivable. A solve can prove exactly one solution while finding it
only by branching search, and seven such puzzles reached book c1: graded
*medium*, 63-97 % of their cells settled only by search, and the 15x15 the
owner tried to play had zero cells derivable by line logic from the empty
board. ADR-0029/R6 closed the grading half of that — a branching solve now
scores the ceiling — but a score is a number and *hard* is a publishable tier.
The grade's job is to not lie; this gate's job is to not sell it.

**Neither of the five tests below needs a database.** Both store modes run in
every one of them: the in-memory mode directly, and the database mode over a
fresh SQLite file through ``tests/helpers/db.py:sqlite_session_scope``. There
is no ``db_required`` marker anywhere in this file and so no test here can skip
green — which matters more than usual, because a skipped gate test is an
ungated door, and 26 tests in this suite do skip green on a box with no
``DATABASE_URL``.

**Why the five are plain functions rather than parametrized ones.** Each name
is a check ref — ADR-0032/R3 names
``test_every_approved_writer_passes_the_gate`` and requirements.yml names the
other four — so the node id a ref resolves to is the node id that runs. A
parametrized test resolves to ``name[memory]``/``name[sqlite]`` instead, and
both modes are therefore driven *inside* each test, with every mode's verdict
recorded and asserted together rather than short-circuited at the first one
(:func:`both_modes` and the ``report``/``verdicts`` idiom below).
"""

from __future__ import annotations

import ast
import pathlib
import uuid
import warnings
from dataclasses import dataclass, field
from typing import Callable, Optional

import pytest

import nonogram.admin.image_manager as image_manager_module
import nonogram.admin.puzzle_review as puzzle_review_module
from nonogram.admin.puzzle_review import (
    Approvability,
    BulkOutcome,
    GridNotApprovable,
    PuzzleReviewService,
    PuzzleStatus,
)
from nonogram.clues import compute_clues
from nonogram.errors import SolverTimeout
from nonogram.solver import STRATEGY_GUESS, solve

from tests.helpers.db import make_batch, make_book, sqlite_session_scope

# --------------------------------------------------------------------------
# The fixtures, pinned as cells and checked against the solver
# --------------------------------------------------------------------------

#: A 9x9 whose verifying solve has to SEARCH: uniquely solvable, but line
#: logic alone does not finish it, so the solver branches and FR-029's
#: ``guess`` strategy is reported for it.
#:
#: The same cells as ``tests/test_admin_regrade.py``'s ``GUESS_GRID``, pinned
#: again here rather than imported: a shared mutable fixture between two files
#: that assert different things about it is how one file's edit silently
#: re-points the other's premise, and this file's whole subject is that the
#: fixture really does branch. Both copies carry their own premise check.
#: 9x9 is the smallest extent at which a branching unique grid exists at all.
GUESS_GRID = [
    [False, False, True, True, False, False, True, True, False],
    [True, False, True, False, False, True, False, False, True],
    [True, False, False, True, False, False, True, False, False],
    [False, False, False, True, True, False, True, False, False],
    [False, True, False, False, True, False, False, False, False],
    [True, False, True, True, False, False, False, False, False],
    [False, True, False, True, True, False, False, False, False],
    [False, True, False, False, False, False, False, True, True],
    [False, True, False, False, False, False, False, False, False],
]

#: The control: the same extent, uniquely solvable, and settled by line logic
#: alone. Found by seeded search (``random.Random(291)``, density 0.55, the
#: third draw) and pinned as cells so the fixture cannot drift with the search.
#: The same extent as :data:`GUESS_GRID` on purpose — AC-396 stores one onto
#: the other, and a replacement grid has to keep the puzzle's size (CARD-251
#: AC-5), so a differently shaped control would be refused for the wrong
#: reason and the test would pass without reaching this card's rule.
LINE_GRID = [
    [True, False, False, False, False, False, False, True, True],
    [False, True, True, True, False, True, True, False, False],
    [True, True, True, True, True, True, True, False, True],
    [False, False, False, False, False, True, True, True, True],
    [False, False, True, True, False, False, False, True, True],
    [True, False, False, True, True, False, False, True, False],
    [False, True, True, True, True, True, True, True, False],
    [False, True, False, True, True, True, False, True, True],
    [False, True, True, True, False, True, False, False, False],
]

#: Two solutions, not one: both diagonals satisfy one filled cell per row and
#: per column. Never stored through ``add_puzzle`` — CARD-080's boundary
#: refuses it, correctly — only written straight into a row, which is AC-395's
#: "non-unique grid" case as an older writer could have left it.
AMBIGUOUS_GRID = [[True, False], [False, True]]


def _assert_the_fixtures_are_what_this_file_assumes() -> None:
    """Checked against the solver rather than asserted in a comment.

    Both facts about :data:`GUESS_GRID`, not one. A solver improvement that
    settled it by line logic alone would leave every refusal test below
    passing vacuously — approving nothing because there is nothing to refuse —
    which is the exact failure mode a guess fixture was first added to end
    (CARD-077 review cycle 1, F-001).
    """
    guess = solve(*compute_clues(GUESS_GRID))
    assert guess.solution_count == 1, "GUESS_GRID is not a puzzle"
    assert guess.signals.branch_nodes > 0, (
        "GUESS_GRID no longer branches, so nothing in this file reaches the "
        "rule it was written for"
    )
    line = solve(*compute_clues(LINE_GRID))
    assert line.solution_count == 1, "LINE_GRID is not a puzzle"
    assert line.signals.branch_nodes == 0, (
        "LINE_GRID branches, so this file has no control and every refusal "
        "below would be indistinguishable from refusing everything"
    )
    assert solve(*compute_clues(AMBIGUOUS_GRID)).solution_count == 2
    assert len(GUESS_GRID[0]) == len(LINE_GRID[0]) and len(GUESS_GRID) == len(LINE_GRID)


def test_the_fixture_grids_are_what_this_file_assumes() -> None:
    _assert_the_fixtures_are_what_this_file_assumes()


# --------------------------------------------------------------------------
# A store in each mode, and a way to drive both without short-circuiting
# --------------------------------------------------------------------------


@dataclass
class Store:
    """One store in one of its two modes, plus what a test needs around it."""

    service: PuzzleReviewService
    mode: str
    session_factory: Optional[Callable] = None
    batches: dict = field(default_factory=dict)

    def batch(self, name: str = "b") -> str:
        """A batch id that satisfies ``puzzles.batch_id``'s foreign key."""
        if name not in self.batches:
            self.batches[name] = (
                str(uuid.uuid4())
                if self.session_factory is None
                else make_batch(self.session_factory)
            )
        return self.batches[name]

    def add(self, grid, *, strategies, batch: Optional[str] = None, **overrides) -> str:
        """Store one puzzle, with its clues derived from the grid it carries.

        ``strategies`` is explicit on every call because the stored list is
        what the gate reads first: a list this system's solver could have
        written is believed, and anything else buys one budgeted re-solve
        (``_is_strategies_list``). Both paths are exercised below and the
        difference is the point, so no test may leave it to a default.
        """
        rows, columns = compute_clues(grid)
        payload = dict(
            grid=grid,
            clues_rows=[list(clue) for clue in rows],
            clues_cols=[list(clue) for clue in columns],
            width=len(grid[0]),
            height=len(grid),
            theme="winter",
            difficulty_score=70,
            difficulty_tier="medium",
            quality_score=60,
            recognizability="high",
            strategies_used=strategies,
            batch_id=self.batch(batch) if batch is not None else None,
            source_image="ornament.png",
        )
        payload.update(overrides)
        return self.service.add_puzzle(**payload)

    def row(self, puzzle_id: str) -> dict:
        return self.service.get_puzzle(puzzle_id)

    def status(self, puzzle_id: str) -> str:
        return self.row(puzzle_id)["status"]

    def book(self, puzzle_id: str) -> str:
        """Record a book as holding this puzzle, foreign key and all."""
        book_id = (
            str(uuid.uuid4())
            if self.session_factory is None
            else make_book(self.session_factory, title="Winter nights")
        )
        assert self.service.assign_to_book([puzzle_id], book_id) == 1
        return book_id

    def overwrite(self, puzzle_id: str, **columns) -> None:
        """Write columns straight into storage, around every write guard.

        AC-395's three unknown verdicts are all rows that *cannot be created
        through the front door*: CARD-080's boundary refuses an unreadable or
        ambiguous grid at ``add_puzzle``. They are rows an older writer left,
        which is precisely the population the fail-closed posture exists for,
        so they are planted the way history planted them.
        """
        if self.session_factory is None:
            self.service.puzzles[puzzle_id].update(columns)
            return
        from nonogram.db.models import Puzzle

        with self.session_factory() as db:
            row = db.query(Puzzle).filter(Puzzle.id == uuid.UUID(puzzle_id)).first()
            assert row is not None, f"no puzzles row for {puzzle_id}"
            for column, value in columns.items():
                setattr(row, column, value)


def both_modes(tmp_path) -> list:
    """A fresh store in each mode: in-memory, and SQLite-backed.

    SQLite rather than ``db_required``/Postgres so this file cannot skip
    green. The session factory is the real one the panel uses, over a file of
    this test's own, with foreign keys enforced (``tests/conftest.py``
    registers the PRAGMA against SQLAlchemy's ``Engine``).
    """
    stores = [Store(service=PuzzleReviewService(), mode="memory")]
    factory = sqlite_session_scope(tmp_path, "approval-gate.db")
    stores.append(
        Store(
            service=PuzzleReviewService(session_factory=factory),
            mode="sqlite",
            session_factory=factory,
        )
    )
    return stores


@dataclass
class Report:
    """Every mode's findings, so one mode's failure does not hide another's.

    A bare ``assert`` inside a loop over the modes stops at the first mode
    that fails, which reports the same single line whether the second mode was
    sound or never reached. Findings are collected under their mode's name and
    asserted once at the end.
    """

    findings: list = field(default_factory=list)
    checks: int = 0

    def check(self, mode: str, what: str, condition: bool) -> None:
        self.checks += 1
        if not condition:
            self.findings.append(f"[{mode}] {what}")

    def equal(self, mode: str, what: str, got, want) -> None:
        self.check(mode, f"{what}: got {got!r}, want {want!r}", got == want)

    def done(self, *, at_least: int) -> None:
        assert self.checks >= at_least, (
            f"only {self.checks} checks ran, expected at least {at_least} — a "
            "mode or a case was not reached, which is a vacuous pass"
        )
        assert not self.findings, "\n".join(self.findings)


@pytest.fixture
def admin_app(monkeypatch):
    """The panel in in-memory mode, for the route half of AC-393/AC-394.

    The rule itself lives in the store and is driven in both modes by the
    service tests; what the route adds is the *sentence* and the status code,
    and that wording is mode-independent — it is read off
    :class:`Approvability`, which has no store in it.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


def _store_of(app) -> Store:
    return Store(service=app.puzzle_review_service, mode="route")


# --------------------------------------------------------------------------
# AC-393 — the per-puzzle door
# --------------------------------------------------------------------------


def test_approve_refuses_a_branching_puzzle(tmp_path, admin_app) -> None:
    """AC-393: a draft puzzle whose solve branched cannot be approved.

    Four readings of one rule, so that none of them can be the only one: the
    service in each store mode, with the stored strategies list believed
    (``["simple_overlap", "guess"]`` — a list this solver could have written)
    and with it *not* believed (``[]``, which buys the re-solve that finds the
    branch), and the route, which has to say why.

    The control rides along in every reading: :data:`LINE_GRID`, same extent,
    same everything but the search, approves. Without it a gate that refused
    every approval would pass this test.
    """
    _assert_the_fixtures_are_what_this_file_assumes()
    report = Report()

    for store in both_modes(tmp_path):
        for label, branching_list, line_list in (
            # The stored solver-written list is believed, so each row carries
            # the list its own grid really earns.
            ("stored list", ["simple_overlap", STRATEGY_GUESS], ["simple_overlap"]),
            # And the other path: a list no solver here wrote — the legacy
            # spelling `line_logic`, which really is in old rows — so the
            # verdict is bought with one budgeted re-solve of the stored grid.
            # Not `[]`, which `add_puzzle` fills in from its own proving solve
            # and which would therefore exercise the believed path twice.
            ("re-solved", ["line_logic"], ["line_logic"]),
        ):
            mode = f"{store.mode}/{label}"
            branching = store.add(GUESS_GRID, strategies=branching_list)
            line = store.add(LINE_GRID, strategies=line_list)

            report.equal(
                mode,
                "the gate's verdict on the branching puzzle",
                store.service.approvability_of(branching),
                Approvability.NEEDS_GUESSING,
            )
            report.check(
                mode,
                "approve_puzzle returned True for a branching puzzle",
                store.service.approve_puzzle(branching) is False,
            )
            report.equal(
                mode,
                "the refused puzzle's status",
                store.status(branching),
                PuzzleStatus.DRAFT.value,
            )
            # The control: the rule is about guessing, not about approving.
            report.equal(
                mode,
                "the gate's verdict on the line-solvable puzzle",
                store.service.approvability_of(line),
                Approvability.OK,
            )
            report.check(
                mode,
                "approve_puzzle refused a line-solvable puzzle",
                store.service.approve_puzzle(line) is True,
            )
            report.equal(
                mode, "the approved puzzle's status", store.status(line),
                PuzzleStatus.APPROVED.value,
            )

    # And the route, which is where the owner meets the refusal.
    route = _store_of(admin_app)
    branching = route.add(GUESS_GRID, strategies=[])
    line = route.add(LINE_GRID, strategies=[])
    client = admin_app.test_client()

    refusal = client.post(
        f"/puzzle/{branching}/approve", headers={"Accept": "application/json"}
    )
    report.equal("route", "the refusal's status code", refusal.status_code, 409)
    report.check(
        "route",
        "the refusal does not say the puzzle needs guessing",
        "needs guessing" in refusal.get_json()["message"],
    )
    report.check("route", "the refusal reported ok", refusal.get_json()["ok"] is False)
    report.equal(
        "route", "the refused row's status", route.status(branching),
        PuzzleStatus.DRAFT.value,
    )

    accepted = client.post(
        f"/puzzle/{line}/approve", headers={"Accept": "application/json"}
    )
    report.equal("route", "the control's status code", accepted.status_code, 200)
    report.equal(
        "route", "the control's status", route.status(line),
        PuzzleStatus.APPROVED.value,
    )

    report.done(at_least=30)


def test_the_refusal_is_not_the_in_book_refusal(tmp_path) -> None:
    """The two refusals this door now has are told apart, not merged.

    CARD-100's refusal and this one both come back as ``False`` from
    ``approve_puzzle``, and a route that reported either as the other would
    send the owner to the wrong fix. The predicates are separate and answer
    independently.
    """
    for store in both_modes(tmp_path):
        branching = store.add(GUESS_GRID, strategies=[STRATEGY_GUESS])
        assert store.service.in_a_book(branching) is False, store.mode
        assert store.service.approvability_of(branching) is Approvability.NEEDS_GUESSING

        line = store.add(LINE_GRID, strategies=["simple_overlap"])
        store.book(line)
        assert store.service.in_a_book(line) is True, store.mode
        assert store.service.approvability_of(line) is Approvability.OK, store.mode


def test_reject_and_restore_stay_ungated(tmp_path) -> None:
    """The gate fires on the way IN, and only there.

    A branching puzzle that could not be rejected would be a branching puzzle
    nobody could get rid of, which is the opposite of what this card is for.
    Both directions out of the invariant are asserted, in both modes.
    """
    for store in both_modes(tmp_path):
        for action, expected in (
            ("reject_puzzle", PuzzleStatus.REJECTED.value),
            ("restore_puzzle", PuzzleStatus.DRAFT.value),
        ):
            branching = store.add(GUESS_GRID, strategies=[STRATEGY_GUESS])
            assert getattr(store.service, action)(branching) is True, (
                f"{store.mode}: {action} was refused for a branching puzzle"
            )
            assert store.status(branching) == expected, store.mode


def test_the_happy_path_does_not_enter_the_solver(tmp_path, monkeypatch) -> None:
    """ADR-0029/R2 at the approval door: the stored verdict is reused.

    A gate that re-solved on every approval would make bulk-approving a batch
    of thirty 30x30 puzzles pay for thirty searches, and the fail-closed
    posture would then be refusing honest puzzles on a timeout. The stored
    solver-written list is believed, so the normal approval buys no solve at
    all; the re-solve is what a row whose list no solver here wrote costs, and
    this asserts both sides rather than only the claim.
    """
    entries = []
    real = puzzle_review_module.solve

    def counting(*args, **kwargs):
        entries.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(puzzle_review_module, "solve", counting)

    store = Store(service=PuzzleReviewService(), mode="memory")
    believed = store.add(LINE_GRID, strategies=["simple_overlap"])
    entries.clear()
    assert store.service.approve_puzzle(believed) is True
    assert entries == [], "an approval of a normally stored puzzle entered the solver"

    # `line_logic` is not a name this solver writes (ADR-0029's rungs plus
    # `guess` are), so the stored list is not read as a statement about the
    # puzzle and the verdict is bought with one solve.
    unbelieved = store.add(LINE_GRID, strategies=["line_logic"])
    entries.clear()
    assert store.service.approve_puzzle(unbelieved) is True
    assert len(entries) == 1, (
        f"a row whose stored list no solver wrote cost {len(entries)} solves, "
        "expected exactly one"
    )


# --------------------------------------------------------------------------
# AC-394 — the bulk door
# --------------------------------------------------------------------------


def test_batch_approve_holds_back_branching_puzzles(tmp_path, admin_app) -> None:
    """AC-394: the sound ones approve, the branching ones keep their status.

    ``set_batch_status`` does not go through ``_set_status`` — it writes
    ``status`` in its own two loops — which is exactly how the bulk path came
    to lack the book protection the per-puzzle path had, once. So the counts
    are read off the outcome in both modes, the held-back rows' statuses are
    read back, and the report's sentence is asserted as a sentence: a number
    the owner cannot attribute is how six puzzles become "Approved 4".
    """
    _assert_the_fixtures_are_what_this_file_assumes()
    from nonogram.admin.app import _bulk_report

    report = Report()

    for store in both_modes(tmp_path):
        mode = store.mode
        batch = store.batch("mixed")
        branching = [store.add(GUESS_GRID, strategies=[], batch="mixed") for _ in range(2)]
        line = [store.add(LINE_GRID, strategies=[], batch="mixed") for _ in range(3)]

        outcome = store.service.set_batch_status(batch, PuzzleStatus.APPROVED)

        report.equal(mode, "approved count", outcome.changed, 3)
        report.equal(mode, "held back for guessing", outcome.needs_guessing, 2)
        report.equal(mode, "held back as unverifiable", outcome.unverifiable, 0)
        report.equal(mode, "counted as unchanged", outcome.unchanged, 0)
        report.equal(mode, "counted as in a book", outcome.in_book, 0)
        for puzzle_id in branching:
            report.equal(
                mode, "a held-back puzzle's status", store.status(puzzle_id),
                PuzzleStatus.DRAFT.value,
            )
        for puzzle_id in line:
            report.equal(
                mode, "an approved puzzle's status", store.status(puzzle_id),
                PuzzleStatus.APPROVED.value,
            )

        sentence = _bulk_report("Approved", outcome, "already approved")
        report.check(
            mode,
            f"the report does not state how many were held back: {sentence!r}",
            "2 held back: need guessing" in sentence,
        )
        report.check(
            mode,
            f"the report does not name what was approved: {sentence!r}",
            sentence.startswith("Approved 3 puzzles"),
        )

        # A second pass: now that three are approved, the three are
        # `unchanged` and the two are still held back — the counts stay
        # attributable rather than collapsing into one another.
        again = store.service.set_batch_status(batch, PuzzleStatus.APPROVED)
        report.equal(mode, "second pass changed", again.changed, 0)
        report.equal(mode, "second pass unchanged", again.unchanged, 3)
        report.equal(mode, "second pass held back", again.needs_guessing, 2)

    # A bulk REJECT of the same batch is ungated: the gate is the way in.
    store = both_modes(tmp_path)[0]
    batch = store.batch("reject")
    store.add(GUESS_GRID, strategies=[STRATEGY_GUESS], batch="reject")
    store.add(LINE_GRID, strategies=["simple_overlap"], batch="reject")
    rejected = store.service.set_batch_status(batch, PuzzleStatus.REJECTED)
    report.equal("memory/reject", "a bulk reject rejected everything", rejected.changed, 2)
    report.equal("memory/reject", "a bulk reject held something back",
                 rejected.needs_guessing, 0)

    # And the route the owner presses.
    route = _store_of(admin_app)
    batch_id = "bulk-route"
    admin_app.batch_generator.jobs[batch_id] = _a_complete_batch(batch_id)
    route.add(GUESS_GRID, strategies=[], batch_id=batch_id)
    route.add(LINE_GRID, strategies=[], batch_id=batch_id)
    response = admin_app.test_client().post(
        f"/batch/{batch_id}/approve-all", follow_redirects=True
    )
    report.equal("route", "the bulk route's status code", response.status_code, 200)
    body = response.get_data(as_text=True)
    report.check(
        "route", "the flashed sentence does not say what was held back",
        "1 held back: need guessing" in body,
    )

    report.done(at_least=34)


def _a_complete_batch(batch_id: str):
    """The smallest thing ``get_batch_status`` answers truthily for."""
    from nonogram.admin.batch_generator import BatchJob, BatchStatus

    return BatchJob(batch_id=batch_id, status=BatchStatus.COMPLETE, total_count=2)


def test_the_bulk_outcome_fields_are_not_double_counted(tmp_path) -> None:
    """Every puzzle of the batch lands in exactly one of the five counts.

    The defect the fields exist against: a held-back puzzle absorbed into
    ``unchanged`` makes the five numbers sum to the batch and still lie. This
    asserts the sum AND the attribution, because the sum alone is satisfied by
    any mislabelling.
    """
    for store in both_modes(tmp_path):
        batch = store.batch("sum")
        for _ in range(2):
            store.add(GUESS_GRID, strategies=[], batch="sum")
        for _ in range(2):
            store.add(LINE_GRID, strategies=[], batch="sum")
        booked = store.add(LINE_GRID, strategies=[], batch="sum")
        store.book(booked)

        outcome = store.service.set_batch_status(batch, PuzzleStatus.APPROVED)
        total = (
            outcome.changed
            + outcome.unchanged
            + outcome.in_book
            + outcome.needs_guessing
            + outcome.unverifiable
        )
        assert total == 5, f"{store.mode}: {outcome} does not account for 5 puzzles"
        assert outcome.changed == 2, f"{store.mode}: {outcome}"
        assert outcome.in_book == 1, f"{store.mode}: {outcome}"
        assert outcome.needs_guessing == 2, f"{store.mode}: {outcome}"


def test_the_outcome_grew_without_moving_what_was_there(tmp_path) -> None:
    """G-4: CARD-068's three counts keep their positions and their meanings.

    ``BulkOutcome`` is built positionally in two places in the store, so a
    field inserted rather than appended would silently re-point every existing
    reading. Asserted as the dataclass's own field order.
    """
    names = [f for f in BulkOutcome.__dataclass_fields__]
    assert names[:3] == ["changed", "unchanged", "in_book"], names
    assert names[3:] == ["needs_guessing", "unverifiable"], names
    assert BulkOutcome() == BulkOutcome(0, 0, 0, 0, 0)


# --------------------------------------------------------------------------
# AC-395 — what defaults to DENY
# --------------------------------------------------------------------------


def test_unknown_verdict_fails_closed(tmp_path, admin_app, monkeypatch) -> None:
    """AC-395: a puzzle whose verdict cannot be obtained is refused.

    **The load-bearing criterion, not the corner case.** The deployed service
    still grades with the pre-ADR-0029/R6 formula until it is redeployed, so
    for a puzzle created or edited in that window this door is the only reader
    of the fact — and an unreadable row is precisely the shape a pre-R6 write
    can leave. An approval is a claim of publishability and an unverifiable
    claim fails closed, which is INV-002's posture one door earlier.

    All three unknowns the criterion names are driven, in both store modes,
    and each is checked at the verdict, at the service door and at the stored
    status. The shape rule (wave 46) is why there is no fourth guess example
    here: the control for a DENY default is a puzzle whose verdict is
    *unknown*.
    """
    _assert_the_fixtures_are_what_this_file_assumes()
    report = Report()

    def unreadable(store: Store) -> str:
        puzzle_id = store.add(LINE_GRID, strategies=[])
        store.overwrite(puzzle_id, grid="not a grid at all", strategies_used=[])
        return puzzle_id

    def ambiguous(store: Store) -> str:
        puzzle_id = store.add(LINE_GRID, strategies=[])
        store.overwrite(puzzle_id, grid=AMBIGUOUS_GRID, strategies_used=[])
        return puzzle_id

    for store in both_modes(tmp_path):
        for case, plant in (("unreadable grid", unreadable), ("non-unique grid", ambiguous)):
            mode = f"{store.mode}/{case}"
            puzzle_id = plant(store)
            report.equal(
                mode, "the verdict",
                store.service.approvability_of(puzzle_id),
                Approvability.UNVERIFIABLE,
            )
            report.check(
                mode, "approve_puzzle approved an unverifiable puzzle",
                store.service.approve_puzzle(puzzle_id) is False,
            )
            report.equal(
                mode, "the refused row's status", store.status(puzzle_id),
                PuzzleStatus.DRAFT.value,
            )

        # The third unknown: a solve that does not conclude in budget. The
        # row is a real puzzle; what fails is the clock, and a timeout is the
        # one verdict that is a fact about a run rather than about a grid —
        # so it must not be cached, assumed or rounded down to "fine".
        mode = f"{store.mode}/timeout"
        puzzle_id = store.add(LINE_GRID, strategies=[])
        # The stored list has to be one no solver here wrote, or the gate
        # answers from it and never reaches the clock. `add_puzzle` fills an
        # empty list in from its own proving solve, so it is emptied after
        # the row exists — which is also the shape of the rows written before
        # the column was recorded.
        store.overwrite(puzzle_id, strategies_used=[])

        def timing_out(*args, **kwargs):
            raise SolverTimeout("the budget ran out")

        monkeypatch.setattr(puzzle_review_module, "solve", timing_out)
        try:
            report.equal(
                mode, "the verdict",
                store.service.approvability_of(puzzle_id),
                Approvability.UNVERIFIABLE,
            )
            report.check(
                mode, "approve_puzzle approved a puzzle whose solve timed out",
                store.service.approve_puzzle(puzzle_id) is False,
            )
            report.equal(
                mode, "the refused row's status", store.status(puzzle_id),
                PuzzleStatus.DRAFT.value,
            )
        finally:
            monkeypatch.undo()

        # The control, after the clock is honest again: the same row approves.
        report.check(
            mode, "the row could not be approved once the solve concluded",
            store.service.approve_puzzle(puzzle_id) is True,
        )

    # The bulk door holds the same posture, under its own count.
    store = both_modes(tmp_path)[0]
    batch = store.batch("unknown")
    broken = store.add(LINE_GRID, strategies=[], batch="unknown")
    store.overwrite(broken, grid="not a grid at all", strategies_used=[])
    store.add(LINE_GRID, strategies=[], batch="unknown")
    outcome = store.service.set_batch_status(batch, PuzzleStatus.APPROVED)
    report.equal("memory/bulk", "approved", outcome.changed, 1)
    report.equal("memory/bulk", "held back as unverifiable", outcome.unverifiable, 1)
    report.equal("memory/bulk", "held back for guessing", outcome.needs_guessing, 0)
    report.equal(
        "memory/bulk", "the unverifiable row's status", store.status(broken),
        PuzzleStatus.DRAFT.value,
    )

    # And the route says which refusal this is — the two messages are
    # distinct, because the owner's next move differs.
    route = _store_of(admin_app)
    broken = route.add(LINE_GRID, strategies=[])
    route.overwrite(broken, grid="not a grid at all", strategies_used=[])
    response = admin_app.test_client().post(
        f"/puzzle/{broken}/approve", headers={"Accept": "application/json"}
    )
    report.equal("route", "the status code", response.status_code, 409)
    message = response.get_json()["message"]
    report.check(
        "route", f"the refusal does not name the unverifiable case: {message!r}",
        Approvability.UNVERIFIABLE.value in message,
    )
    report.check(
        "route", f"the unverifiable refusal reads as the guess refusal: {message!r}",
        Approvability.NEEDS_GUESSING.value not in message,
    )
    report.equal(
        "route", "the refused row's status", route.status(broken),
        PuzzleStatus.DRAFT.value,
    )

    report.done(at_least=28)


def test_the_two_refusals_are_worded_apart(tmp_path) -> None:
    """One verdict vocabulary, three members, no two of them the same sentence.

    The messages live on :class:`Approvability` so the route, the flash and the
    bulk report say the same thing from one place. That only helps if the
    members really are distinguishable, which a shared constant does not
    guarantee by itself.
    """
    sentences = [member.value for member in Approvability]
    assert len(set(sentences)) == len(sentences), sentences
    assert Approvability.OK.value == "", "a passing verdict has nothing to say"
    assert Approvability.OK.refuses is False
    assert all(
        member.refuses for member in Approvability if member is not Approvability.OK
    )
    assert "guess" in Approvability.NEEDS_GUESSING.value
    assert "verif" in Approvability.UNVERIFIABLE.value


# --------------------------------------------------------------------------
# AC-396 — the edit door into the invariant
# --------------------------------------------------------------------------


def test_edit_refuses_a_branching_grid_behind_the_approved_door(tmp_path) -> None:
    """AC-396: a branching replacement is refused behind the approval door.

    The second way into the invariant. A status gate alone leaves it open: the
    row is already ``approved``, so no transition happens, and every approved
    row would be reachable by a posted edit carrying a grid the approval door
    would have refused.

    Both halves of the criterion, in both modes: the stored grid is unchanged
    after the refusal (not merely "an exception was raised"), and the same
    replacement stores onto a draft — because the rule is that a puzzle cannot
    leave draft carrying a branching grid, not that no such grid may be stored.
    """
    _assert_the_fixtures_are_what_this_file_assumes()
    report = Report()

    for store in both_modes(tmp_path):
        # The in-book arm is seeded at tier `hard` deliberately. A booked
        # puzzle is also protected by CARD-251's regrade refusal, which comes
        # first in `save_edited_grid` and would answer for a tier change
        # instead of for this card's rule — the row would be protected, by
        # another rule, and this test would assert nothing about FR-046. A
        # branching grid grades hard/100 since ADR-0029/R6, so a stored `hard`
        # is the seed that lets the regrade pass and this refusal be reached.
        for state, tier, arrange in (
            ("approved", "medium", lambda s, pid: s.service.approve_puzzle(pid)),
            (
                "in_book",
                "hard",
                lambda s, pid: (
                    s.book(pid),
                    s.overwrite(pid, status=PuzzleStatus.IN_BOOK.value),
                ),
            ),
        ):
            mode = f"{store.mode}/{state}"
            puzzle_id = store.add(
                LINE_GRID, strategies=["simple_overlap"], difficulty_tier=tier
            )
            arrange(store, puzzle_id)
            report.equal(mode, "the arranged status", store.status(puzzle_id), state)

            # The verify grades and shows: the owner learns the grade, and the
            # refusal is the store's (AC-396's own wording).
            store.service.verify_replacement_grid(puzzle_id, GUESS_GRID)
            with pytest.raises(GridNotApprovable) as refused:
                store.service.save_edited_grid(puzzle_id, GUESS_GRID, confirmed=True)
            report.check(
                mode, f"the refusal does not name the reason: {refused.value}",
                "needs guessing" in str(refused.value),
            )
            report.equal(
                mode, "the refusal's verdict", refused.value.verdict,
                Approvability.NEEDS_GUESSING,
            )
            report.equal(mode, "the stored grid moved", store.row(puzzle_id)["grid"], LINE_GRID)
            report.equal(
                mode, "a refused edit left a stamp",
                store.row(puzzle_id)["manually_edited_at"], None,
            )
            report.equal(
                mode, "the stored strategies moved",
                store.row(puzzle_id)["strategies_used"], ["simple_overlap"],
            )

        # The control: the same replacement onto a draft stores.
        mode = f"{store.mode}/draft"
        draft = store.add(LINE_GRID, strategies=["simple_overlap"])
        store.service.verify_replacement_grid(draft, GUESS_GRID)
        stored = store.service.save_edited_grid(draft, GUESS_GRID)
        report.check(mode, "the draft edit stored nothing", stored is not None)
        report.equal(mode, "the draft's grid", store.row(draft)["grid"], GUESS_GRID)
        report.check(
            mode, "the draft's strategies do not report the branch",
            STRATEGY_GUESS in store.row(draft)["strategies_used"],
        )
        # And now it cannot be approved — which is the whole rule, end to end.
        report.check(
            mode, "a draft carrying a branching grid could be approved",
            store.service.approve_puzzle(draft) is False,
        )

        # The other control: a line-solvable replacement onto an approved
        # puzzle stores. A refusal of every edit behind the door would pass
        # the assertions above.
        mode = f"{store.mode}/approved-control"
        approved = store.add(GUESS_GRID, strategies=["simple_overlap", STRATEGY_GUESS])
        store.overwrite(approved, status=PuzzleStatus.APPROVED.value)
        store.service.verify_replacement_grid(approved, LINE_GRID)
        report.check(
            mode, "a sound replacement was refused behind the door",
            store.service.save_edited_grid(approved, LINE_GRID, confirmed=True) is not None,
        )
        report.equal(mode, "the replacement's grid", store.row(approved)["grid"], LINE_GRID)

    report.done(at_least=36)


def test_the_edit_route_says_which_refusal_it_is(admin_app) -> None:
    """The refusal reaches the owner as a reason, not as a 500.

    409, like the booked conflict and unlike the grid refusals' 422: the grid
    is a fine puzzle and the request is well formed — it is the approved row
    underneath it that the replacement conflicts with.
    """
    store = _store_of(admin_app)
    puzzle_id = store.add(LINE_GRID, strategies=["simple_overlap"])
    assert store.service.approve_puzzle(puzzle_id) is True
    client = admin_app.test_client()

    verified = client.post(
        f"/puzzle/{puzzle_id}/edit/verify", json={"grid": GUESS_GRID}
    )
    assert verified.status_code == 200, verified.get_data(as_text=True)
    assert STRATEGY_GUESS in verified.get_json()["grade"]["strategies_used"]

    refusal = client.post(
        f"/puzzle/{puzzle_id}/edit", json={"grid": GUESS_GRID, "confirmed": True}
    )
    assert refusal.status_code == 409, refusal.get_data(as_text=True)
    body = refusal.get_json()
    assert body["ok"] is False
    assert body["reason"] == "needs_guessing", body
    assert "needs guessing" in body["message"], body
    assert store.row(puzzle_id)["grid"] == LINE_GRID


def test_the_edit_seam_leaves_the_stored_list_in_step_with_the_grid(tmp_path) -> None:
    """The gate's cost assumption, verified at the seam rather than restated.

    The gate re-solves only when the stored ``strategies_used`` is not
    solver-written, so an approval of a normally stored puzzle is an O(1)
    read. That is only true if the two-phase edit leaves the stored list in
    step with the stored grid — otherwise the gate reads a stale verdict off a
    replaced grid, which is a wrong answer rather than a slow one.
    """
    for store in both_modes(tmp_path):
        puzzle_id = store.add(LINE_GRID, strategies=["simple_overlap"])
        store.service.verify_replacement_grid(puzzle_id, GUESS_GRID)
        store.service.save_edited_grid(puzzle_id, GUESS_GRID)

        stored = store.row(puzzle_id)
        assert stored["grid"] == GUESS_GRID, store.mode
        assert STRATEGY_GUESS in stored["strategies_used"], (
            f"{store.mode}: the stored list does not report the branch the "
            "stored grid needs, so the gate would read a stale verdict"
        )
        # Believed without a re-solve, and still the right answer.
        assert PuzzleReviewService._is_strategies_list(stored["strategies_used"])
        assert store.service.approvability_of(puzzle_id) is Approvability.NEEDS_GUESSING


# --------------------------------------------------------------------------
# EC-051 — the writer set is DERIVED, and what is not derived defaults to DENY
# --------------------------------------------------------------------------

#: The tree the guard walks. ``src/nonogram/**`` per EC-051, from this file's
#: own location rather than from the working directory, so the guard measures
#: the checkout it is running inside.
SOURCE_ROOT = pathlib.Path(__file__).resolve().parent.parent / "src" / "nonogram"

#: The module that owns the ``puzzles`` table's status column.
STORE_MODULE = "src/nonogram/admin/puzzle_review.py"

#: FR-046's rule, as the symbols that implement it. A door "passes the gate"
#: when one of these is reachable on its call graph. Two entries rather than
#: one because the rule has two seams — the status transition and the edit
#: behind the door (AC-396) — and a door that reaches neither is ungated.
THE_GATE = frozenset(
    {
        f"{STORE_MODULE}:PuzzleReviewService._approvability",
        f"{STORE_MODULE}:PuzzleReviewService._refuse_a_grid_the_approval_door_would_not",
    }
)

#: The word a stored approved status is spelled with.
APPROVED_WORD = PuzzleStatus.APPROVED.value

#: The status words that are NOT the approved one. Derived from the enum, so a
#: fifth status added tomorrow cannot be read as "provably not approved" until
#: someone names it here.
NOT_APPROVED_WORDS = frozenset(
    member.value for member in PuzzleStatus if member is not PuzzleStatus.APPROVED
)
NOT_APPROVED_MEMBERS = frozenset(
    member.name for member in PuzzleStatus if member is not PuzzleStatus.APPROVED
)

#: The name of the ORM row class an approved status can be constructed into.
ROW_CONSTRUCTORS = frozenset({"Puzzle"})

#: Base classes a module-level class of the store inherits from to BE a
#: refusal — the ones ``puzzle_review`` actually uses. Written out rather than
#: matched on a name suffix, so a class called ``StatusValueError`` does not
#: become a refusal by its name alone.
REFUSAL_BASES = frozenset({"ValueError", "Exception", "NotUniquelySolvable", "SolverTimeout"})

#: Calls whose result is a container this body built, so a store into it is
#: not a store into durable state.
FRESH_CALLS = frozenset({"list", "dict", "set", "tuple", "sorted", "deepcopy", "copy"})

#: Methods that take a value *out* of a container. A removal cannot set a
#: status, so its argument is a key and not a payload — which is why
#: ``delete_puzzle``'s ``self.puzzles.pop(...)`` is not a status write and
#: needs no exemption. ``test_a_removal_is_not_a_status_write`` is the control.
REMOVERS = frozenset({"pop", "popitem", "remove", "clear", "discard"})


def _own_nodes(node):
    """Every node of this body, NOT descending into a nested function or class.

    So each symbol is judged on what it does itself. ``create_app`` holds
    every route of the panel as nested functions; walked whole, it would
    absorb all of them and one giant candidate would stand for sixty doors.
    A nested function is its own symbol and its caller reaches it through the
    call graph instead.
    """
    out, stack = [], list(ast.iter_child_nodes(node))
    while stack:
        current = stack.pop()
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        out.append(current)
        stack.extend(ast.iter_child_nodes(current))
    return out


def _symbols_of(tree, module):
    """``module:Owner.name`` -> FunctionDef, for every function at any depth."""
    out = {}

    def walk(node, prefix):
        for child in node.body:
            if isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[f"{prefix}{child.name}"] = child
                walk(child, f"{prefix}{child.name}.")

    walk(tree, f"{module}:")
    return out


def _fresh_names(nodes):
    """Locals bound to a container this body built, and never to anything else."""
    fresh, other = set(), set()
    for node in nodes:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = node.value
        built = isinstance(
            value,
            (ast.List, ast.Dict, ast.Set, ast.Tuple, ast.ListComp, ast.DictComp, ast.SetComp),
        ) or (
            isinstance(value, ast.Call)
            and (
                (isinstance(value.func, ast.Name) and value.func.id in FRESH_CALLS)
                or (isinstance(value.func, ast.Attribute) and value.func.attr in FRESH_CALLS)
            )
        )
        (fresh if built else other).add(target.id)
    return fresh - other


def _is_fresh(expression, fresh) -> bool:
    while isinstance(expression, (ast.Subscript, ast.Attribute)):
        expression = expression.value
    return isinstance(expression, ast.Name) and expression.id in fresh


def _provably_not_approved(value) -> bool:
    """Is this written value a constant that is NOT the approved status?

    The only way a status write leaves the candidate set without reaching the
    gate: the source says, in so many words, which status it writes, and it is
    not this one. A parameter, a variable, a call's result or a splat says
    nothing and is therefore denied.
    """
    if isinstance(value, ast.Attribute) and value.attr == "value":
        value = value.value
    if isinstance(value, ast.Attribute) and value.attr in NOT_APPROVED_MEMBERS:
        return True
    if isinstance(value, ast.Constant) and value.value in NOT_APPROVED_WORDS:
        return True
    return False


def _is_status_target(target) -> bool:
    if isinstance(target, ast.Attribute) and target.attr == "status":
        return True
    return (
        isinstance(target, ast.Subscript)
        and isinstance(target.slice, ast.Constant)
        and target.slice.value == "status"
    )


def _unreadable(argument) -> bool:
    """Is this payload argument one whose contents the source does not state?

    A bare name, an attribute or a subscript is a reference to something built
    elsewhere — ``puzzle.update(derived)``, which is production's own legacy
    write path and the shape that once left eight of nine real writers
    invisible to a guard. A literal or a call with explicit keywords is
    readable: the source says what is in it.
    """
    return isinstance(argument, (ast.Name, ast.Attribute, ast.Subscript, ast.Starred))


def _status_writes(node, *, in_store: bool):
    """Every place this body could write an approved status.

    Three shapes, each named so that what the guard sees can be told from what
    it does not:

    * **B1** a store into a ``status`` target — ``x.status = v``,
      ``x["status"] = v``, ``setattr(x, "status", v)`` — where ``v`` is not a
      provably non-approved constant;
    * **B2** a ``Puzzle(status=v)`` row constructor, or a ``{"status": v}``
      literal landing in a target this body did not build, with the same
      proviso on ``v``;
    * **B3** a write whose *payload* the source cannot read at all — a ``**``
      splat into a call, or ``.update(<a name>)`` on a receiver this body did
      not build — inside the module that owns the puzzles table. Nothing in
      the source says whether a status rides along in one of these, so they
      are denied.

    **This is a bound, not a completeness claim** — it is a catalogue, so what
    it does not name, it does not see. Named rather than left to look covered:
    reflection (``object.__setattr__``, ``operator.setitem``, a computed
    ``getattr``, ``exec``) is invisible to any ``.py``-AST guard and is evasion
    rather than the accident this guards against; a status written inside an
    imported third-party helper is not parsed here; and B3 is scoped to the
    store module, so an opaque payload write to a puzzle row from a module that
    never names ``PuzzleStatus`` is outside it. The second axis closes most of
    that third gap: a write of the *word* ``"approved"`` anywhere in the tree
    is seen by :func:`_approved_escapes` whatever shape it takes.
    """
    nodes = _own_nodes(node)
    fresh = _fresh_names(nodes)
    found = []
    for current in nodes:
        if isinstance(current, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = (
                current.targets if isinstance(current, ast.Assign) else [current.target]
            )
            if (
                any(_is_status_target(target) for target in targets)
                and not _provably_not_approved(current.value)
                and not all(_is_fresh(target, fresh) for target in targets)
            ):
                found.append(("B1", ast.unparse(current)[:70]))
            durable = any(
                isinstance(target, (ast.Attribute, ast.Subscript))
                and not _is_fresh(target, fresh)
                for target in targets
            )
            if durable:
                for value in _status_dict_values(current.value):
                    if not _provably_not_approved(value):
                        found.append(
                            ("B2", f"{{'status': ...}} into {ast.unparse(targets[0])[:40]}")
                        )
        if not isinstance(current, ast.Call):
            continue
        function = current.func
        if isinstance(function, ast.Name) and function.id == "setattr" and len(current.args) >= 2:
            if not isinstance(current.args[1], ast.Constant):
                if in_store:
                    found.append(("B3", "setattr(<a computed name>)"))
            elif (
                current.args[1].value == "status"
                and len(current.args) >= 3
                and not _provably_not_approved(current.args[2])
            ):
                found.append(("B1", "setattr(_, 'status', _)"))
        if isinstance(function, ast.Name) and function.id in ROW_CONSTRUCTORS:
            for keyword in current.keywords:
                if keyword.arg is None:
                    found.append(("B2", f"{function.id}(**<opaque>)"))
                elif keyword.arg == "status" and not _provably_not_approved(keyword.value):
                    found.append(("B2", f"{function.id}(status=<unprovable>)"))
        if in_store:
            if any(keyword.arg is None for keyword in current.keywords):
                found.append(("B3", f"** splat into {ast.unparse(function)[:40]}"))
            if (
                isinstance(function, ast.Attribute)
                and function.attr in ("update", "setdefault")
                and function.attr not in REMOVERS
                and current.args
                and _unreadable(current.args[0])
                and not _is_fresh(function.value, fresh)
            ):
                found.append(
                    ("B3", f".{function.attr}(<opaque>) on {ast.unparse(function.value)[:32]}")
                )
    return found


def _status_dict_values(value):
    """Every value a ``{"status": ...}`` literal inside ``value`` carries."""
    out = []
    for node in ast.walk(value):
        if isinstance(node, ast.Dict):
            for key, item in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "status":
                    out.append(item)
    return out


def _name_slots(nodes):
    """Node ids that sit in a NAME position: a dict key, a subscript index.

    ``{"approved": 0}`` and ``counts["approved"]`` name a bucket; they do not
    carry the status as a value, and treating them as if they did would make
    every tally in the tree a candidate writer.
    """
    out = set()
    for node in nodes:
        if isinstance(node, ast.Dict):
            out |= {id(key) for key in node.keys if key is not None}
        if isinstance(node, ast.Subscript):
            out.add(id(node.slice))
    return out


def _callee(function):
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return None


def _approved_escapes(node):
    """Where a value denoting the approved status can get out of this body.

    Axis A, and EC-051's own sentence: every *write* of
    ``PuzzleStatus.APPROVED``. The seeds are the three spellings the value can
    take — the enum member, ``PuzzleStatus["APPROVED"]``, and the bare word —
    and a seed in a name slot is not one. A seed is then followed forward
    through assignments to locals, and reported where it is stored into
    something this body did not build, splatted, or handed to a call.

    Taint does not cross a ``Compare`` (``row.status == APPROVED`` is the read
    this gate must not absorb) and does not propagate out of a call's *result*
    (``_bulk_report(outcome)`` is not the approved value). The escape itself is
    still recorded in both cases, so nothing is lost at the point where it
    matters; what is avoided is a cascade that would make the whole module one
    candidate.
    """
    nodes = _own_nodes(node)
    skip = _name_slots(nodes)
    seeds = set()
    for current in nodes:
        if id(current) in skip:
            continue
        if isinstance(current, ast.Attribute) and current.attr == PuzzleStatus.APPROVED.name:
            seeds.add(id(current))
        elif (
            isinstance(current, ast.Subscript)
            and isinstance(current.slice, ast.Constant)
            and current.slice.value == PuzzleStatus.APPROVED.name
        ):
            seeds.add(id(current))
        elif isinstance(current, ast.Constant) and current.value == APPROVED_WORD:
            seeds.add(id(current))
    if not seeds:
        return []
    carried = set()

    def tainted(expression, *, through_calls=True) -> bool:
        if expression is None:
            return False
        stack = [expression]
        while stack:
            current = stack.pop()
            if id(current) in seeds:
                return True
            if (
                isinstance(current, ast.Name)
                and isinstance(current.ctx, ast.Load)
                and current.id in carried
            ):
                return True
            if isinstance(current, ast.Compare):
                continue
            if isinstance(current, ast.Call) and not through_calls:
                continue
            stack.extend(ast.iter_child_nodes(current))
        return False

    for _ in range(4):  # a fixpoint over assignment chains; 4 is past the deepest
        for current in nodes:
            if isinstance(current, (ast.Assign, ast.AnnAssign)):
                targets = (
                    current.targets if isinstance(current, ast.Assign) else [current.target]
                )
                if tainted(current.value, through_calls=False):
                    carried |= {t.id for t in targets if isinstance(t, ast.Name)}
    fresh = _fresh_names(nodes)
    out = []
    for current in nodes:
        if isinstance(current, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = (
                current.targets if isinstance(current, ast.Assign) else [current.target]
            )
            if tainted(current.value):
                for target in targets:
                    if isinstance(target, (ast.Attribute, ast.Subscript)) and not _is_fresh(
                        target, fresh
                    ):
                        out.append(("store", ast.unparse(target)[:50], None))
        if isinstance(current, ast.Call):
            for keyword in current.keywords:
                if keyword.arg is None and tainted(keyword.value):
                    out.append(("splat", ast.unparse(current.func)[:50], _callee(current.func)))
            arguments = list(current.args) + [
                keyword.value for keyword in current.keywords if keyword.arg
            ]
            for argument in arguments:
                if tainted(argument):
                    out.append(("call", ast.unparse(current.func)[:50], _callee(current.func)))
    return out


def _refusal_constructors(trees):
    """``Class.__init__`` of the store's refusals — DERIVED, not listed.

    A refusal's ``__init__`` writes attributes on a **fresh exception**: the
    object it mutates was made by the ``raise`` standing in place of a write,
    so ``self.status = status`` there cannot reach a row. Recognised narrowly —
    every base must be a refusal base — so this cannot become a second
    default-allow; ``test_a_class_that_is_not_a_refusal_is_not_excused`` is the
    control.
    """
    out = set()
    for module, tree in trees.items():
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
            if not bases or len(bases) != len(node.bases):
                continue
            if not set(bases) <= REFUSAL_BASES:
                continue
            for member in node.body:
                if (
                    isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and member.name == "__init__"
                ):
                    out.add(f"{module}:{node.name}.__init__")
    return out


#: The one candidate that is allowed not to reach the gate, with its reason.
#:
#: **Every entry is machine-checked** by :func:`_cannot_approve`, which is the
#: half that makes this list safe to have: an entry must write no status of its
#: own, write no payload the source cannot read, and hand its approved-denoting
#: value to nothing in this tree that writes a status. All four real doors fail
#: that check and therefore cannot be silenced by being listed here —
#: ``test_no_real_door_could_be_excused_by_listing_it`` drives exactly that.
APPROVES_NOTHING = {
    "src/nonogram/admin/app.py:create_app.select_puzzles_for_book": (
        "the `?status=` filter default (CARD-166): the word reaches a query "
        "filter and a template context, never a row"
    ),
}


def _cannot_approve(name, analysis) -> list:
    """Why ``name`` could not approve anything, or the reasons it could.

    Empty means the exemption holds. A non-empty list is what disqualifies an
    entry on :data:`APPROVES_NOTHING`.
    """
    reasons = []
    for kind, shape in analysis["writes"][name]:
        reasons.append(f"writes a status itself ({kind}: {shape})")
    reaching = sorted(_tainted_callees(name, analysis) & analysis["status_writers"])
    if reaching:
        reasons.append(f"hands the approved value to a status writer: {reaching}")
    return reasons


def _tainted_callees(name, analysis) -> set:
    """Symbols in the tree that ``name`` hands an approved-denoting value to."""
    out = set()
    for kind, _shape, callee in analysis["escapes"][name]:
        if kind in ("call", "splat") and callee:
            out |= analysis["by_last"].get(callee, set())
    return out


def analyse(root=SOURCE_ROOT) -> dict:
    """One walk of ``src/nonogram/**``: symbols, writes, escapes, verdicts."""
    trees, symbols = {}, {}
    files = sorted(root.rglob("*.py"))
    for path in files:
        module = path.relative_to(root.parent.parent).as_posix()
        with warnings.catch_warnings():
            # `src/nonogram/sourcing/templates/dog_in_house.py` holds ASCII
            # art in a plain docstring and so parses with one
            # `SyntaxWarning: "\," is an invalid escape sequence`. It is a
            # fact about that file, not about this guard, and is named here
            # rather than silenced namelessly: parsing the tree must not add
            # a warning line to every run of the suite.
            warnings.simplefilter("ignore", SyntaxWarning)
            trees[module] = ast.parse(path.read_text(encoding="utf-8"))
        symbols.update(_symbols_of(trees[module], module))
    by_last = {}
    for name in symbols:
        by_last.setdefault(name.split(".")[-1], set()).add(name)
    refusals = _refusal_constructors(trees)
    # The modules that could write a `PuzzleStatus` value under that name,
    # derived from the tree rather than listed: a module that never mentions
    # the enum cannot write one of its members. `batch_generator`'s
    # `job.status` and `book_manager`'s `book.status` are other tables'
    # columns and are out of this rule's subject by that measurement.
    vocabulary = {
        module for module, tree in trees.items() if "PuzzleStatus" in ast.dump(tree)
    }
    writes, escapes = {}, {}
    for name, node in symbols.items():
        module = name.split(":")[0]
        escapes[name] = _approved_escapes(node)
        if name in refusals or module not in vocabulary:
            writes[name] = []
        else:
            writes[name] = _status_writes(node, in_store=module == STORE_MODULE)
    callees = {}
    for name, node in symbols.items():
        reached = set()
        for current in _own_nodes(node):
            if isinstance(current, ast.Call):
                reached |= by_last.get(_callee(current.func), set())
        callees[name] = reached - {name}
    direct = {name for name, found in writes.items() if found}
    status_writers = set(direct)
    changed = True
    while changed:
        changed = False
        for name in symbols:
            if name not in status_writers and callees[name] & status_writers:
                status_writers.add(name)
                changed = True
    candidates = ({name for name in symbols if escapes[name]} | direct) - refusals

    def reaches_the_gate(start: str) -> bool:
        seen, pending = set(), [start]
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            seen.add(name)
            if name in THE_GATE:
                return True
            pending.extend(callees.get(name, ()))
        return False

    analysis = {
        "files": [path.as_posix() for path in files],
        "trees": trees,
        "symbols": symbols,
        "by_last": by_last,
        "refusals": refusals,
        "vocabulary": vocabulary,
        "writes": writes,
        "escapes": escapes,
        "callees": callees,
        "direct": direct,
        "status_writers": status_writers,
        "candidates": candidates,
        "reaches_the_gate": reaches_the_gate,
    }
    analysis["ungated"] = sorted(
        name
        for name in candidates
        if name not in APPROVES_NOTHING and not reaches_the_gate(name)
    )
    return analysis


def _analyse_source(source: str, *, module=STORE_MODULE) -> dict:
    """The same analysis over a planted probe, so a control needs no file.

    A probe written into ``tests/`` would be collected, and
    ``tests/test_collected_names.py`` is default-deny over test names; a probe
    written into ``src/`` would be a real edit. Both controls below feed the
    analyser a string instead.
    """
    tree = ast.parse(source)
    trees = {module: tree}
    symbols = _symbols_of(tree, module)
    by_last = {}
    for name in symbols:
        by_last.setdefault(name.split(".")[-1], set()).add(name)
    refusals = _refusal_constructors(trees)
    writes = {
        name: (
            []
            if name in refusals
            else _status_writes(node, in_store=module == STORE_MODULE)
        )
        for name, node in symbols.items()
    }
    escapes = {name: _approved_escapes(node) for name, node in symbols.items()}
    callees = {}
    for name, node in symbols.items():
        reached = set()
        for current in _own_nodes(node):
            if isinstance(current, ast.Call):
                reached |= by_last.get(_callee(current.func), set())
        callees[name] = reached - {name}
    direct = {name for name, found in writes.items() if found}
    status_writers = set(direct)
    changed = True
    while changed:
        changed = False
        for name in symbols:
            if name not in status_writers and callees[name] & status_writers:
                status_writers.add(name)
                changed = True
    candidates = ({name for name in symbols if escapes[name]} | direct) - refusals
    return {
        "symbols": symbols,
        "by_last": by_last,
        "writes": writes,
        "escapes": escapes,
        "callees": callees,
        "direct": direct,
        "status_writers": status_writers,
        "candidates": candidates,
        "refusals": refusals,
    }


@pytest.fixture(scope="module")
def analysis() -> dict:
    """One analysis of the real tree, shared by the EC-051 assertions."""
    return analyse()


def test_every_approved_writer_passes_the_gate(analysis) -> None:
    """EC-051 (ADR-0032/R3, ADR-0039/R1-R2): default-DENY on an unlisted writer.

    **What is derived.** The writer set is not a list. Every function in
    ``src/nonogram/**`` is walked, and a function becomes a *candidate
    approver* the moment it either lets a value denoting the approved status
    escape its body (axis A — EC-051's own sentence) or writes a status whose
    value the source does not prove to be another one (axis B). A candidate
    must then reach :data:`THE_GATE` on its call graph, or stand on
    :data:`APPROVES_NOTHING` with a reason that :func:`_cannot_approve` can
    check. **A function added tomorrow that writes a status is a candidate the
    moment it exists and fails this by default** — it does not have to be
    recognised, remembered or added to anything.

    **What defaults to DENY, stated exactly.** An unprovable written value; an
    unreadable payload; an escape into any call at all; a module that names
    ``PuzzleStatus``. The three exits are all derived or checked: a provably
    non-approved constant, a structurally recognised refusal constructor, and
    the one exemption whose entry is machine-checked against the same
    predicate every real door fails.

    **What this proves and what it does not.** It proves the gate is on the
    call graph of everything that can write an approved status: *reachability*,
    not ordering. That the gate is in FRONT of the write is pinned
    behaviourally instead, by AC-393/394/395/396 above, each of which reads the
    stored row back after a refusal. Both halves are needed and neither stands
    in for the other.
    """
    assert analysis["files"], "no source files were parsed, so this proves nothing"
    assert len(analysis["symbols"]) > 500, (
        f"only {len(analysis['symbols'])} symbols were enumerated; the walk is "
        "not seeing the tree"
    )
    assert analysis["candidates"], "nothing was classified a writer, so this proves nothing"
    assert analysis["direct"], "no direct status writer was found at all"

    assert not analysis["ungated"], (
        "these can write an approved status without reaching the gate, and are "
        f"not on APPROVES_NOTHING: {analysis['ungated']} — every write of "
        "PuzzleStatus.APPROVED passes the gate (EC-051)"
    )


def test_the_four_doors_are_candidates_and_reach_the_gate(analysis) -> None:
    """A floor under the derivation, not the definition of the set.

    If the inversion above ever stopped classifying these as writers, it would
    pass by having nothing to check. Each of the four doors FR-046 names is
    required to be in the derived candidate set, to be unlistable as an
    exemption, and to reach the gate.
    """
    doors = [
        f"{STORE_MODULE}:PuzzleReviewService._set_status",
        f"{STORE_MODULE}:PuzzleReviewService.approve_puzzle",
        f"{STORE_MODULE}:PuzzleReviewService.set_batch_status",
        f"{STORE_MODULE}:PuzzleReviewService.save_edited_grid",
        "src/nonogram/admin/app.py:create_app.approve_batch_puzzles",
    ]
    missing = [name for name in doors if name not in analysis["symbols"]]
    assert not missing, f"these doors do not exist under these names: {missing}"
    not_candidates = [name for name in doors if name not in analysis["candidates"]]
    assert not not_candidates, f"classified as writing nothing: {not_candidates}"
    ungated = [name for name in doors if not analysis["reaches_the_gate"](name)]
    assert not ungated, f"doors that do not reach the gate: {ungated}"


def test_no_real_door_could_be_excused_by_listing_it(analysis) -> None:
    """The exemption list cannot be used to silence a failing door.

    The failure mode a hand-written exemption invites: a door goes red, the
    door's name goes on the list, the suite goes green. Every one of the five
    doors is required to be *disqualified* by :func:`_cannot_approve`, so
    listing it would red this test instead.
    """
    doors = [
        f"{STORE_MODULE}:PuzzleReviewService._set_status",
        f"{STORE_MODULE}:PuzzleReviewService.approve_puzzle",
        f"{STORE_MODULE}:PuzzleReviewService.set_batch_status",
        f"{STORE_MODULE}:PuzzleReviewService.save_edited_grid",
        "src/nonogram/admin/app.py:create_app.approve_batch_puzzles",
    ]
    excusable = [name for name in doors if not _cannot_approve(name, analysis)]
    assert not excusable, (
        f"these doors could be moved onto APPROVES_NOTHING and silenced: {excusable}"
    )


def test_every_exemption_is_still_unable_to_approve(analysis) -> None:
    """Each listed entry exists, and its reason is checked rather than read."""
    offences = {}
    for name, reason in sorted(APPROVES_NOTHING.items()):
        assert name in analysis["symbols"], f"{name} is exempted but does not exist"
        assert reason.strip(), f"{name} is exempted with no reason"
        reasons = _cannot_approve(name, analysis)
        if reasons:
            offences[name] = reasons
    assert not offences, (
        f"exemptions that are not excusable: {offences} — remove the entry and "
        "gate the door"
    )


def test_the_exemption_list_holds_only_what_it_has_to(analysis) -> None:
    """A pin on the size of the hand-written part, so it cannot grow quietly.

    One entry, measured. Counted from the list itself and cross-checked
    against the derived candidate set — an entry that is no longer a candidate
    is a stale exemption and is also a finding.
    """
    assert len(APPROVES_NOTHING) == 1, (
        f"APPROVES_NOTHING holds {len(APPROVES_NOTHING)} entries: "
        f"{sorted(APPROVES_NOTHING)}. Every entry is a door nobody gated — "
        "state why the set grew, in the entry and in the card"
    )
    stale = sorted(set(APPROVES_NOTHING) - analysis["candidates"])
    assert not stale, f"exempted but no longer classified a writer: {stale}"


# --- EC-051's controls: shapes the guard was NOT written from --------------

#: Each probe is a writer shape the guard's own code does not mention, fed in
#: as source so it never touches the tree. ``(label, source, the symbol that
#: must be denied)``.
_WRITER_PROBES = (
    (
        "the enum member, assigned straight onto a row",
        """
class PuzzleReviewService:
    def bless(self, puzzle_id):
        row = self._row(puzzle_id)
        row.status = PuzzleStatus.APPROVED.value
        return True
""",
        "PuzzleReviewService.bless",
    ),
    (
        "the bare word, with no enum anywhere",
        """
class PuzzleReviewService:
    def bless(self, puzzle_id):
        self.puzzles[puzzle_id]["status"] = "approved"
        return True
""",
        "PuzzleReviewService.bless",
    ),
    (
        "a caller-supplied status: nothing in the source names the approved one",
        """
class PuzzleReviewService:
    def force(self, puzzle_id, new_status):
        row = self._row(puzzle_id)
        row.status = new_status
        return True
""",
        "PuzzleReviewService.force",
    ),
    (
        "setattr, so the written column's name is a string",
        """
class PuzzleReviewService:
    def bless(self, puzzle_id):
        setattr(self._row(puzzle_id), "status", PuzzleStatus.APPROVED.value)
""",
        "PuzzleReviewService.bless",
    ),
    (
        "the subscript spelling of the enum member",
        """
class PuzzleReviewService:
    def bless(self, puzzle_id):
        return self._set_it(puzzle_id, PuzzleStatus["APPROVED"])

    def _set_it(self, puzzle_id, status):
        self.puzzles[puzzle_id]["status"] = status.value
""",
        "PuzzleReviewService.bless",
    ),
    (
        "a whole row payload built around the word",
        """
class PuzzleReviewService:
    def bless(self, puzzle_id, row):
        self.puzzles[puzzle_id] = {**row, "status": "approved"}
""",
        "PuzzleReviewService.bless",
    ),
    (
        "a row constructed approved at insert time",
        """
class PuzzleReviewService:
    def seed(self, db, grid, wanted):
        db.add(Puzzle(grid=grid, status=wanted))
""",
        "PuzzleReviewService.seed",
    ),
    (
        "an opaque payload: the source does not say what is in it",
        """
class PuzzleReviewService:
    def bless(self, puzzle_id, changes):
        self.puzzles[puzzle_id].update(changes)
""",
        "PuzzleReviewService.bless",
    ),
    (
        "a module-level function, outside the class entirely",
        """
def bless_everything(store):
    for row in store.rows():
        row.status = PuzzleStatus.APPROVED.value
""",
        "bless_everything",
    ),
    (
        "a nested function inside a route, which is how app.py is shaped",
        """
def create_app():
    @app.route("/bless/<puzzle_id>", methods=["POST"])
    def bless(puzzle_id):
        store.rows[puzzle_id]["status"] = "approved"
        return "", 200
""",
        "create_app.bless",
    ),
)


@pytest.mark.parametrize(
    "label,source,symbol", _WRITER_PROBES, ids=[probe[0] for probe in _WRITER_PROBES]
)
def test_a_writer_shape_the_guard_was_not_written_from_is_denied(label, source, symbol) -> None:
    """ADR-0039/R1's controls: caught WITH the mechanism, by shape.

    Ten writer shapes, none of which appears in the guard's own source, each
    required to land in the derived candidate set and to be refused the
    exemption. The eighth is the one that matters most for the default: it
    writes a payload the source cannot read, which is the shape that once left
    eight of nine real write paths silently exempt from a sibling guard.
    """
    probe = _analyse_source(source)
    qualified = f"{STORE_MODULE}:{symbol}"
    assert qualified in probe["symbols"], (
        f"the probe did not even parse into {qualified}: {sorted(probe['symbols'])}"
    )
    assert qualified in probe["candidates"], (
        f"{label}: classified as writing nothing — "
        f"writes={probe['writes'][qualified]} escapes={probe['escapes'][qualified]}"
    )
    assert _cannot_approve(qualified, probe), (
        f"{label}: could be excused onto APPROVES_NOTHING"
    )


#: Shapes that must NOT be absorbed. A guard that denied everything would pass
#: every control above and be worthless, so the reads are controls too.
_READ_PROBES = (
    (
        "a comparison against the approved status",
        """
class PuzzleReviewService:
    def is_approved(self, puzzle_id):
        return self.get_puzzle(puzzle_id)["status"] == PuzzleStatus.APPROVED.value
""",
        "PuzzleReviewService.is_approved",
    ),
    (
        "a tally bucket named for the status",
        """
class PuzzleReviewService:
    def counts(self):
        tally = {"approved": 0, "draft": 0}
        for row in self.puzzles.values():
            if row["status"] in tally:
                tally[row["status"]] += 1
        return tally
""",
        "PuzzleReviewService.counts",
    ),
    (
        "a query filtered on the approved status",
        """
class PuzzleReviewService:
    def how_many(self, db):
        return db.query(Puzzle).filter(Puzzle.status == PuzzleStatus.APPROVED.value).count()
""",
        "PuzzleReviewService.how_many",
    ),
    (
        "a status written that is provably another one",
        """
class PuzzleReviewService:
    def park(self, puzzle_id):
        self.puzzles[puzzle_id]["status"] = PuzzleStatus.DRAFT.value
""",
        "PuzzleReviewService.park",
    ),
    (
        "a row inserted as a draft, which is what add_puzzle does",
        """
class PuzzleReviewService:
    def seed(self, db, grid):
        db.add(Puzzle(grid=grid, status=PuzzleStatus.DRAFT.value))
""",
        "PuzzleReviewService.seed",
    ),
)


@pytest.mark.parametrize(
    "label,source,symbol", _READ_PROBES, ids=[probe[0] for probe in _READ_PROBES]
)
def test_a_read_is_not_absorbed_into_the_writer_set(label, source, symbol) -> None:
    """ADR-0039/R1's other direction: missed WITHOUT a write to find.

    A guard that classified every mention as a write would satisfy every
    writer control and tell nobody anything. These five shapes have to stay
    out of the candidate set — and the fourth and fifth are the edge: one
    character apart from a writer, and the only thing separating them is that
    the source names which status it writes.
    """
    probe = _analyse_source(source)
    qualified = f"{STORE_MODULE}:{symbol}"
    assert qualified in probe["symbols"], sorted(probe["symbols"])
    assert qualified not in probe["candidates"], (
        f"{label}: a read was classified a writer — "
        f"writes={probe['writes'][qualified]} escapes={probe['escapes'][qualified]}"
    )


def test_a_removal_is_not_a_status_write(analysis) -> None:
    """:data:`REMOVERS`, as an assertion rather than as a comment.

    ``delete_puzzle``'s ``self.puzzles.pop(puzzle_id)`` is the live instance:
    a removal cannot set a status, so its argument is a key and not a payload,
    and the method needs no exemption. The control is the one-word difference
    — the same shape with ``update`` instead of ``pop`` IS denied.
    """
    assert f"{STORE_MODULE}:PuzzleReviewService.delete_puzzle" not in analysis["candidates"]

    removal = _analyse_source(
        """
class PuzzleReviewService:
    def drop(self, puzzle_id):
        self.puzzles.pop(puzzle_id, None)
"""
    )
    assert f"{STORE_MODULE}:PuzzleReviewService.drop" not in removal["candidates"]

    payload = _analyse_source(
        """
class PuzzleReviewService:
    def drop(self, puzzle_id):
        self.puzzles.update(puzzle_id)
"""
    )
    assert f"{STORE_MODULE}:PuzzleReviewService.drop" in payload["candidates"], (
        "the one-word control did not bite, so REMOVERS is excusing more than "
        "removals"
    )


def test_a_class_that_is_not_a_refusal_is_not_excused() -> None:
    """The derived refusal exclusion cannot become a second default-allow.

    A refusal's ``__init__`` is excused because the object it writes was made
    by the ``raise``. The recognition is structural — every base must be a
    refusal base — so a class that merely looks like one is not excused, and
    its ``self.status = ...`` stays a candidate.
    """
    refusal = _analyse_source(
        """
class GridNotApprovable(ValueError):
    def __init__(self, message, *, status):
        super().__init__(message)
        self.status = status
"""
    )
    assert f"{STORE_MODULE}:GridNotApprovable.__init__" in refusal["refusals"]
    assert f"{STORE_MODULE}:GridNotApprovable.__init__" not in refusal["candidates"]

    impostor = _analyse_source(
        """
class StatusWriter(SomeBase):
    def __init__(self, message, *, status):
        self.status = status
"""
    )
    assert f"{STORE_MODULE}:StatusWriter.__init__" not in impostor["refusals"]
    assert f"{STORE_MODULE}:StatusWriter.__init__" in impostor["candidates"], (
        "a class that is not a refusal was excused as one"
    )


def test_the_modules_in_the_status_vocabulary_are_measured(analysis) -> None:
    """The scope of axis B, as a measurement rather than a claim.

    Axis B is scoped to the modules that name ``PuzzleStatus``, which is how
    ``batch_generator``'s ``job.status`` and ``book_manager``'s ``book.status``
    — other tables' columns — stay out of this rule's subject without being
    hand-excluded. The set is derived from the trees, and this asserts both
    what is in it and what the measurement excluded, so a module that starts
    importing the enum joins the rule's scope and is seen.
    """
    assert STORE_MODULE in analysis["vocabulary"]
    assert "src/nonogram/admin/app.py" in analysis["vocabulary"]
    for outside in (
        "src/nonogram/admin/batch_generator.py",
        "src/nonogram/admin/book_manager.py",
    ):
        assert outside in {path for path in analysis["trees"]}, outside
        assert outside not in analysis["vocabulary"], (
            f"{outside} now names PuzzleStatus, so axis B covers it and its "
            "status writes must reach the gate or be exempted"
        )
    # And the bound said out loud: a `status` write in one of those modules is
    # invisible to axis B. Axis A still sees the word itself.
    outside_probe = _analyse_source(
        """
def bless(row):
    row.status = PuzzleStatus.APPROVED.value
""",
        module="src/nonogram/admin/book_manager.py",
    )
    name = "src/nonogram/admin/book_manager.py:bless"
    assert outside_probe["escapes"][name], (
        "axis A does not see the enum member outside the store module, which "
        "would make the vocabulary scoping a hole rather than a narrowing"
    )


def _silenced(refs, namespace) -> list:
    """Refs whose function exists but carries a skip mark, so it never runs.

    Review cycle 1's F-001. Resolving a ref to a module-level callable proves
    the function *exists*; it does not prove the criterion is checked. A
    ``@pytest.mark.skip`` above any of the five left
    :func:`test_the_registrys_check_refs_for_this_card_all_resolve` green and
    the whole file reporting "36 passed, 1 skipped" — the model would read the
    criterion as mechanically verified while the gate it names never executed.
    That is the same defect as a dead ref, one level in.

    Separate from the resolve test so that
    :func:`test_a_skipped_criterion_is_not_a_resolved_one` can drive it over a
    synthetic namespace and prove it discriminates, rather than asserting a
    property of a tree where no skip mark exists.
    """
    out = []
    for ref in refs:
        name = ref.split("::", 1)[1]
        function = namespace.get(name)
        if function is None:
            continue
        marks = getattr(function, "pytestmark", ())
        if any(getattr(mark, "name", "") in ("skip", "skipif") for mark in marks):
            out.append(ref)
    return out


def test_the_registrys_check_refs_for_this_card_all_resolve() -> None:
    """Every ``tests/test_approval_guess_gate.py::…`` the model names is here.

    The defect this closes is the one this card arrived with, and it is the
    one the board has spent the week on: a ref that reads as mechanically
    checked while nothing backs it. FR-046's AC-393..396 and EC-051 named node
    ids in a file that did not exist, and ADR-0032/R3's check was held as a
    `review-lens` for exactly that reason.

    Writing the tests is only half the fix. **Measured on this branch**: with
    all five collected and passing, the architecture validator still reported
    five DEAD check refs, because it matches the whole ``path::name`` string
    with ``git grep -lw`` and that string appeared in no code file. So the
    other half is the docstring table above — and this test, in both
    directions and derived from the registry rather than from a list kept
    here:

    #. every ref ``meta/architecture/requirements.yml`` points at this module
       resolves to a module-level function in it — a renamed test reds here
       instead of going quietly dead in the model;
    #. every one of them is written out in this module's docstring, which is
       what the validator's ``git grep`` actually reads, so a ref cannot be
       alive in pytest and dead in the model at the same time;
    #. and the same for ADR-0032/R3's own check ref, which is this card's
       ``flip``: the rule and the registry name the same node id, so neither
       can drift from the test alone.

    The registry is parsed with a regex rather than a YAML library: there is
    no YAML parser in the dependency baseline (ADR-0006/R1), and the shape
    being read is one line.
    """
    import re

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    module = pathlib.Path(__file__).resolve().relative_to(repo_root).as_posix()
    pattern = rf"({re.escape(module)}::[A-Za-z_][A-Za-z0-9_]*)"

    registry = (repo_root / "meta" / "architecture" / "requirements.yml").read_text(
        encoding="utf-8"
    )
    refs = sorted(set(re.findall(pattern, registry)))
    # Five: AC-393..396 and EC-051. Counted from the registry rather than
    # restated, so a sixth joining FR-046 is seen rather than assumed away.
    assert len(refs) == 5, refs

    defined = {
        name
        for name, value in globals().items()
        if name.startswith("test_")
        and callable(value)
        and getattr(value, "__module__", "") == __name__
    }
    assert len(defined) >= 15, sorted(defined)

    missing = [ref for ref in refs if ref.split("::", 1)[1] not in defined]
    assert missing == [], missing

    # Existing is not running — see :func:`_silenced`.
    silenced = _silenced(refs, globals())
    assert silenced == [], (
        "these refs resolve to a function that is skipped, so the criterion "
        f"they name is NOT checked however green the suite is: {silenced}"
    )

    docstring = __doc__ or ""
    unnamed = [ref for ref in refs if ref not in docstring]
    assert unnamed == [], (
        "these refs resolve in pytest but the validator's git grep will not "
        f"find their node id in any code file: {unnamed}"
    )

    # And the ADR rule this card flipped out of `review-lens`.
    rule = (
        repo_root
        / "meta"
        / "architecture"
        / "decisions"
        / "adr"
        / "0032-admin-storage-guarantees.md"
    ).read_text(encoding="utf-8")
    rule_refs = sorted(set(re.findall(pattern, rule)))
    assert f"{module}::test_every_approved_writer_passes_the_gate" in rule_refs, rule_refs
    unnamed_rule = [ref for ref in rule_refs if ref not in docstring]
    assert unnamed_rule == [], (
        f"ADR-0032/R3 names node ids this module's docstring does not: {unnamed_rule}"
    )


def test_a_skipped_criterion_is_not_a_resolved_one() -> None:
    """:func:`_silenced` discriminates, and is not simply returning nothing.

    The control this card's own bar demands: a guard added because a hole was
    found must be shown to close it, and shown not to be vacuous. At HEAD no
    function in this module carries a skip mark, so asserting over the real
    tree would pass whatever ``_silenced`` did — including ``return []``.
    So the two skip spellings and a live function are driven over a synthetic
    namespace instead, and the live five are checked separately.
    """
    module = pathlib.Path(__file__).resolve()
    module = module.relative_to(module.parent.parent).as_posix()

    # The marks are attached by ASSIGNING ``pytestmark``, the way pytest
    # itself stores a decorator's result, and NOT by writing
    # ``@pytest.mark.skipif(...)`` here. CARD-238's detector
    # (``tests/test_suite_profile.py::_conditional_silences``) AST-walks every
    # guarded source for a ``skipif`` decorator and reports it **whatever it
    # is keyed on** — deliberately wider than host state — so a decorator in
    # this control registers as a new host-state silence anywhere in the tree
    # and reds
    # ``test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones``.
    # That guard is right and stricter than this test: the fix is to stop
    # writing the decorator, NOT to add this probe to its measured baseline.
    # (The CARD-291 merge gate caught exactly that, with the decorator form
    # here, after review cycle 1 — a round the reviewer's impact scope never
    # reached.) The marks below are still real ``Mark`` objects, so this
    # control would still fail if :func:`_silenced` read the wrong attribute.
    def probe_skipped() -> None:
        pass

    def probe_skipif() -> None:
        pass

    def probe_live() -> None:
        pass

    probe_skipped.pytestmark = [pytest.mark.skip("probe").mark]
    probe_skipif.pytestmark = [pytest.mark.skipif(True, reason="probe").mark]

    namespace = {
        "probe_skipped": probe_skipped,
        "probe_skipif": probe_skipif,
        "probe_live": probe_live,
    }
    refs = [f"{module}::{name}" for name in namespace]

    # Both spellings are caught -- `skipif` because a condition that is True
    # today is a skip today, whatever it reads like.
    assert _silenced([refs[0]], namespace) == [refs[0]]
    assert _silenced([refs[1]], namespace) == [refs[1]]
    # And the live one is NOT caught, which is what stops a deny-everything
    # version of this helper from passing the two assertions above.
    assert _silenced([refs[2]], namespace) == []
    # All three at once, so the helper is not order-dependent.
    assert _silenced(refs, namespace) == [refs[0], refs[1]]

    # A ref naming nothing is the resolve test's `missing` case, not this
    # one's: `_silenced` must not claim it, or the two assertions would
    # overlap and either could stand in for the other.
    assert _silenced([f"{module}::probe_absent"], namespace) == []
