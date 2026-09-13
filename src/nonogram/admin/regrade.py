"""CARD-077 — re-grade every stored puzzle under ADR-0029's ladder scale.

The one question this module answers: *what would this row's grade be if it
were graded today, by the pipeline that grades a puzzle now?* — and, on the
write path, it makes that the row's grade.

Why the stored grades have to be replaced rather than left alone
---------------------------------------------------------------
Every ``puzzles`` row carries a ``difficulty_score`` and a
``difficulty_tier``. They did not come from :mod:`nonogram.difficulty`. They
were written by ``admin/image_to_puzzle.create_puzzle_from_image``, a private
derivation that read the *grid extent* and never called the solver at all —
CARD-076 deleted it as an ADR-0025/R2 violation. So the re-grade is not "old
formula to new formula"; it is "a number that was never about the puzzle's
reasoning, to one that is". Book assembly reads ``difficulty_tier`` to print a
difficulty breakdown, so leaving the rows as they are means shipping a book
whose printed grades are about nothing.

The old values are not thrown away: they move to ``legacy_difficulty_score``
and ``legacy_difficulty_tier`` (migration 006), which stay until the owner has
reviewed the new distribution. Dropping them is a later card.

What the batch does to one row
------------------------------
Exactly one solve, and everything graded comes out of it (ADR-0029/R2)::

    stored grid -> clues.compute_clues -> solver.solve(deadline=...) -> signals
                -> difficulty.score_difficulty + difficulty.classify

The clues are re-derived from the stored ``grid`` rather than read from the
stored ``clues_rows``/``clues_cols``: those columns are display copies, and
CARD-051's rule is that the one encoder is :func:`nonogram.clues.compute_clues`.
Re-deriving also means a row whose stored clues had drifted from its grid is
graded by what the grid actually is.

Nothing here decides a tier. :func:`nonogram.difficulty.classify` does, and it
is handed ``(score, branch_nodes)`` from that same solve — which is also how
``guess`` gets onto the strategies list without this module reading
``branch_nodes`` to reach a verdict of its own (ADR-0025/R2, guardrail G-3).

What the batch refuses to do
----------------------------
A row is re-graded only if its grid is a real puzzle. If the clue set has 0 or
>= 2 solutions (CON-005: the solver is the uniqueness authority), if the solve
runs past its deadline (ADR-0011), or if the stored grid is not a readable
grid at all, the row is **left exactly as it is** — not marked, not cleared,
not partially written — and appears in the report with its reason. A grade is
a claim about a puzzle, and a clue set with two solutions is not one.

"Not a readable grid" means the wrong *shape* — not a list, empty, ragged, or
holding an empty row. Cell values are read for truthiness rather than type
checked; :func:`_as_grid` says why.

Dry run and write are one code path
-----------------------------------
:func:`regrade` takes ``dry_run`` and runs the identical loop either way; the
flag gates only the three assignments at the end of a row's turn. That is what
makes the confirmation page's report the report of the run it is confirming,
rather than a second implementation that could disagree with it. In dry-run
mode the session is rolled back before returning, so nothing this function did
is even committable.

Determinism (NFR-007, CON-014, ADR-0015)
----------------------------------------
A row's new grade is a pure function of its stored grid. No clock reading
reaches it: :class:`~nonogram.solver.SolveSignals` carries
``elapsed_seconds``, but :class:`nonogram.difficulty.SolverSignals` — the
protocol the scorer grades through — does not have the member, so the score
*cannot* read it. The deadline is the one clock in the module and it can only
decide whether a row is graded, never how. Running the batch twice over the
same rows therefore produces byte-identical rows.
"""

from __future__ import annotations

import math
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.orm import Session

from nonogram.clues import compute_clues
from nonogram.db.models import Puzzle
from nonogram.difficulty import (
    SCORE_MAX,
    SCORE_MIN,
    Tier,
    classify,
    score_difficulty,
    tier_of_record,
)
from nonogram.errors import SolverTimeout
from nonogram.orchestrator import GENERATION_BUDGET_SECONDS
from nonogram.solver import MANY, solve

__all__ = [
    "NO_LEGACY_TIER",
    "Grade",
    "RegradeReport",
    "RowOutcome",
    "Skip",
    "SkipReason",
    "grade_stored_grid",
    "regrade",
]


#: What ``legacy_difficulty_tier`` holds for a row that had **no** tier at all
#: when the batch first re-graded it.
#:
#: The point is that it is not ``NULL``. "Has this row's original grade already
#: been captured?" is answered by ``legacy_difficulty_tier IS NOT NULL``, and a
#: capture that wrote ``NULL`` for a row with no original tier would leave that
#: question answering "no" forever — so the *second* run would capture the
#: values the *first* run wrote, and the legacy columns would quietly hold
#: ADR-0029 grades presented as pre-run ones. Writing a non-NULL "there was
#: nothing here" instead makes the capture provably once-per-row
#: (:func:`_capture_legacy_grade`), which is AC-B's real requirement rather
#: than the common case of it.
#:
#: It reads back as "not a tier" through
#: :func:`nonogram.difficulty.tier_of_record`, which is exactly true.
NO_LEGACY_TIER = ""


class SkipReason(StrEnum):
    """Why a row was left alone. The values are what the report prints."""

    #: CON-005: the clue set has 0 or >= 2 solutions, so it is not a puzzle and
    #: has no grade. Never rewritten, never marked — cleaning these rows up is
    #: CARD-080's decision to make, not this batch's.
    NOT_UNIQUE = "not uniquely solvable"
    #: ADR-0011: the solve ran past its deadline, so there is no verdict. A
    #: timeout is a fact about this run, not about the puzzle — the row is
    #: unchanged and a later run with more budget may well grade it.
    TIMED_OUT = "solve exceeded its deadline"
    #: The stored ``grid`` is not a rectangular, non-empty grid of booleans, so
    #: there is nothing to encode. A data defect, reported rather than guessed
    #: at.
    UNREADABLE_GRID = "stored grid is not a readable grid"


@dataclass(frozen=True, slots=True)
class Grade:
    """What one solve says a row's three graded columns should be."""

    #: ADR-0029's 0..100 number, as the ``difficulty_score`` column's integer.
    score: int
    #: :func:`nonogram.difficulty.classify`'s verdict for that same solve.
    tier: Tier
    #: FR-029's ordered strategies list: the rungs the solve used, plus
    #: ``guess`` when the tier says the search branched.
    strategies: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Skip:
    """Why a row has no :class:`Grade`, in the report's own words."""

    reason: SkipReason
    #: The specifics — the solution count, the malformation, the budget.
    detail: str

    def __str__(self) -> str:
        return f"{self.reason.value} ({self.detail})"


@dataclass(frozen=True, slots=True)
class RowOutcome:
    """One row's turn in the batch — the unit the report is built from."""

    puzzle_id: str
    puzzle_name: str | None
    width: int
    height: int
    old_score: int | None
    old_tier: Tier | None
    #: The raw stored tier text, kept beside :attr:`old_tier` because a row can
    #: carry a spelling that is not a tier at all, and the report should say so
    #: rather than print a blank.
    old_tier_text: str | None
    grade: Grade | None
    skip: Skip | None

    @property
    def regraded(self) -> bool:
        return self.grade is not None

    @property
    def moved(self) -> bool:
        """Did this row's tier change? False for a skipped row."""
        return self.grade is not None and self.grade.tier is not self.old_tier

    @property
    def extent(self) -> str:
        return f"{self.width}x{self.height}"


@dataclass(frozen=True, slots=True)
class RegradeReport:
    """The whole run, as the confirmation page and the tests both read it.

    Built the same way on both paths, because both paths are the same loop —
    so the report the owner confirms is the report of the run they confirmed.
    """

    dry_run: bool
    outcomes: tuple[RowOutcome, ...]

    @property
    def row_count(self) -> int:
        return len(self.outcomes)

    @property
    def regraded(self) -> tuple[RowOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if outcome.regraded)

    @property
    def skipped(self) -> tuple[RowOutcome, ...]:
        """The rows left untouched, in the order the batch met them.

        First-class, not a footnote: a skipped row keeps a grade nobody has
        checked, and the count is the number of stored rows this card could not
        vouch for.
        """
        return tuple(outcome for outcome in self.outcomes if not outcome.regraded)

    @property
    def distribution(self) -> Counter[Tier]:
        """The new tier distribution over the rows that were graded.

        A :class:`~collections.Counter`, so every member of :class:`Tier` reads
        0 rather than raising — including ``GUESS``, which is the tier a
        breakdown that predates ADR-0025 would silently drop.
        """
        return Counter(outcome.grade.tier for outcome in self.regraded)

    @property
    def old_distribution(self) -> Counter[Tier]:
        """The same rows' tiers before the run — the other half of the picture."""
        return Counter(
            outcome.old_tier for outcome in self.regraded if outcome.old_tier is not None
        )

    @property
    def moves(self) -> Counter[tuple[Tier | None, Tier]]:
        """``(old tier, new tier) -> count`` over the graded rows."""
        return Counter(
            (outcome.old_tier, outcome.grade.tier)
            for outcome in self.regraded
            if outcome.grade is not None
        )

    @property
    def skips_by_reason(self) -> Counter[SkipReason]:
        return Counter(
            outcome.skip.reason for outcome in self.skipped if outcome.skip is not None
        )

    @property
    def unchanged_count(self) -> int:
        """Graded rows whose tier came out the same as the stored one."""
        return sum(1 for outcome in self.regraded if not outcome.moved)


def grade_stored_grid(
    grid: object,
    *,
    deadline: float | None = None,
) -> Grade | Skip:
    """Grade one stored grid, or say why it cannot be graded. One solve.

    Args:
        grid: The ``puzzles.grid`` column as it comes back from the DB — a
            JSON-decoded list of equal-length, non-empty rows of booleans.
            Typed ``object`` deliberately: this is data off a disk that no
            schema constrains, so "is it even a grid" is part of the question
            rather than a precondition the caller must have checked.
        deadline: ADR-0011's absolute :func:`time.monotonic` reading for this
            one solve, or ``None`` to run to completion.

    Returns:
        A :class:`Grade` when the clue set has exactly one solution, and a
        :class:`Skip` otherwise. Never raises for bad data: a malformed row is
        a thing to report, and a batch that died on row 3 of 36 would leave the
        table half re-graded.

    Pure apart from ``deadline`` (and the clock only decides *whether* a grade
    comes back, never *which* one): no I/O, no randomness, no module state.
    """
    rows = _as_grid(grid)
    if rows is None:
        return Skip(
            SkipReason.UNREADABLE_GRID,
            "expected a non-empty rectangle of booleans",
        )

    try:
        row_clues, column_clues = compute_clues(rows)
    except (TypeError, ValueError) as exc:  # pragma: no cover - _as_grid screens these
        return Skip(SkipReason.UNREADABLE_GRID, str(exc))

    try:
        result = solve(row_clues, column_clues, deadline=deadline)
    except SolverTimeout:
        return Skip(SkipReason.TIMED_OUT, "no verdict; the row is left as it was")
    except ValueError as exc:  # pragma: no cover - compute_clues emits valid clues
        return Skip(SkipReason.UNREADABLE_GRID, str(exc))

    if result.solution_count != 1:
        counted = "2 or more" if result.solution_count == MANY else "0"
        return Skip(
            SkipReason.NOT_UNIQUE,
            f"the clue set has {counted} solutions, so it has no grade",
        )

    score = score_difficulty(result.signals)
    tier = classify(score, result.signals.branch_nodes)
    return Grade(
        score=_stored_score(score),
        tier=tier,
        strategies=_strategies_used(result.signals.rungs, tier),
    )


def regrade(
    session: Session,
    *,
    dry_run: bool,
    budget_seconds: float = GENERATION_BUDGET_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
) -> RegradeReport:
    """Re-grade every stored puzzle, or report what that would do.

    Args:
        session: An open SQLAlchemy session. The caller owns the transaction:
            on the write path it must commit (``session_scope`` does), and on
            the dry-run path there is nothing to commit — this function rolls
            the session back before returning, so a caller that commits anyway
            still writes nothing.
        dry_run: ``True`` to produce the report without touching a row. The
            same loop runs either way; the flag gates only the assignments.
        budget_seconds: ADR-0011's per-row solve budget. Per *row*, not per
            run: one pathological grid must not eat the budget of the rows
            behind it, and a row that times out is reported, not fatal.
        monotonic: The clock the deadline is read from. Injected only so a test
            can dilate it; nothing graded depends on it (CON-014).

    Returns:
        The :class:`RegradeReport` for the run — on both paths, built from the
        same outcomes.

    Rows are taken in primary-key order so two runs meet them in the same
    order; nothing about a grade depends on the order, but a report that
    reshuffled itself between runs would be hard to compare by eye.
    """
    rows = session.query(Puzzle).order_by(Puzzle.id).all()

    outcomes: list[RowOutcome] = []
    for row in rows:
        graded = grade_stored_grid(row.grid, deadline=monotonic() + budget_seconds)
        outcomes.append(_outcome(row, graded))

        if isinstance(graded, Grade) and not dry_run:
            _capture_legacy_grade(row)
            row.difficulty_score = graded.score
            row.difficulty_tier = graded.tier.value
            row.strategies_used = list(graded.strategies)

    if dry_run:
        # AC-D as a property of the function rather than of its callers: after
        # this, nothing the run touched can reach the file even by accident.
        session.rollback()

    return RegradeReport(dry_run=dry_run, outcomes=tuple(outcomes))


def _capture_legacy_grade(row: Puzzle) -> None:
    """Move a row's pre-run grade into the legacy columns, at most once, ever.

    The guard is ``legacy_difficulty_tier IS NULL`` and the capture always
    writes a non-NULL value there — see :data:`NO_LEGACY_TIER`. Those two facts
    together are what make "the second run cannot overwrite the originals"
    structural: after one capture the guard is closed for good, whatever the
    row's original grade was, including no grade at all.
    """
    if row.legacy_difficulty_tier is not None:
        return
    row.legacy_difficulty_score = row.difficulty_score
    row.legacy_difficulty_tier = (
        row.difficulty_tier if row.difficulty_tier is not None else NO_LEGACY_TIER
    )


def _outcome(row: Puzzle, graded: Grade | Skip) -> RowOutcome:
    """One row's line in the report — the before, and what the solve said.

    The stored tier is read through
    :func:`~nonogram.difficulty.tier_of_record` and not
    :func:`~nonogram.difficulty.parse_tier`: these rows were written months ago
    in whatever spelling the writer used, there is nobody to tell about a bad
    one, and a report that crashed on the row it was meant to describe would be
    the least useful possible outcome.
    """
    return RowOutcome(
        puzzle_id=str(row.id),
        puzzle_name=row.puzzle_name,
        width=row.width,
        height=row.height,
        old_score=row.difficulty_score,
        old_tier=tier_of_record(row.difficulty_tier),
        old_tier_text=row.difficulty_tier,
        grade=graded if isinstance(graded, Grade) else None,
        skip=graded if isinstance(graded, Skip) else None,
    )


def _strategies_used(rungs: Sequence[str], tier: Tier) -> tuple[str, ...]:
    """FR-029's list: the solve's rungs in ladder order, ``guess`` last if it branched.

    ``guess`` is appended on the *tier*, not on ``branch_nodes``. The two say
    the same thing — ADR-0025 keys ``Tier.GUESS`` on exactly that count — but
    reading the count here would put a second reader of EC-015's rule in
    ``admin/``, which is the thing ADR-0025/R2 exists to prevent. Asking
    :func:`~nonogram.difficulty.classify` and believing the answer keeps one
    implementation.

    CARD-072 persists the same list from the generation path; this is the
    derivation to reuse there rather than write twice.
    """
    strategies = tuple(rungs)
    if tier is Tier.GUESS:
        return (*strategies, Tier.GUESS.value)
    return strategies


def _stored_score(score: float) -> int:
    """ADR-0029's float as the ``difficulty_score`` column's integer.

    Rounded **up**, and that is not a taste call. The column is an ``Integer``,
    so the float has to lose its fraction somewhere; the requirement is that
    the number left on disk still classifies as the tier stored beside it,
    because every reader that compares the two would otherwise see a row
    contradict itself.

    Ceiling gives that for free. A band is ``(low, high]`` with both edges whole
    numbers (0, 33, 66, 100), and a score inside it ceils to a whole number in
    ``[low + 1, high]`` — still inside the same band. Ordinary rounding does
    not: a ``line_dp`` puzzle that settled one cell at its top rung scores
    33.08, which rounds to 33 and reads back as Easy while its stored tier says
    Medium. The bottom rung's exact 33.0 is unmoved either way.

    One documented exception, and it is not this function's to fix:
    :data:`~nonogram.difficulty.Tier.GUESS` is keyed on ``branch_nodes``, not on
    a band (ADR-0025's EC-015), so a guess row's stored number reads back as
    whatever band it falls in — never as ``guess``, since no band maps there.
    The invariant above is therefore "the stored number keeps the *band* its
    float came from", which is what every reader comparing the two columns
    needs, rather than the stronger claim that it re-derives the stored tier.

    Both halves are pinned by
    ``tests/test_admin_regrade.py::TestStoredScore_KeepsTheBandItsFloatCameFrom``,
    including the case that tells ceiling from rounding — which cycle 1 found
    no test could (F-002).
    """
    return int(math.ceil(_clamp(score, SCORE_MIN, SCORE_MAX)))


def _as_grid(grid: object) -> list[list[bool]] | None:
    """``grid`` as the boundary type, or ``None`` if it is not one.

    Reading, not validating a domain rule: this is a JSON column, so it can
    hold anything, and the batch has to survive whatever is actually there.
    Rectangularity is checked here rather than left to
    :func:`~nonogram.clues.compute_clues`'s ``zip(strict=True)`` so that an
    empty grid — which encodes to two empty clue sets and would "solve"
    vacuously — is reported as unreadable instead of being graded 0.

    **Shape is validated; cell type is not.** A cell is read for its truthiness
    (``bool(cell)``), so a row of JSON nulls is a row of empty cells and a row
    of non-empty strings is a row of filled ones — neither is refused. That is
    deliberate rather than an oversight, and the reason is asymmetric risk: a
    row whose cells round-tripped as ``0``/``1`` through some other writer is
    still a perfectly good puzzle, and refusing it would skip a gradable row on
    the strength of a JSON encoding detail. A malformed *shape* has no such
    benign reading, which is why that half is strict.

    Pinned by
    ``tests/test_admin_regrade.py::test_a_grid_of_non_booleans_is_coerced_rather_than_refused``
    so the asymmetry stays a decision rather than becoming folklore
    (CARD-077 review cycle 1, F-009).
    """
    if not isinstance(grid, list) or not grid:
        return None
    width: int | None = None
    rows: list[list[bool]] = []
    for line in grid:
        if not isinstance(line, list) or not line:
            return None
        if width is None:
            width = len(line)
        elif len(line) != width:
            return None
        rows.append([bool(cell) for cell in line])
    return rows


def _clamp(value: float, low: float, high: float) -> float:
    return low if value < low else high if value > high else value
