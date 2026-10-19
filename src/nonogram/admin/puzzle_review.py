"""Puzzle review and filtering service for admin panel.

Handles filtering puzzles by various criteria and managing approval/rejection.
"""

import hashlib
import math
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from datetime import datetime, date, timezone

from nonogram.admin.book_plan import TIERS as PLAN_TIERS
from nonogram.clues import compute_clues
from nonogram.difficulty import Tier, classify, score_difficulty, tier_of_record
from nonogram.errors import NotUniquelySolvable, SolverTimeout
from nonogram.limits import MAX_SIZE, MIN_SIZE
from nonogram.orchestrator import GENERATION_BUDGET_SECONDS
from nonogram.solver import MANY, RUNG_ORDER, STRATEGY_GUESS, solve


#: Every name FR-029's strategies list can carry, in the order a list is
#: written: ADR-0029's ladder rungs, then ``guess`` when the search branched.
#: A stored list holding anything else was written by an older caller that
#: invented its names (``"LineLogic"``, ``"backtracking"``), so it is not read
#: as a statement about the puzzle — see :meth:`PuzzleReviewService.strategies_for`.
STRATEGY_NAMES: Tuple[str, ...] = (*RUNG_ORDER, STRATEGY_GUESS)

#: The longest name a puzzle can be given from the review list.
MAX_PUZZLE_NAME_LENGTH = 120

#: How many proved grids the service remembers at once (CARD-245).
#:
#: This is the *whole* of what "a verification expires" means here, and it is
#: deliberately not a clock. A remembered verification is two things at once:
#: the :class:`~nonogram.solver.SolveResult` that proved a grid a puzzle — a
#: pure function of that grid, which cannot go stale — and the fact that the
#: owner has been *shown* that grid's grade for a particular puzzle. The first
#: is what makes one solve serve both the uniqueness verdict and the grade
#: (ADR-0029/R2); the second is what stops a save storing a grid whose grade
#: nobody saw.
#:
#: A wall-clock TTL would add a clock, a seam to inject it through and a
#: flaky-test surface, to guard a case that is not harmful: an approve of the
#: *same* grid an hour later is still an approve of a grid this store proved.
#: The staleness that does matter — the row moving underneath, by being put in
#: a book — is re-checked at save time against the row itself, not against a
#: timer. So a verification is forgotten when this many newer grids have been
#: proved, or when the process restarts, and a save whose verification has
#: been forgotten is **refused** (:class:`EditNotVerified`): the owner verifies
#: again, which is one solve and cannot store anything ungraded.
MAX_REMEMBERED_VERIFICATIONS = 16


class EditNotVerified(ValueError):
    """A replacement grid was saved without a live verification *of that grid*.

    The two-phase save the owner asked for — show the difficulty, then
    Cancel or Approve — means a grade is produced before anything is stored,
    and that opens exactly one hole: an approve could carry a *different* grid
    from the one whose grade was on screen, and be stored with the earlier
    grade. This is that hole closed. A save is refused unless the grid it
    carries is one this store proved and showed for this puzzle.

    A ``ValueError`` subclass for the same reason as
    ``book_manager.InvalidBookDetails``: the panel's routes already answer
    ``ValueError`` from a store call, so no caller has to learn a new base to
    keep working.
    """


class EditNeedsConfirmation(ValueError):
    """A booked puzzle's grid may be replaced, but only once it is confirmed.

    CARD-251, the owner's request of 2026-10-19: a puzzle a book already holds
    is editable "with an additional 'are you sure' question". The question has
    to reach the **server** — a client-side dialog that then posts the same
    unchanged request is not a guard — so this is the refusal a save gets when
    it arrives without the owner's answer.

    It mirrors INV-008 / CARD-131's `confirmed` flag exactly
    (``book_manager.py``: a published book's membership changes only behind an
    explicit confirmation, and an unconfirmed call *measures nothing and
    writes nothing*). That is why it is raised before the solve rather than
    after it: an unconfirmed save pays for no solve, stamps no row and reports
    the one thing the caller needs in order to ask the question — which book.

    Attributes:
        book_id: The book that holds this puzzle, so the caller can name it.
            Never falsy: a membership with no book IDENTITY is refused
            outright instead
            (:meth:`PuzzleReviewService._an_edit_may_touch`).
    """

    def __init__(self, message: str, *, book_id: str) -> None:
        super().__init__(message)
        self.book_id = book_id


class RegradeInsideABook(ValueError):
    """A replacement grid for a booked puzzle grades into a different tier.

    **The owner's settled rule, 2026-10-19 (CARD-251).** INV-009 is not
    amended: a book's order is grouped by tier, every easy puzzle before every
    medium one, and a page pairs two puzzles only when their tiers are equal
    (INV-010). A replacement that graded into another tier would therefore
    move the book's structure — the level runs, the divider pages, the puzzle
    numbers 1..n — underneath its owner. Refusing it is what keeps INV-009
    true, and the owner chose that over giving the invariant a regrade clause.

    Raised from the **verify** as well as from the store, deliberately: the
    verify phase is the one that computes the new tier, so the owner learns
    this with the grade and before Approve, never as a surprise after storing.

    Attributes:
        stored_tier: The row's own ``difficulty_tier`` text, as stored.
        new_tier: The tier the replacement grid grades into.
        book_id: The book whose order the refusal protects.
    """

    def __init__(
        self, message: str, *, stored_tier: object, new_tier: str, book_id: str
    ) -> None:
        super().__init__(message)
        self.stored_tier = stored_tier
        self.new_tier = new_tier
        self.book_id = book_id


class ReplacementExtentChanged(ValueError):
    """A replacement grid is not the stored grid's size (CARD-251 AC-5).

    An edit replaces a puzzle's *picture*, not its shape.
    :meth:`PuzzleReviewService.verify_replacement_grid` read the submitted
    grid's own width and height and never compared them with the stored row's,
    which was unreachable through the editor page — its board is built from
    the stored grid and cannot change size — and irrelevant while a booked
    puzzle was refused outright. CARD-251 opens that door, and a differently
    shaped grid stored into a booked puzzle changes that book's geometry: the
    cell size its pages are fitted at, which puzzles pair, and therefore how
    many pages the book has. That is the harm the original "no editing a
    booked puzzle" rule was written to prevent.

    Refused for an unbooked puzzle too. The rule is "a replacement replaces a
    grid", not "a book is protected": a store that guarded only the booked
    case would leave every other row reachable by the same posted request.

    Attributes:
        stored: The stored grid's ``(width, height)``.
        submitted: The replacement's ``(width, height)``.
    """

    def __init__(
        self,
        message: str,
        *,
        stored: Tuple[int, int],
        submitted: Tuple[int, int],
    ) -> None:
        super().__init__(message)
        self.stored = stored
        self.submitted = submitted


@dataclass
class _Verification:
    """One proved grid: the proof, and who has been shown its grade.

    ``shown_for`` is a set of puzzle ids rather than a single one because the
    same grid may legitimately be verified for more than one puzzle, and the
    proof is about the grid alone.
    """

    #: The :class:`~nonogram.solver.SolveResult` that proved this grid a puzzle.
    proof: Any
    #: Puzzle ids whose owner has been shown this grid's grade.
    shown_for: set = field(default_factory=set)


#: CARD-122 / AC-215: the order a book's longest-side tab is listed in — tier
#: (easy, medium, hard, ungraded last), then the shorter side ascending, then
#: the longer side, then the id so two renders of the same tab agree.
#:
#: It is a ``sort_by`` value and not a Python ``sorted()`` at the route because
#: LIMIT/OFFSET *page* a tab: an order applied to
#: :attr:`PuzzleListResponse.puzzles` re-sorts one page in isolation, so the
#: tier sequence restarts at easy on page 2 and the tab as a whole is not in
#: the declared order at all (review cycle 2, F-001 — the same defect class as
#: cycle 1's filter-after-the-slice). Anything that decides *which* rows the
#: owner sees, or *in what order*, has to be inside the query.
#:
#: The four names below are tokens of :meth:`PuzzleReviewService._parse_sort_string`'s
#: existing grammar (comma-separated, ``-`` for descending); they are additive
#: and no previously accepted token changed meaning.
BOOK_TAB_SORT = "tier_rank,shorter_side,longer_side,id"


def _tier_rank(value: object) -> int:
    """Where a stored ``difficulty_tier`` sits in :data:`book_plan.TIERS`.

    The ladder is ``book_plan``'s and only ``book_plan``'s (G-1: one tier
    order), and how the stored text is *read* is
    :func:`nonogram.difficulty.tier_of_record`'s job — a row carries either
    spelling in any casing, and ADR-0025's retired ``"guess"`` reads as Hard.
    A value that is no tier at all ranks after every value that is.
    """
    tier = tier_of_record(value)
    return PLAN_TIERS.index(tier) if tier in PLAN_TIERS else len(PLAN_TIERS)


#: ADR-0025's retired fourth tier, still readable off old rows. Named here only
#: as a *spelling* to feed :func:`_tier_rank` — the verdict on it is
#: ``tier_of_record``'s, not this module's.
_RETIRED_TIER_SPELLING = "guess"

#: Every tier spelling a stored row can carry, trimmed and lower-cased, mapped
#: to its rank. SQL cannot call :func:`_tier_rank`, so the DB branch needs the
#: table — but the table is *derived* by calling that same function, so the two
#: backends cannot drift apart and neither restates the tier ladder.
_TIER_RANK_BY_SPELLING: Dict[str, int] = {
    spelling: _tier_rank(spelling)
    for spelling in sorted(
        {s.strip().lower() for tier in Tier for s in (tier.value, tier.label)}
        | {_RETIRED_TIER_SPELLING}
    )
}

#: The in-memory half of the tokens above: a sort key per computed column.
#: ``min``/``max`` rather than a stored column, because "shorter side" is a
#: fact about the extent pair and not a scalar the row carries (ADR-0022/R1).
_COMPUTED_SORT_KEYS = {
    "tier_rank": lambda p: _tier_rank(p.get("difficulty_tier")),
    "shorter_side": lambda p: min(p.get("width") or 0, p.get("height") or 0),
    "longer_side": lambda p: max(p.get("width") or 0, p.get("height") or 0),
    "id": lambda p: str(p.get("id") or ""),
}


class PuzzleStatus(Enum):
    """Status of a puzzle in the curation workflow."""

    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_BOOK = "in_book"


@dataclass
class PuzzleFilter:
    """Filters for puzzle queries."""

    size: Optional[Tuple[int, int]] = None  # e.g., (20, 20) as (width, height) extent pair
    #: Either spelling of any tier — the enum value ("easy") a
    #: pipeline-written row carries, or the display label ("Easy") an older
    #: one does. Resolved through difficulty.tier_of_record where it is
    #: applied, so both match the same rows (ADR-0025's four tiers included).
    difficulty: Optional[str] = None
    quality_min: Optional[int] = None  # 1-100
    theme: Optional[str] = None
    status: Optional[str] = None
    #: FR-029: keep only puzzles whose recorded strategies *contain* this name
    #: — "show me the ones that need a guess". Membership, not equality: a
    #: puzzle needing ``simple_overlap`` and ``guess`` answers both filters.
    #: One of :data:`STRATEGY_NAMES`; the route rejects anything else.
    strategy: Optional[str] = None
    batch_id: Optional[str] = None  # Filter by batch ID
    date_from: Optional[str] = None  # Filter by created_at >= date (YYYY-MM-DD)
    date_to: Optional[str] = None    # Filter by created_at <= date (YYYY-MM-DD)
    book_id: Optional[str] = None    # Filter by book_id (or special values: "unassigned")
    puzzle_name: Optional[str] = None  # Free-text search on puzzle_name field
    #: Comma-separated sort tokens, ``-`` prefixing a descending one, applied
    #: left to right **inside the query** — so LIMIT/OFFSET page the result in
    #: this order rather than slicing some other one (review cycle 2, F-001).
    #:
    #: Stored columns: ``batch_id``, ``size`` (= ``width``), ``width``,
    #: ``height``, ``quality`` (= ``quality_score``), ``difficulty``
    #: (= ``difficulty_tier``, the stored *string*), ``created_at``,
    #: ``puzzle_name``, ``id``. Computed keys (CARD-122, additive — no existing
    #: token changed meaning): ``tier_rank`` (the tier's position in
    #: ``book_plan.TIERS``, ungraded last — a rank, not the string
    #: ``difficulty`` sorts alphabetically), ``shorter_side`` =
    #: ``min(width, height)`` and ``longer_side`` = ``max(width, height)``.
    #: An unknown token is ignored. :data:`BOOK_TAB_SORT` is AC-215's order
    #: spelled in this grammar.
    sort_by: str = "batch_id,-size,quality"  # Default sort: batch DESC, size ASC, quality DESC
    limit: int = 25
    offset: int = 0
    #: CARD-122: a range on the grid's **longest** side — ``max(width, height)``
    #: — as ``(low, high)``, either bound optional. A 30x12 never matches
    #: ``longest_side_range=(10, 15)``, although its short side is in range:
    #: its longest side is 30. The book's longest-side tabs and the review
    #: page's size from/to fields (CARD-190) are this predicate, and they must
    #: be able to page:
    #: filtering a superset in Python after the store applied LIMIT hides the
    #: rows the tab is made of (review cycle 1, F-001).
    #:
    #: A row with a side outside the supported ``MIN_SIZE..MAX_SIZE`` range —
    #: one stored under an older limit — matches no longest-side range at all.
    #: It belongs to no bucket, which is the verdict ``book_plan.bucket_of``
    #: makes on the same row, so the store's count and the rendered tab agree.
    #: Both halves of that predicate are written down as a contract in
    #: ``book_plan.bucket_of``'s own docstring; this filter is its pushdown and
    #: follows it rather than restating it (review cycle 2, F-006).
    longest_side_range: Optional[Tuple[Optional[int], Optional[int]]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API."""
        return {
            "size": self.size,
            "difficulty": self.difficulty,
            "quality_min": self.quality_min,
            "theme": self.theme,
            "status": self.status,
            "batch_id": self.batch_id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "book_id": self.book_id,
            "puzzle_name": self.puzzle_name,
            "sort_by": self.sort_by,
            "limit": self.limit,
            "offset": self.offset,
            "longest_side_range": self.longest_side_range,
        }

    @staticmethod
    def from_dict(data: dict) -> "PuzzleFilter":
        """Create PuzzleFilter from dictionary."""
        return PuzzleFilter(
            size=data.get("size"),
            difficulty=data.get("difficulty"),
            quality_min=data.get("quality_min"),
            theme=data.get("theme"),
            status=data.get("status"),
            batch_id=data.get("batch_id"),
            date_from=data.get("date_from"),
            date_to=data.get("date_to"),
            book_id=data.get("book_id"),
            puzzle_name=data.get("puzzle_name"),
            sort_by=data.get("sort_by", "batch_id,-size,quality"),
            limit=data.get("limit", 25),
            offset=data.get("offset", 0),
            longest_side_range=data.get("longest_side_range"),
        )


@dataclass(frozen=True)
class BulkOutcome:
    """What a bulk action did to a batch, and what it did not do (CARD-068).

    These operations pass over puzzles for two different reasons, and only one
    of them is a refusal: a puzzle already in the target status needed nothing,
    while a puzzle in a book was *held back* — bulk-approving it would silently
    detach it from the book's curation state. Reporting one number for both
    made "Deleted 3 rejected puzzle(s)" read the same whether or not a fourth
    was kept out of it.
    """

    #: Puzzles this action actually changed or deleted.
    changed: int = 0
    #: Puzzles that were already as the action wanted them.
    unchanged: int = 0
    #: Puzzles left alone because they belong to a book.
    in_book: int = 0


@dataclass
class PuzzleListResponse:
    """Response for puzzle list queries."""

    puzzles: List[Dict[str, Any]]
    total_count: int
    offset: int
    limit: int
    has_more: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for API."""
        return {
            "puzzles": self.puzzles,
            "total_count": self.total_count,
            "offset": self.offset,
            "limit": self.limit,
            "has_more": self.has_more,
        }


class PuzzleReviewService:
    """Service for reviewing and filtering puzzles.

    Supports both in-memory storage (legacy, for backward compatibility) and
    database-backed storage (when session_factory is provided).
    """

    def __init__(self, session_factory=None):
        """Initialize puzzle review service.

        Args:
            session_factory: Optional callable that yields a DB session.
                           If None, uses in-memory dict storage (legacy mode).
                           If provided, uses database backend.
        """
        self._session_factory = session_factory
        # In-memory puzzle storage (used only in legacy mode when session_factory is None)
        self.puzzles: Dict[str, Dict[str, Any]] = {}
        self._next_id = 1
        # CARD-245: grids this service has proved, newest last, keyed by
        # fingerprint and bounded by MAX_REMEMBERED_VERIFICATIONS. Per
        # instance, in this process, and nowhere else: the panel runs one
        # gunicorn worker (CARD-086 G-4, `start.sh`), and it is the same place
        # the legacy mode already keeps `self.puzzles`. Losing it costs a
        # re-verify, never a wrong write — see the constant's own note.
        self._verifications: "OrderedDict[str, _Verification]" = OrderedDict()

    def _row_to_dict(self, puzzle_row) -> Dict[str, Any]:
        """Convert SQLAlchemy Puzzle ORM row to dict (matching legacy format).

        Args:
            puzzle_row: SQLAlchemy Puzzle ORM instance

        Returns:
            Dict with same keys as legacy puzzle dicts
        """
        return {
            "id": str(puzzle_row.id),
            "grid": puzzle_row.grid,
            "clues_rows": puzzle_row.clues_rows,
            "clues_cols": puzzle_row.clues_cols,
            "width": puzzle_row.width,
            "height": puzzle_row.height,
            "theme": puzzle_row.theme,
            "difficulty_score": puzzle_row.difficulty_score,
            "difficulty_tier": puzzle_row.difficulty_tier,
            "quality_score": puzzle_row.quality_score,
            "recognizability": puzzle_row.recognizability,
            "strategies_used": puzzle_row.strategies_used,
            "status": puzzle_row.status,
            "batch_id": str(puzzle_row.batch_id) if puzzle_row.batch_id else None,
            "source_image": puzzle_row.source_image,
            "puzzle_name": puzzle_row.puzzle_name,
            "book_id": str(puzzle_row.book_id) if puzzle_row.book_id else None,
            "created_at": puzzle_row.created_at.isoformat() if puzzle_row.created_at else None,
            # CARD-245: when the grid was last replaced by hand, or None. Read
            # beside `quality_score` everywhere the score is shown, because
            # non-null means that number predates the edit.
            "manually_edited_at": (
                puzzle_row.manually_edited_at.isoformat()
                if puzzle_row.manually_edited_at
                else None
            ),
        }

    @staticmethod
    def _refuse_unless_shaped_like_a_grid(grid: object) -> None:
        """Refuse anything that is not a non-empty rectangle of booleans.

        Checked before ``compute_clues``, because ``compute_clues`` is happy to
        encode things that are not grids and the result then *solves*. Measured:
        ``[]`` encodes to two empty clue sets, ``[[]]`` to ``((0,),)``, and the
        string ``"not a grid"`` to ten rows of one filled cell — a 10x1 grid
        that is uniquely solvable, so a guard that only asked the solver would
        have stored the string. :meth:`_as_readable_grid` (and
        ``regrade._as_grid``) exist for the same reason on the read side.

        Strict about cell *type*, where those two deliberately coerce. They are
        answering different questions: they read rows a previous version of
        this system already wrote, where a cell stored as ``0``/``1`` is a fact
        to be accommodated; this one is a write boundary, where a caller
        handing over anything but booleans has a bug worth hearing about
        (ADR-0012 fixes the boundary type as ``list[list[bool]]``).

        The audit used to come through here too, which made it report
        uniquely-solvable legacy rows as failures — the write path's strictness
        applied to the read path's question (CARD-080 review cycle 1, F-001).
        It now reads through :meth:`_as_readable_grid` instead.
        """
        if not isinstance(grid, list) or not grid:
            raise NotUniquelySolvable(
                "refusing to store a grid that is not a readable grid: "
                "expected a non-empty list of rows"
            )
        width = None
        for row in grid:
            if not isinstance(row, list) or not row:
                raise NotUniquelySolvable(
                    "refusing to store a grid that is not a readable grid: "
                    "every row must be a non-empty list"
                )
            if not all(isinstance(cell, bool) for cell in row):
                raise NotUniquelySolvable(
                    "refusing to store a grid that is not a readable grid: "
                    "cells must be booleans (ADR-0012)"
                )
            if width is None:
                width = len(row)
            elif len(row) != width:
                raise NotUniquelySolvable(
                    "refusing to store a grid that is not a readable grid: "
                    f"row lengths differ ({width} then {len(row)})"
                )

    @staticmethod
    def _as_readable_grid(grid: object) -> Optional[List[List[bool]]]:
        """``grid`` as the boundary type, or ``None`` if it is not one.

        The **read** half of the pair whose write half is
        :meth:`_refuse_unless_shaped_like_a_grid`, and deliberately not the
        same function. Shape is checked exactly as strictly — a ragged grid has
        no benign reading, and an empty one encodes to two empty clue sets and
        would "solve" vacuously — but cell *type* is coerced (``bool(cell)``)
        rather than refused, because a row whose cells round-tripped as
        ``0``/``1`` through some earlier writer is still a perfectly good
        puzzle. Refusing it on the read path would be an audit lying about the
        data it exists to describe: measured, ``[[1, 1], [0, 1]]`` is a
        uniquely solvable Easy puzzle that the write-path check calls
        malformed.

        A native reimplementation of ``regrade._as_grid`` rather than an import
        of it — the same rule, read by two modules — cross-checked against that
        one from the test tree by
        ``tests/test_admin_uniqueness_boundary.py::TestTheTwoGridReaders_AgreeWithEachOther``,
        which is this package's standing way of keeping duplicated logic honest
        (``solver.propagate.mask_runs`` is the precedent).
        """
        if not isinstance(grid, list) or not grid:
            return None
        width: Optional[int] = None
        rows: List[List[bool]] = []
        for line in grid:
            if not isinstance(line, list) or not line:
                return None
            if width is None:
                width = len(line)
            elif len(line) != width:
                return None
            rows.append([bool(cell) for cell in line])
        return rows

    def _why_this_is_not_a_puzzle(
        self, grid: List[List[bool]], *, deadline_seconds: float
    ) -> tuple[Optional[str], Optional[BaseException], Optional[Any]]:
        """The solver's objection to ``grid``, its cause, and the solve.

        ``(None, None, result)`` when the grid is a puzzle: the third element
        is the :class:`~nonogram.solver.SolveResult` that proved it, so a
        caller that also wants the strategies list reads it off this solve
        instead of paying for a second one (ADR-0029/R2). It is ``None``
        whenever there is an objection.

        The single place either path asks the question, so the write boundary
        and the audit cannot drift into disagreeing about what "a puzzle"
        means. It answers in the audit's voice — a reason, not a refusal —
        because a reason reads correctly in a report *and* inside the
        exception the write path wraps it in, where the reverse is not true.

        The second element is the exception that produced the objection, or
        ``None`` when the objection is a verdict rather than a failure. The
        write path re-attaches it with ``raise ... from``; the audit drops it.
        Returning it rather than raising here is what keeps one question in one
        place without the write path losing its traceback: a refusal caused by
        a :class:`SolverTimeout` is logged by ``batch_generator`` with
        ``exc_info=True``, and a refusal that *should be unreachable* is
        exactly the one whose cause somebody will need (CARD-080 review cycle
        2, F-008).

        The clues are re-derived from the grid rather than taken from any
        ``clues_rows``/``clues_cols`` the caller supplied. Those are the
        caller's claim about the grid, and a guard that trusts the caller's
        claim is not a guard — CARD-051's rule that ``clues.compute_clues`` is
        the one encoder says the same thing from the other direction.

        ``deadline_seconds`` is a per-grid budget (ADR-0011). A solve that
        passes it is an objection, not a pass: storage asks *has this been
        proven to be a puzzle?*, and an unproven grid is not a proven one.
        """
        try:
            row_clues, column_clues = compute_clues(grid)
        except (TypeError, ValueError) as exc:  # pragma: no cover - both callers screen the shape
            return f"not a readable grid: {exc}", exc, None

        try:
            result = solve(
                row_clues,
                column_clues,
                deadline=time.monotonic() + deadline_seconds,
            )
        except SolverTimeout as exc:
            return (
                f"uniqueness could not be proven within {deadline_seconds}s "
                "— unproven is not proven"
            ), exc, None

        if result.solution_count != 1:
            # The zero arm is unreachable while the clues are derived from the
            # grid, since that grid satisfies them — measured over 120 random
            # derived clue sets: 97 unique, 23 ambiguous, none unsolvable. Kept
            # because the solver's contract allows the value, not because a
            # caller can produce it (CARD-080 review cycle 2, F-015).
            counted = "2 or more" if result.solution_count == MANY else "0"
            return (
                f"the clue set has {counted} solutions, and a clue set that is "
                "not uniquely solvable is not a puzzle (FR-006)"
            ), None, None
        return None, None, result

    def _refuse_unless_uniquely_solvable(self, grid: object):
        """Ask the solver whether this grid is a puzzle, and refuse if it is not.

        FR-006 says uniqueness is the product's defining property, and CON-005
        says the solver is the authority on it. Together those make this the
        only honest place for the check: a store that accepts whatever its
        callers hand it has the property only as long as every caller does, and
        the twenty rows deleted on 2026-09-14 are what that argument costs when
        it stops holding. They came from a third caller that derived a tier
        from the grid's *size* and never solved anything. Deleting that
        function closed the instance; this closes the class.

        This is the **write** path, so it is strict about cell type where
        :meth:`_as_readable_grid` coerces — see
        :meth:`_refuse_unless_shaped_like_a_grid` for why the two differ. The
        refusal carries the exception that caused it (``from cause``), so a
        caller logging with ``exc_info`` records what the solver actually said.

        Returns:
            The :class:`~nonogram.solver.SolveResult` that proved the grid a
            puzzle.

        Raises:
            NotUniquelySolvable: the grid is not a readable grid, its clue set
                has 0 or >= 2 solutions, or the solve passed its deadline
                (ADR-0011) without concluding.

        **One solve, two answers** (CARD-245). A proof this method has already
        produced for this exact grid is remembered
        (:data:`MAX_REMEMBERED_VERIFICATIONS`) and handed back instead of being
        bought again, so the two-phase manual edit — show the difficulty, then
        Approve — enters the search *once* rather than once per phase. The
        remembered answer is sound because it is the answer to a pure question:
        the clue set is re-derived from the grid here, and the solve is
        deterministic, so the verdict is a function of the grid's cells alone.
        Only proofs are remembered — a timeout is a fact about one run's clock
        and is never cached (ADR-0011).
        """
        self._refuse_unless_shaped_like_a_grid(grid)

        fingerprint = self._grid_fingerprint(grid)
        remembered = self._remembered_verification(fingerprint)
        if remembered is not None:
            return remembered.proof

        # ADR-0011's bound, not a caller's choice — which is why this takes no
        # budget argument. The audit's does, because raising the budget is how
        # an operator asks a deeper question of a table; a *write* that needed
        # longer than the generation budget to be proven was not proven.
        objection, cause, result = self._why_this_is_not_a_puzzle(
            grid, deadline_seconds=GENERATION_BUDGET_SECONDS
        )
        if objection is not None:
            raise NotUniquelySolvable(f"refusing to store a grid: {objection}") from cause
        self._remember_proof(fingerprint, result)
        return result

    @staticmethod
    def _grid_fingerprint(grid: List[List[bool]]) -> str:
        """A short, stable name for one grid's cells — its SHA-256 digest.

        Only ever called on a grid :meth:`_refuse_unless_shaped_like_a_grid`
        has already accepted, so the cells really are booleans and the extent
        really is rectangular. The extent is part of the digest rather than
        implied by it: without it, two grids whose cells read the same in
        row-major order (a 2x6 and a 3x4 of the same bits) would share a name.
        """
        bits = "".join("1" if cell else "0" for row in grid for cell in row)
        text = f"{len(grid)}x{len(grid[0])}:{bits}"
        return hashlib.sha256(text.encode("ascii")).hexdigest()

    def _remembered_verification(self, fingerprint: str) -> Optional["_Verification"]:
        """The verification remembered for ``fingerprint``, or ``None``.

        The **one** way the memo is read. Reading through it marks the entry
        as the most recently used, so the grid a flow is working on is not the
        one evicted out from under it — and that refresh is why there is one
        accessor rather than two call sites each doing their own ``get``
        (review cycle 1, F-011: the save used to read ``self._verifications``
        directly and so did not refresh recency, which was harmless only
        because the gate immediately before it did).
        """
        verification = self._verifications.get(fingerprint)
        if verification is None:
            return None
        self._verifications.move_to_end(fingerprint)
        return verification

    def _remember_proof(self, fingerprint: str, proof) -> "_Verification":
        """Remember ``proof`` for ``fingerprint``, evicting the oldest if full.

        Reads ``self._verifications`` directly rather than through
        :meth:`_remembered_verification`, and the reason is simply that this
        is one of the memo's own three methods — the F-011 rule is that
        nothing *outside* them touches the structure, and
        ``test_nothing_outside_the_memos_own_methods_touches_it`` is where
        that is pinned. It is **not** that the accessor's recency refresh has
        to be avoided here (review cycle 2, F-103): the ``move_to_end`` below
        runs on both branches, so going through the accessor would behave
        identically, with one redundant refresh on the hit.
        """
        verification = self._verifications.get(fingerprint)
        if verification is None:
            verification = _Verification(proof=proof)
            self._verifications[fingerprint] = verification
        else:
            verification.proof = proof
        self._verifications.move_to_end(fingerprint)
        while len(self._verifications) > MAX_REMEMBERED_VERIFICATIONS:
            self._verifications.popitem(last=False)
        return verification

    @staticmethod
    def _strategies_of(result) -> List[str]:
        """FR-029's list from one solve: its rungs, then ``guess`` if it branched.

        ``guess`` is read off ``branch_nodes`` since CARD-098 — ADR-0031
        retired the tier that used to carry the same fact, so there is no
        classifier to ask. A native reimplementation of
        ``regrade._strategies_used`` — that module imports SQLAlchemy, which
        this one must not require — held to the same answer from the test tree.
        """
        signals = result.signals
        strategies = list(signals.rungs)
        if signals.branch_nodes > 0:
            strategies.append(STRATEGY_GUESS)
        return strategies

    @staticmethod
    def _is_strategies_list(value: object) -> bool:
        """Is ``value`` a list this system's solver could have written?"""
        return (
            isinstance(value, (list, tuple))
            and bool(value)
            and all(name in STRATEGY_NAMES for name in value)
        )

    def strategies_for(
        self, puzzle: Dict[str, Any], *, deadline_seconds: float = GENERATION_BUDGET_SECONDS
    ) -> Optional[List[str]]:
        """The strategies a solver needs for ``puzzle``, or ``None`` if unknown.

        The stored list when it is one the solver wrote. Otherwise — rows
        stored before the list was recorded carry ``[]``, and older test and
        demo writers invented names — the stored grid is solved again and the
        list read off that solve. Read-only: nothing is written back.

        ``None`` when that solve cannot answer: the grid is unreadable, not
        uniquely solvable, or not concluded within ``deadline_seconds``.
        """
        stored = puzzle.get("strategies_used")
        if self._is_strategies_list(stored):
            return list(stored)
        rows = self._as_readable_grid(puzzle.get("grid"))
        if rows is None:
            return None
        objection, _, result = self._why_this_is_not_a_puzzle(
            rows, deadline_seconds=deadline_seconds
        )
        if objection is not None:
            return None
        return self._strategies_of(result)

    def audit_uniqueness(self, *, deadline_seconds: float = GENERATION_BUDGET_SECONDS):
        """Re-verify every stored row and report the ones that are not puzzles.

        Reports; never writes. The guard above stops new bad rows, and this
        answers the separate question the guard cannot — *what is in there
        now?* — which is the question that found the twenty. Being able to ask
        it again at any time is the part of this card's original quarantine
        framing worth keeping.

        Rows are read through :meth:`_as_readable_grid`, not through the write
        path's shape check: this method's whole subject is rows written by
        older code, so a cell stored as ``0`` rather than ``false`` is a fact
        to accommodate rather than a bug to report.

        Args:
            deadline_seconds: Per-row solve budget. Raising it is how an
                operator asks a deeper question of a table whose hard rows time
                out at the default; it reaches the solver, so a larger number
                really does buy more proof.

        Returns:
            A list of ``(puzzle_id, reason)`` pairs, one per row that is not
            provably a puzzle, in the order the rows were met. Empty means
            every stored row was re-verified as uniquely solvable — a real
            statement about the data, not a default.
        """
        failures = []
        for puzzle in self._all_rows_for_audit():
            rows = self._as_readable_grid(puzzle.get("grid"))
            if rows is None:
                failures.append(
                    (
                        str(puzzle["id"]),
                        "not a readable grid: expected a non-empty rectangle of cells",
                    )
                )
                continue
            objection, _, _ = self._why_this_is_not_a_puzzle(
                rows, deadline_seconds=deadline_seconds
            )
            if objection is not None:
                failures.append((str(puzzle["id"]), objection))
        return failures

    def _all_rows_for_audit(self):
        """Every stored row as ``{"id", "grid"}``, from whichever store is live."""
        if self._session_factory is None:
            return [
                {"id": puzzle_id, "grid": puzzle.get("grid")}
                for puzzle_id, puzzle in self.puzzles.items()
            ]
        from nonogram.db.models import Puzzle

        with self._session_factory() as db:
            return [
                {"id": row.id, "grid": row.grid}
                for row in db.query(Puzzle).order_by(Puzzle.id).all()
            ]

    def add_puzzle(
        self,
        grid: list,
        clues_rows: list,
        clues_cols: list,
        width: int,
        height: int,
        theme: str,
        difficulty_score: int,
        difficulty_tier: str,
        quality_score: int,
        recognizability: str,
        strategies_used: List[str],
        batch_id: Optional[str] = None,
        source_image: Optional[str] = None,
    ) -> str:
        """Add a puzzle to the store (legacy in-memory or DB-backed).

        Args:
            grid: Nonogram grid (List[List[bool]])
            clues_rows: Row clues (List[List[int]])
            clues_cols: Column clues (List[List[int]])
            width: Grid width
            height: Grid height
            theme: Puzzle theme
            difficulty_score: Difficulty score (1-100)
            difficulty_tier: Difficulty tier (Easy/Medium/Hard)
            quality_score: Quality score (1-100)
            recognizability: Recognizability (high/medium/low)
            strategies_used: List of strategy names. Empty means "not
                recorded by the caller": the list is then read off the
                uniqueness solve this method already runs.
            batch_id: Optional batch ID to link puzzle to batch
            source_image: Optional source image name (for image-based generation)

        Returns:
            puzzle_id (in-memory: puzzle_NNNNNN, DB: UUID string)

        Raises:
            NotUniquelySolvable: ``grid``'s clues do not have exactly one
                solution, or the solve could not conclude in time. Nothing is
                written in either case. See
                :meth:`_refuse_unless_uniquely_solvable`.
        """
        # Before either branch, so the property is the store's and not one
        # mode's. A refusal here is a bug in the caller, so it is raised rather
        # than returned or logged (CARD-080).
        proof = self._refuse_unless_uniquely_solvable(grid)
        if not strategies_used:
            # Neither generation path had the solve to hand, and this guard
            # just ran one — record what it says rather than store nothing.
            strategies_used = self._strategies_of(proof)

        if self._session_factory is None:
            # Legacy mode: in-memory dict
            puzzle_id = f"puzzle_{self._next_id:06d}"
            self._next_id += 1

            self.puzzles[puzzle_id] = {
                "id": puzzle_id,
                "grid": grid,
                "clues_rows": clues_rows,
                "clues_cols": clues_cols,
                "width": width,
                "height": height,
                "theme": theme,
                "difficulty_score": difficulty_score,
                "difficulty_tier": difficulty_tier,
                "quality_score": quality_score,
                "recognizability": recognizability,
                "strategies_used": strategies_used,
                "status": PuzzleStatus.DRAFT.value,
                "batch_id": batch_id,
                "source_image": source_image,
                "created_at": datetime.now(timezone.utc).isoformat(),
                # CARD-245: a freshly generated puzzle has never been hand
                # edited, and the key is present so both modes' rows have the
                # same shape for every reader.
                "manually_edited_at": None,
            }
            return puzzle_id
        else:
            # DB mode: insert Puzzle row
            import uuid as uuid_module
            from nonogram.db.models import Puzzle

            with self._session_factory() as db:
                batch_uuid = uuid_module.UUID(batch_id) if batch_id and isinstance(batch_id, str) else batch_id
                puzzle = Puzzle(
                    grid=grid,
                    clues_rows=clues_rows,
                    clues_cols=clues_cols,
                    width=width,
                    height=height,
                    theme=theme,
                    difficulty_score=difficulty_score,
                    difficulty_tier=difficulty_tier,
                    quality_score=quality_score,
                    recognizability=recognizability,
                    strategies_used=strategies_used,
                    status=PuzzleStatus.DRAFT.value,
                    batch_id=batch_uuid,  # Convert string to UUID
                    source_image=source_image,
                )
                db.add(puzzle)
                db.flush()  # get the auto-generated UUID
                return str(puzzle.id)

    # ------------------------------------------------------------------
    # CARD-245 — manual editing: one solve answers both questions, and a
    # grid that was not proved by it is not stored.
    #
    # Two methods, because the owner asked for the difficulty *before*
    # committing: `verify_replacement_grid` grades without writing (Cancel
    # loses nothing) and `save_edited_grid` writes what was graded. They are
    # one solve between them, not two: the first proves the grid and the
    # store remembers the proof, the second reads it back through the same
    # gate (see `_refuse_unless_uniquely_solvable`).
    #
    # The editor UI is CARD-246. A *filter* on "hand-edited" is deliberately
    # not here: it is an obvious next want and a cheap follow-up, but adding
    # a filter field is scope this card did not ask for.
    # ------------------------------------------------------------------

    @staticmethod
    def _stored_score(score: float) -> int:
        """ADR-0029's float as the ``difficulty_score`` column's integer.

        Rounded **up**, because the number left on disk has to classify as the
        tier stored beside it: a band is ``(low, high]`` with whole-number
        edges, so a ceiling stays inside the band its float came from while
        ordinary rounding does not (33.08 rounds to 33, which reads back Easy
        beside a stored tier of Medium).

        A native reimplementation of ``regrade._stored_score`` for the same
        reason as :meth:`_strategies_of`: that module imports SQLAlchemy and
        this one must not require it. The two are pinned against each other
        from the test tree, where importing it is legal.
        """
        return int(math.ceil(min(max(score, 0.0), 100.0)))

    def _grade_of(self, proof) -> Dict[str, Any]:
        """FR-026's three graded columns, read off one solve and nothing else.

        No solver re-entry (ADR-0029/R2): ``proof`` is the
        :class:`~nonogram.solver.SolveResult` the uniqueness gate already
        produced, and :func:`~nonogram.difficulty.score_difficulty` grades its
        signals.
        """
        score = score_difficulty(proof.signals)
        return {
            "difficulty_score": self._stored_score(score),
            "difficulty_tier": classify(score).value,
            "strategies_used": self._strategies_of(proof),
        }

    def _row_an_edit_may_touch(self, puzzle_id: str) -> Optional[Dict[str, Any]]:
        """The stored row, or ``None`` if it may not be edited.

        ``None`` for a puzzle that does not exist **and** for one whose
        membership carries NO BOOK IDENTITY — the contract
        :meth:`_set_status` already set, so the routes tell the two apart by
        asking :meth:`in_a_book` first and can say which it was.

        **CARD-251 narrowed the second case.** Until then every booked puzzle
        was refused here, for the reason approve, reject, restore and delete
        still refuse one. The owner has since asked for a booked puzzle to be
        editable behind a confirmation that *names the book*, so a row whose
        ``book_id`` is a real id is returned and the confirmation is asked for
        separately (:meth:`_refuse_unless_confirmed_for_its_book`). What stays
        refused outright is the membership there is no book to name:
        :meth:`_an_edit_may_touch` says which that is.
        """
        puzzle = self.get_puzzle(puzzle_id)
        if puzzle is None:
            return None
        if not self._an_edit_may_touch(puzzle.get("book_id"), puzzle.get("status")):
            return None
        return puzzle

    @staticmethod
    def _an_edit_may_touch(book_id, status) -> bool:
        """May a row with this membership be edited at all (CARD-251)?

        **One spelling of the rule**, for the four surfaces that ask it: the
        list row's Edit control and the puzzle card's (both through
        ``app.py``'s ``puzzle_is_editable``), the editor page's route, and the
        two save routes through :meth:`_row_an_edit_may_touch`. That is
        CARD-246's F-010 rule kept — three surfaces disagreeing about one
        puzzle is how a control got offered for a row the route then refused.

        ``False`` only for a membership with NO BOOK IDENTITY — the
        predicate is ``bool(book_id)`` under ``_holds_a_book``, which answers
        True for the legacy ``in_book`` status with no ``book_id`` at all and
        for a migration's empty-string ``book_id``. The confirmation CARD-251
        asks has to name the book it is about — "Are you sure?" with no object
        is a dialog to click through, not a question — so where there is no id
        to ask about, the guard stays the refusal it was.

        **Said as the predicate rather than as "a book this panel cannot
        name"** (review cycle 1, F-005): a ``book_id`` pointing at a deleted
        row is equally unnameable and takes the OTHER branch — it IS an
        identity, so the edit is asked about, and the question names the id
        and says the title could not be read (failure matrix F-4,
        ``puzzle_edit.js``'s ``namedBook``). The seam is the identity, not the
        title.
        """
        if not PuzzleReviewService._holds_a_book(book_id, status):
            return True
        return bool(book_id)

    @staticmethod
    def _refuse_unless_confirmed_for_its_book(
        puzzle: Dict[str, Any], confirmed: bool
    ) -> None:
        """Refuse an unconfirmed replacement of a booked puzzle's grid (AC-2).

        The INV-008 shape, exactly: the question is the server's, an
        unconfirmed call writes nothing, and — because this runs before the
        solve — it measures nothing either.

        Raises:
            EditNeedsConfirmation: a book holds this puzzle and the caller did
                not confirm. The refusal carries the ``book_id`` so the caller
                can name the book in the question it asks.
        """
        book_id = puzzle.get("book_id")
        if not PuzzleReviewService._holds_a_book(book_id, puzzle.get("status")):
            return
        if confirmed:
            return
        raise EditNeedsConfirmation(
            "a book holds this puzzle, so replacing its grid has to be "
            "confirmed: nothing was stored",
            book_id=str(book_id),
        )

    @staticmethod
    def _refuse_a_regrade_inside_a_book(
        puzzle: Dict[str, Any], new_tier: str
    ) -> None:
        """Refuse a replacement that would change a booked puzzle's tier (AC-4).

        The stored text is read through :func:`~nonogram.difficulty.tier_of_record`
        — the one reader of a stored tier, so ``"Easy"`` and ``"easy"`` are
        the same tier and ADR-0025's retired ``"guess"`` still reads as Hard.
        A stored value that is no tier at all reads as ``None``, which differs
        from every real tier, so such a row is refused: a book groups by tier
        (INV-009) and a row that moves from "no readable tier" into a level
        moves the book's structure just as surely as one that changes level.

        Raises:
            RegradeInsideABook: a book holds this puzzle and the replacement
                grades into another tier. Nothing is stored and, at the
                verify, no proof is remembered.
        """
        book_id = puzzle.get("book_id")
        if not PuzzleReviewService._holds_a_book(book_id, puzzle.get("status")):
            return
        stored_tier = puzzle.get("difficulty_tier")
        if tier_of_record(stored_tier) is tier_of_record(new_tier):
            return
        raise RegradeInsideABook(
            f"this grid grades {new_tier} and the puzzle a book holds is "
            f"stored as {stored_tier}: a book's order is grouped by tier "
            "(INV-009) and a page pairs equal tiers only (INV-010), so a "
            "replacement that changes the tier is refused. Nothing was stored",
            stored_tier=stored_tier,
            new_tier=new_tier,
            book_id=str(book_id),
        )

    @staticmethod
    def _refuse_unless_the_stored_extent(
        puzzle: Dict[str, Any], grid: List[List[bool]]
    ) -> None:
        """Refuse a replacement that is not the stored grid's size (AC-5, G-5).

        Measured against the stored **grid**, not against the row's own
        ``width``/``height`` columns: the editor's board is built from the
        grid (``app.py``'s ``_board_page_payload``), so a row whose columns
        disagree with its grid would otherwise have no storable replacement at
        all.

        Raises:
            ReplacementExtentChanged: the submitted grid's extent is not the
                stored one's. Nothing is written.
        """
        stored_grid = puzzle.get("grid") or []
        stored = (len(stored_grid[0]) if stored_grid else 0, len(stored_grid))
        submitted = (len(grid[0]), len(grid))
        if submitted == stored:
            return
        raise ReplacementExtentChanged(
            f"a replacement grid keeps the puzzle's size: this one is "
            f"{submitted[0]}x{submitted[1]} and the stored grid is "
            f"{stored[0]}x{stored[1]}. Nothing was stored",
            stored=stored,
            submitted=submitted,
        )

    def _refuse_unless_verified(self, puzzle_id: str, grid: List[List[bool]]) -> None:
        """Refuse a save whose grid is not the grid whose grade was shown.

        Raises:
            EditNotVerified: no live verification of *this* grid for *this*
                puzzle — because none was made, because the approve carries a
                different grid than the verify did, or because the
                verification has been forgotten
                (:data:`MAX_REMEMBERED_VERIFICATIONS`).
        """
        verification = self._remembered_verification(self._grid_fingerprint(grid))
        if verification is None or str(puzzle_id) not in verification.shown_for:
            raise EditNotVerified(
                "refusing to store an edit that was not verified: this grid's "
                "difficulty has not been shown for this puzzle (verify it again)"
            )

    def verify_replacement_grid(
        self, puzzle_id: str, grid: object
    ) -> Optional[Dict[str, Any]]:
        """Grade a replacement grid for ``puzzle_id`` without storing anything.

        The first half of the owner's two-phase save: the difficulty is shown
        with Cancel and Approve beside it, and Cancel must lose nothing — so
        this writes no row, and a verified grid is remembered only as a proof
        the save can read back.

        Args:
            puzzle_id: The puzzle the replacement is for.
            grid: The replacement grid, ``list[list[bool]]`` (ADR-0012).

        Returns:
            What one solve says about the grid — ``difficulty_score``,
            ``difficulty_tier``, ``strategies_used``, the re-encoded
            ``clues_rows``/``clues_cols``, the extent and (CARD-251) the
            ``book_id`` of the book that holds the puzzle, if one does — or
            ``None`` if the puzzle does not exist or its membership carries
            no book identity (:meth:`_row_an_edit_may_touch`).

            ``book_id`` is the whole of what this method says about the book.
            The title, the book's status and whether the edit would change the
            book's page count are the route's to add (``app.py``): a title is
            ``book_manager``'s and the pairing geometry is
            ``book_pdf_generator``'s, and this module imports neither.

        Raises:
            NotUniquelySolvable: the grid is not a readable grid, or its clue
                set does not have exactly one solution. The refusal names
                which (FR-006, CON-005).
            RegradeInsideABook: a book holds this puzzle and the grid grades
                into another tier (CARD-251 AC-4). Raised **here**, at the
                phase that computes the tier, so the owner learns it with the
                grade and before Approve — and raised before the proof is
                remembered, so there is nothing a later save could approve.
        """
        puzzle = self._row_an_edit_may_touch(puzzle_id)
        if puzzle is None:
            return None

        # The one gate, for the one reason it exists: nothing is graded that
        # has not been proved to be a puzzle first (G-1).
        proof = self._refuse_unless_uniquely_solvable(grid)
        grade = self._grade_of(proof)
        # The tier the book reads, against the tier this grid would get. The
        # refusal belongs after the grade and before the memo: it is a
        # statement about the grade, and remembering a proof for a grid that
        # may not be stored would leave an approvable grid behind a refusal.
        self._refuse_a_regrade_inside_a_book(puzzle, grade["difficulty_tier"])
        fingerprint = self._grid_fingerprint(grid)
        self._remember_proof(fingerprint, proof).shown_for.add(str(puzzle_id))

        row_clues, column_clues = compute_clues(grid)
        return {
            "puzzle_id": str(puzzle_id),
            "grid_hash": fingerprint,
            "width": len(grid[0]),
            "height": len(grid),
            "clues_rows": [list(clue) for clue in row_clues],
            "clues_cols": [list(clue) for clue in column_clues],
            "book_id": (
                str(puzzle["book_id"])
                if self._holds_a_book(puzzle.get("book_id"), puzzle.get("status"))
                else None
            ),
            **grade,
        }

    def save_edited_grid(
        self, puzzle_id: str, grid: object, confirmed: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Store a verified replacement grid, re-deriving everything derived.

        The grid lands, and with it the five columns that are facts about the
        grid rather than about the puzzle's history: ``clues_rows`` and
        ``clues_cols`` re-encoded through COMP-004 (they are marked "display
        only" on the model precisely because they are derived),
        ``difficulty_score``, ``difficulty_tier`` and ``strategies_used`` read
        off the one solve that proved the grid unique, and
        ``manually_edited_at`` stamped now.

        What does **not** move: ``id``, ``batch_id``, ``source_image``,
        ``created_at``, ``status``, ``book_id``, ``puzzle_name``, ``theme`` —
        and ``quality_score``/``recognizability``, which are stale rather than
        meaningless after an edit and are what the new stamp exists to qualify
        (see the model's own note on why nulling the score was refused).

        Args:
            puzzle_id: The puzzle whose grid is replaced.
            grid: The replacement grid, ``list[list[bool]]`` (ADR-0012).
            confirmed: The owner has confirmed replacing the grid of a puzzle
                a book holds (CARD-251). Ignored for an unbooked puzzle, which
                has no book to ask about. ``False`` by default, so a caller
                cannot reach the write by forgetting the argument — the same
                shape, and the same default, as ``book_manager``'s INV-008
                flag.

        Returns:
            The stored row as :meth:`get_puzzle` reads it back, or ``None`` if
            the puzzle does not exist or is held by a book this panel cannot
            name (:meth:`_row_an_edit_may_touch`).

        Raises:
            EditNeedsConfirmation: a book holds this puzzle and ``confirmed``
                is false (CARD-251 AC-2). Raised first, so an unconfirmed save
                measures nothing and writes nothing.
            NotUniquelySolvable: the grid is not a readable grid, or its clue
                set does not have exactly one solution. Nothing is written.
            EditNotVerified: the grid is not the one whose grade was shown for
                this puzzle (AC-6). Nothing is written.
            ReplacementExtentChanged: the grid is not the stored grid's size
                (CARD-251 AC-5), booked or not. Nothing is written.
            RegradeInsideABook: a book holds this puzzle and the grid grades
                into another tier (CARD-251 AC-4 / G-2). Enforced here as well
                as at the verify, by the same discipline the confirmation
                follows: a save posted straight at the route, with no page in
                front of it, writes nothing either.

        A verification is **not** consumed by a save. A retried save of the
        same grid — a double click, a write that failed on the connection —
        must not have to buy a second solve, and storing the same proved grid
        twice differs only in the stamp. What a save never permits is a
        *different* grid, which is the hole :class:`EditNotVerified` closes.

        Order matters, and it is: *may this row be edited* (a cheap read),
        *has the owner confirmed its book* (CARD-251 — before the solve, so an
        unconfirmed save measures nothing as well as writing nothing),
        *is this grid a puzzle* (the gate — so a grid that is not one is
        refused for not being one, which is the stronger answer than "you did
        not verify it"), *was this grid verified* (the two-phase flow's own
        hole), *is it the stored grid's size* (CARD-251 AC-5 — after the
        verification check, so a save carrying a grid nobody verified is still
        refused for not being verified), *would it regrade a booked puzzle*
        (CARD-251 G-2), then the write.
        """
        row = self._row_an_edit_may_touch(puzzle_id)
        if row is None:
            return None

        self._refuse_unless_confirmed_for_its_book(row, confirmed)
        proof = self._refuse_unless_uniquely_solvable(grid)
        self._refuse_unless_verified(puzzle_id, grid)
        self._refuse_unless_the_stored_extent(row, grid)

        row_clues, column_clues = compute_clues(grid)
        derived = {
            "grid": grid,
            "clues_rows": [list(clue) for clue in row_clues],
            "clues_cols": [list(clue) for clue in column_clues],
            "width": len(grid[0]),
            "height": len(grid),
            **self._grade_of(proof),
        }
        # G-2: the verify refuses a regrade so the owner learns it with the
        # grade, and the store refuses it so a save posted straight at the
        # route cannot walk past that. Read off `derived` — the grade this
        # write would store — rather than graded a second time (ADR-0029/R2).
        self._refuse_a_regrade_inside_a_book(row, derived["difficulty_tier"])
        edited_at = datetime.now(timezone.utc)

        if self._session_factory is None:
            puzzle = self.puzzles.get(puzzle_id)
            if puzzle is None:  # pragma: no cover - re-read of a row just read
                return None
            puzzle.update(derived)
            # Aware, like this mode's own `created_at`.
            puzzle["manually_edited_at"] = edited_at.isoformat()
            return self.get_puzzle(puzzle_id)

        import uuid as uuid_module
        from nonogram.db.models import Puzzle

        try:
            puzzle_uuid = uuid_module.UUID(puzzle_id) if isinstance(puzzle_id, str) else puzzle_id
        except ValueError:  # pragma: no cover - screened by the read above
            return None
        with self._session_factory() as db:
            row = db.query(Puzzle).filter(Puzzle.id == puzzle_uuid).first()
            if row is None:  # pragma: no cover - re-read of a row just read
                return None
            # Column by column rather than through a loop over `derived`, so
            # a reader can see which five columns an edit moves without
            # holding `derived`'s keys in their head. It is no longer what
            # keeps the write *visible to G-1*: the guard used to recognise
            # grid writes by shape, which made this spelling load-bearing and
            # the legacy branch's `puzzle.update(derived)` invisible (review
            # cycle 1, F-002). The guard is now default-deny — any write at
            # all makes a method a candidate that must reach the gate — so
            # either spelling is seen, and this one is kept for the reader.
            row.grid = derived["grid"]
            row.clues_rows = derived["clues_rows"]
            row.clues_cols = derived["clues_cols"]
            row.width = derived["width"]
            row.height = derived["height"]
            row.difficulty_score = derived["difficulty_score"]
            row.difficulty_tier = derived["difficulty_tier"]
            row.strategies_used = derived["strategies_used"]
            # Naive UTC, like the `DateTime` columns beside it (`created_at`
            # is `func.now()` and carries no offset either).
            row.manually_edited_at = edited_at.replace(tzinfo=None)
        return self.get_puzzle(puzzle_id)

    def _parse_sort_string(self, sort_by: str) -> List[Tuple[str, str]]:
        """Parse sort_by string into list of (column, direction) tuples.

        Format: "batch_id,-size,quality" → [("batch_id", "asc"), ("size", "desc"), ("quality", "asc")]
        Prefix with - for descending. The token vocabulary — stored columns
        plus CARD-122's computed ``tier_rank`` / ``shorter_side`` /
        ``longer_side`` — is documented on :attr:`PuzzleFilter.sort_by`.

        Args:
            sort_by: Sort specification string

        Returns:
            List of (column_name, direction) tuples
        """
        sorts = []
        for part in sort_by.split(","):
            part = part.strip()
            if not part:
                continue
            if part.startswith("-"):
                sorts.append((part[1:], "desc"))
            else:
                sorts.append((part, "asc"))
        return sorts

    def _apply_sort_to_query(self, query, sort_list: List[Tuple[str, str]]):
        """Apply multi-column sort to SQLAlchemy query.

        Applied before ``count()`` and before ``offset()/limit()``, which is
        the whole point: the page the caller gets back is a slice of *this*
        order (see :attr:`PuzzleFilter.sort_by`).

        Args:
            query: SQLAlchemy query object
            sort_list: List of (column_name, direction) tuples

        Returns:
            Query with order_by applied
        """
        from nonogram.db.models import Puzzle
        from sqlalchemy import case, desc, func, or_

        col_map = {
            "batch_id": Puzzle.batch_id,
            "size": Puzzle.width,
            "width": Puzzle.width,
            "height": Puzzle.height,
            "quality": Puzzle.quality_score,
            "quality_score": Puzzle.quality_score,
            "difficulty": Puzzle.difficulty_tier,
            "difficulty_tier": Puzzle.difficulty_tier,
            "created_at": Puzzle.created_at,
            "puzzle_name": Puzzle.puzzle_name,
            # CARD-122's computed keys, appended. A CASE rather than a
            # two-argument min()/max() for the same reason the longest-side
            # filter uses one: SQLite's min()/max() are scalars of two
            # arguments while Postgres' are aggregates of one (least()/
            # greatest() are its scalars), and the expression has to mean one
            # thing on both. The tier table is derived from `_tier_rank`, so
            # this branch and the in-memory one rank a row identically.
            "id": Puzzle.id,
            "tier_rank": case(
                _TIER_RANK_BY_SPELLING,
                value=func.trim(func.lower(Puzzle.difficulty_tier)),
                else_=len(PLAN_TIERS),
            ),
            "shorter_side": case(
                (Puzzle.width < Puzzle.height, Puzzle.width), else_=Puzzle.height
            ),
            "longer_side": case(
                (Puzzle.width > Puzzle.height, Puzzle.width), else_=Puzzle.height
            ),
        }

        for col_name, direction in sort_list:
            if col_name not in col_map:
                continue
            col = col_map[col_name]
            query = query.order_by(desc(col) if direction == "desc" else col)

        return query

    @staticmethod
    def _side_bounds(bounds) -> Tuple[int, int]:
        """The ``(low, high)`` a side range means, validated.

        An absent bound is the supported limit on that end, so "from 25" and
        "to 15" are both complete requests. Out-of-range or inverted bounds
        raise, the way the exact-extent filter does — a range that can match
        nothing is a mistake to report, not an empty page to puzzle over.
        """
        if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
            raise ValueError(f"Side range must be a (from, to) pair, got {bounds!r}")
        low, high = bounds
        low = MIN_SIZE if low is None else low
        high = MAX_SIZE if high is None else high
        if not (MIN_SIZE <= low <= MAX_SIZE and MIN_SIZE <= high <= MAX_SIZE):
            raise ValueError(f"Size range must stay within {MIN_SIZE}-{MAX_SIZE} cells")
        if low > high:
            raise ValueError(f"Size range is inverted: from {low} to {high}")
        return low, high

    @staticmethod
    def _name_matches(needle: str, puzzle: dict) -> bool:
        wanted = needle.lower()
        return any(
            wanted in (puzzle.get(field) or "").lower()
            for field in ("puzzle_name", "source_image")
        )

    def filter_puzzles(self, filter_opts: PuzzleFilter) -> PuzzleListResponse:
        """Filter puzzles based on criteria (legacy in-memory or DB-backed).

        Args:
            filter_opts: PuzzleFilter with criteria

        Returns:
            PuzzleListResponse with filtered puzzles
        """
        # Validate filter
        if filter_opts.limit < 1 or filter_opts.limit > 100:
            raise ValueError("Limit must be 1-100")
        if filter_opts.offset < 0:
            raise ValueError("Offset must be >= 0")
        if filter_opts.size:
            # Named rather than unpacked blind. A caller passing a bare int —
            # extent as one number, which ADR-0022/R1 removed from every
            # boundary in CARD-027 — used to reach the unpack and die there
            # with "cannot unpack non-iterable int object", five frames from
            # anything that names the rule it broke (CARD-082).
            if not isinstance(filter_opts.size, (tuple, list)) or len(filter_opts.size) != 2:
                raise ValueError(
                    f"Size filter must be a (width, height) pair, got "
                    f"{filter_opts.size!r} — a grid's extent is two numbers "
                    f"(ADR-0022/R1)"
                )
            width, height = filter_opts.size
            if not (MIN_SIZE <= width <= MAX_SIZE and MIN_SIZE <= height <= MAX_SIZE):
                raise ValueError(f"Size dimensions must be {MIN_SIZE}-{MAX_SIZE}")
        if filter_opts.longest_side_range:
            self._side_bounds(filter_opts.longest_side_range)
        if filter_opts.quality_min and not (0 <= filter_opts.quality_min <= 100):
            raise ValueError("Quality min must be 0-100")

        # Validate date range
        if filter_opts.date_from and filter_opts.date_to:
            try:
                df = datetime.strptime(filter_opts.date_from, "%Y-%m-%d")
                dt = datetime.strptime(filter_opts.date_to, "%Y-%m-%d")
                if df > dt:
                    raise ValueError("Date from must be <= date to")
            except ValueError as e:
                raise ValueError(f"Invalid date format (use YYYY-MM-DD): {str(e)}")

        # Parse sort specification
        sort_list = self._parse_sort_string(filter_opts.sort_by)

        if self._session_factory is None:
            # Legacy mode: filter in-memory dict
            filtered = []
            for puzzle_id, puzzle in self.puzzles.items():
                # Batch ID filter
                if filter_opts.batch_id and puzzle.get("batch_id") != filter_opts.batch_id:
                    continue
                # Size filter
                if filter_opts.size:
                    width, height = filter_opts.size
                    if puzzle["width"] != width or puzzle["height"] != height:
                        continue
                # Longest-side range (CARD-122): max(width, height), not
                # "either side". A row with a side outside the supported range
                # matches nothing here — see the field's own note.
                if filter_opts.longest_side_range:
                    low, high = self._side_bounds(filter_opts.longest_side_range)
                    sides = (puzzle["width"], puzzle["height"])
                    if not all(MIN_SIZE <= side <= MAX_SIZE for side in sides):
                        continue
                    if not low <= max(sides) <= high:
                        continue
                # Difficulty filter. Matched by tier rather than by exact
                # string when the requested value names one: rows carry either
                # spelling — the pipeline writes the enum value ("easy"), older
                # rows the display label ("Easy") — so an exact comparison hid
                # whole populations (CARD-076 review F-002). A value that is
                # not a tier at all keeps the old exact behaviour rather than
                # matching everything.
                if filter_opts.difficulty:
                    wanted = tier_of_record(filter_opts.difficulty)
                    if wanted is None:
                        if puzzle["difficulty_tier"] != filter_opts.difficulty:
                            continue
                    elif tier_of_record(puzzle["difficulty_tier"]) is not wanted:
                        continue
                # Quality filter. An unmeasured puzzle (quality_score None —
                # what random mode stores since CARD-050) cannot satisfy a
                # minimum, so it is excluded rather than compared: `None < int`
                # raises, and this branch is reached from two routes that take
                # quality_min straight off the query string (ADR-0032/R2).
                # Excluding matches what the DB branch below has always done,
                # where SQL's `NULL >= n` is simply false.
                if filter_opts.quality_min:
                    quality = puzzle["quality_score"]
                    if quality is None or quality < filter_opts.quality_min:
                        continue
                # Theme filter
                if filter_opts.theme and puzzle["theme"] != filter_opts.theme:
                    continue
                # Status filter
                if filter_opts.status and puzzle["status"] != filter_opts.status:
                    continue
                # Strategy filter (FR-029): does this puzzle need that one?
                if filter_opts.strategy:
                    recorded = puzzle.get("strategies_used") or ()
                    if filter_opts.strategy not in recorded:
                        continue
                # Puzzle name filter: a case-insensitive substring of either
                # name a row can carry. Picture-derived rows often have no
                # puzzle_name at all and are listed under their source_image,
                # so a search that ignored it found nothing the page shows.
                if filter_opts.puzzle_name:
                    if not self._name_matches(filter_opts.puzzle_name, puzzle):
                        continue
                # Book ID filter
                if filter_opts.book_id:
                    if filter_opts.book_id == "unassigned":
                        if puzzle.get("book_id") is not None:
                            continue
                    else:
                        if puzzle.get("book_id") != filter_opts.book_id:
                            continue
                filtered.append(puzzle)

            # Apply multi-column sort (legacy: sort in Python). Applied to the
            # whole filtered set and *before* the slice below, so `paginated`
            # is a page of this order — the in-memory mirror of what
            # `_apply_sort_to_query` does ahead of OFFSET/LIMIT.
            for col_name, direction in reversed(sort_list):
                # CARD-122's computed keys first: `tier_rank`, `shorter_side`,
                # `longer_side` and `id` are not stored columns, and `id` in
                # particular must not fall through to the `or 0` default below
                # (a str against an int raises).
                if col_name in _COMPUTED_SORT_KEYS:
                    filtered.sort(
                        key=_COMPUTED_SORT_KEYS[col_name], reverse=(direction == "desc")
                    )
                    continue
                col_map_py = {
                    "batch_id": "batch_id",
                    "size": "width",
                    "width": "width",
                    "height": "height",
                    "quality": "quality_score",
                    "quality_score": "quality_score",
                    "difficulty": "difficulty_tier",
                    "difficulty_tier": "difficulty_tier",
                    "created_at": "created_at",
                    "puzzle_name": "puzzle_name",
                }
                if col_name in col_map_py:
                    py_col = col_map_py[col_name]
                    filtered.sort(
                        key=lambda p: p.get(py_col) or 0,
                        reverse=(direction == "desc")
                    )

            total = len(filtered)
            start = filter_opts.offset
            end = start + filter_opts.limit
            paginated = filtered[start:end]
            has_more = end < total

        else:
            # DB mode: query database
            from sqlalchemy import String, case, cast, or_
            from nonogram.db.models import Puzzle
            import uuid as uuid_module

            with self._session_factory() as db:
                query = db.query(Puzzle)

                # Apply filters
                if filter_opts.batch_id:
                    batch_uuid = uuid_module.UUID(filter_opts.batch_id) if isinstance(filter_opts.batch_id, str) else filter_opts.batch_id
                    query = query.filter(Puzzle.batch_id == batch_uuid)
                if filter_opts.size:
                    width, height = filter_opts.size
                    query = query.filter(Puzzle.width == width, Puzzle.height == height)
                if filter_opts.longest_side_range:
                    low, high = self._side_bounds(filter_opts.longest_side_range)
                    # CASE rather than a two-argument max(): SQLite's max() is
                    # a scalar of two arguments but Postgres' is an aggregate
                    # of one (greatest() is its scalar), and this expression
                    # has to mean the same thing on both.
                    longest = case(
                        (Puzzle.width > Puzzle.height, Puzzle.width), else_=Puzzle.height
                    )
                    query = query.filter(
                        Puzzle.width.between(MIN_SIZE, MAX_SIZE),
                        Puzzle.height.between(MIN_SIZE, MAX_SIZE),
                        longest.between(low, high),
                    )
                if filter_opts.difficulty:
                    # Both spellings, for the reason in the in-memory branch
                    # above: value and label are the same tier and a row may
                    # carry either.
                    wanted = tier_of_record(filter_opts.difficulty)
                    query = query.filter(
                        Puzzle.difficulty_tier.in_((wanted.value, wanted.label))
                        if wanted is not None
                        else Puzzle.difficulty_tier == filter_opts.difficulty
                    )
                if filter_opts.quality_min is not None:
                    query = query.filter(Puzzle.quality_score >= filter_opts.quality_min)
                if filter_opts.theme:
                    query = query.filter(Puzzle.theme == filter_opts.theme)
                if filter_opts.status:
                    query = query.filter(Puzzle.status == filter_opts.status)
                if filter_opts.strategy:
                    # The column is JSON, and the two databases this runs on
                    # disagree about how to look inside one: Postgres wants
                    # JSONB containment, SQLite wants json_each. Matching the
                    # *quoted* name inside the serialized text is the one
                    # expression both accept, and it is exact rather than
                    # approximate because the vocabulary is closed
                    # (STRATEGY_NAMES): the names contain no quote, no
                    # wildcard and no substring of one another, so `"guess"`
                    # can only match the element `guess` — never a longer
                    # name, and never other text in the row (a source image
                    # called `guess.png` is not quoted this way).
                    query = query.filter(
                        cast(Puzzle.strategies_used, String).like(
                            f'%"{filter_opts.strategy}"%'
                        )
                    )

                # Date range filter
                if filter_opts.date_from:
                    df = datetime.strptime(filter_opts.date_from, "%Y-%m-%d")
                    query = query.filter(Puzzle.created_at >= df)
                if filter_opts.date_to:
                    dt = datetime.strptime(filter_opts.date_to, "%Y-%m-%d")
                    # Add 1 day to make it inclusive of the entire date_to day
                    query = query.filter(Puzzle.created_at < (dt.replace(hour=0, minute=0, second=0) + __import__('datetime').timedelta(days=1)))

                # Free-text name search over both name fields (see the
                # in-memory branch for why source_image is included).
                if filter_opts.puzzle_name:
                    pattern = f"%{filter_opts.puzzle_name}%"
                    query = query.filter(
                        or_(Puzzle.puzzle_name.ilike(pattern), Puzzle.source_image.ilike(pattern))
                    )

                # Book ID filter
                if filter_opts.book_id:
                    if filter_opts.book_id == "unassigned":
                        query = query.filter(Puzzle.book_id.is_(None))
                    else:
                        book_uuid = uuid_module.UUID(filter_opts.book_id) if isinstance(filter_opts.book_id, str) else filter_opts.book_id
                        query = query.filter(Puzzle.book_id == book_uuid)

                # Apply multi-column sort
                query = self._apply_sort_to_query(query, sort_list)

                # Get total count before paginating
                total = query.count()

                # Paginate
                rows = query.offset(filter_opts.offset).limit(filter_opts.limit).all()
                paginated = [self._row_to_dict(row) for row in rows]

            has_more = (filter_opts.offset + filter_opts.limit) < total

        return PuzzleListResponse(
            puzzles=paginated,
            total_count=total,
            offset=filter_opts.offset,
            limit=filter_opts.limit,
            has_more=has_more,
        )

    def get_puzzle(self, puzzle_id: str) -> Optional[Dict[str, Any]]:
        """Get a single puzzle by ID (legacy in-memory or DB-backed).

        Args:
            puzzle_id: ID of puzzle to retrieve

        Returns:
            Puzzle dict, or None if not found
        """
        if self._session_factory is None:
            # Legacy mode
            return self.puzzles.get(puzzle_id)
        else:
            # DB mode
            import uuid as uuid_module
            from nonogram.db.models import Puzzle

            with self._session_factory() as db:
                puzzle_uuid = uuid_module.UUID(puzzle_id) if isinstance(puzzle_id, str) else puzzle_id
                puzzle = db.query(Puzzle).filter(Puzzle.id == puzzle_uuid).first()
                return self._row_to_dict(puzzle) if puzzle else None

    def get_puzzles(self, puzzle_ids) -> Dict[Any, Dict[str, Any]]:
        """The records :meth:`get_puzzle` returns for each of ``puzzle_ids``, in one read.

        Keyed by each id exactly as given, in first-seen order. An id no row
        matches is left out, and so is one :meth:`get_puzzle` would refuse
        with ``ValueError`` or ``TypeError`` (a string that is not a UUID, an
        unhashable value) — the verdict every caller reached by catching those
        two. In DB mode it is one session and one ``WHERE id IN (...)`` query,
        and none at all when no id can match a row (CARD-157).

        Reads by **id** only, never by ``puzzles.book_id``: a caller passes the
        book's own ``puzzle_ids``, because nothing reads membership from that
        mirror (ADR-0033/R1).
        """
        puzzle_ids = list(puzzle_ids)
        if self._session_factory is None:
            found: Dict[Any, Dict[str, Any]] = {}
            for puzzle_id in puzzle_ids:
                try:
                    record = self.puzzles.get(puzzle_id)
                except TypeError:
                    continue
                if record is not None:
                    found[puzzle_id] = record
            return found

        import uuid as uuid_module
        from nonogram.db.models import Puzzle

        wanted: Dict[Any, Any] = {}
        for puzzle_id in puzzle_ids:
            if isinstance(puzzle_id, uuid_module.UUID):
                wanted[puzzle_id] = puzzle_id
            elif isinstance(puzzle_id, str):
                try:
                    wanted[puzzle_id] = uuid_module.UUID(puzzle_id)
                except ValueError:
                    continue
        if not wanted:
            return {}

        with self._session_factory() as db:
            rows = {
                row.id: row
                for row in db.query(Puzzle).filter(Puzzle.id.in_(set(wanted.values()))).all()
            }
            # One dict per id, as one get_puzzle call per id would give: a
            # caller that writes into a record must not reach another id's.
            return {
                puzzle_id: self._row_to_dict(rows[puzzle_uuid])
                for puzzle_id, puzzle_uuid in wanted.items()
                if puzzle_uuid in rows
            }

    @staticmethod
    def _clean_puzzle_name(name: Optional[str]) -> Optional[str]:
        """A name as stored: trimmed, and ``None`` when blank.

        Blank clears the name, so the list falls back to showing the source
        picture's filename — which is what a row the pipeline wrote shows.

        Raises:
            ValueError: the name is longer than :data:`MAX_PUZZLE_NAME_LENGTH`.
        """
        cleaned = " ".join((name or "").split())
        if len(cleaned) > MAX_PUZZLE_NAME_LENGTH:
            raise ValueError(
                f"Puzzle name must be at most {MAX_PUZZLE_NAME_LENGTH} characters"
            )
        return cleaned or None

    def rename_puzzle(self, puzzle_id: str, name: Optional[str]) -> bool:
        """Set a puzzle's display name; a blank name clears it.

        Returns:
            True if renamed, False if not found

        Raises:
            ValueError: the name is too long.
        """
        cleaned = self._clean_puzzle_name(name)
        if self._session_factory is None:
            if puzzle_id not in self.puzzles:
                return False
            self.puzzles[puzzle_id]["puzzle_name"] = cleaned
            return True

        import uuid as uuid_module
        from nonogram.db.models import Puzzle

        try:
            puzzle_uuid = uuid_module.UUID(puzzle_id)
        except ValueError:
            return False
        with self._session_factory() as db:
            puzzle = db.query(Puzzle).filter(Puzzle.id == puzzle_uuid).first()
            if not puzzle:
                return False
            puzzle.puzzle_name = cleaned
            return True

    def batch_summaries(self, batch_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Per batch: puzzle counts by status and the first few puzzle names.

        Counted from the puzzles themselves rather than read from the batch
        row's ``puzzle_count``, which is written once at generation and does
        not follow later deletions.

        Returns:
            ``{batch_id: {"total": n, "draft": n, "approved": n,
            "rejected": n, "in_book": n, "names": [...]}}`` for every id
            asked about, zeros included.
        """
        summaries: Dict[str, Dict[str, Any]] = {
            batch_id: {
                "total": 0,
                **{status.value: 0 for status in PuzzleStatus},
                "names": [],
            }
            for batch_id in batch_ids
        }

        def count(batch_id, status, name):
            summary = summaries.get(batch_id)
            if summary is None:
                return
            summary["total"] += 1
            if status in summary:
                summary[status] += 1
            if name and len(summary["names"]) < 3 and name not in summary["names"]:
                summary["names"].append(name)

        if self._session_factory is None:
            for puzzle in self.puzzles.values():
                count(
                    puzzle.get("batch_id"),
                    puzzle.get("status"),
                    puzzle.get("puzzle_name") or puzzle.get("source_image"),
                )
            return summaries

        if not batch_ids:
            return summaries

        import uuid as uuid_module
        from nonogram.db.models import Puzzle

        with self._session_factory() as db:
            rows = (
                db.query(Puzzle.batch_id, Puzzle.status, Puzzle.puzzle_name, Puzzle.source_image)
                .filter(Puzzle.batch_id.in_([uuid_module.UUID(b) for b in batch_ids]))
                .order_by(Puzzle.created_at)
                .all()
            )
            for batch_id, status, puzzle_name, source_image in rows:
                count(str(batch_id), status, puzzle_name or source_image)
        return summaries

    # ------------------------------------------------------------------
    # CARD-100 — membership, and the one rule every status change obeys
    # ------------------------------------------------------------------

    @staticmethod
    def _holds_a_book(book_id, status) -> bool:
        """Is this puzzle in a book?

        ``book_id`` is the fact this card made real. The ``in_book`` status is
        read too, and only read: rows written before CARD-100 carry it, and
        they are still in books. Nothing writes it any more except the legacy
        :meth:`mark_in_book`, the way ``difficulty.tier_of_record`` still
        answers for the retired guess tier without anything assigning it.
        """
        return book_id is not None or status == PuzzleStatus.IN_BOOK.value

    def in_a_book(self, puzzle_id: str) -> bool:
        """Whether a stored puzzle belongs to a book (CARD-100)."""
        puzzle = self.get_puzzle(puzzle_id)
        if puzzle is None:
            return False
        return self._holds_a_book(puzzle.get("book_id"), puzzle.get("status"))

    def _set_status(self, puzzle_id: str, status: PuzzleStatus) -> bool:
        """Move one puzzle to ``status``, unless a book is built on it.

        The three per-puzzle actions were three copies of the same six lines,
        and none of them asked about books — so a per-puzzle Reject walked
        straight past the protection the bulk path takes care over (CARD-100).
        One implementation, one rule, one place for it to be wrong.

        Returns:
            True if the puzzle moved. False if it does not exist **or** a book
            holds it; callers that need to tell those apart ask
            :meth:`in_a_book` first, which is what the routes do so they can
            say why.
        """
        if self._session_factory is None:
            puzzle = self.puzzles.get(puzzle_id)
            if puzzle is None:
                return False
            if self._holds_a_book(puzzle.get("book_id"), puzzle.get("status")):
                return False
            puzzle["status"] = status.value
            return True

        import uuid as uuid_module
        from nonogram.db.models import Puzzle

        with self._session_factory() as db:
            puzzle_uuid = uuid_module.UUID(puzzle_id) if isinstance(puzzle_id, str) else puzzle_id
            row = db.query(Puzzle).filter(Puzzle.id == puzzle_uuid).first()
            if row is None:
                return False
            if self._holds_a_book(row.book_id, row.status):
                return False
            row.status = status.value
            return True

    def assign_to_book(self, puzzle_ids, book_id: str) -> int:
        """Record that a book holds these puzzles (CARD-100).

        Called by :class:`BookManager` as it edits ``Book.puzzle_ids``, so the
        two sides of membership are written in one gesture. The curation status
        is deliberately left alone: a puzzle is approved *and* in a book, and
        overwriting that would leave removal guessing what to restore.

        Returns:
            How many rows were written.
        """
        return self._write_book_id(puzzle_ids, book_id)

    def release_from_book(self, puzzle_ids) -> int:
        """Clear the book from these puzzles (CARD-100)."""
        return self._write_book_id(puzzle_ids, None)

    def _write_book_id(self, puzzle_ids, book_id) -> int:
        written = 0
        puzzle_ids = list(puzzle_ids)
        if self._session_factory is None:
            for puzzle_id in puzzle_ids:
                puzzle = self.puzzles.get(puzzle_id)
                if puzzle is not None:
                    puzzle["book_id"] = book_id
                    written += 1
            return written

        import uuid as uuid_module
        from nonogram.db.models import Puzzle

        def as_uuid(value):
            try:
                return uuid_module.UUID(value) if isinstance(value, str) else value
            except (ValueError, AttributeError):
                return None

        wanted = [u for u in (as_uuid(p) for p in puzzle_ids) if u is not None]
        if not wanted:
            return 0
        with self._session_factory() as db:
            for row in db.query(Puzzle).filter(Puzzle.id.in_(wanted)):
                row.book_id = as_uuid(book_id)
                written += 1
        return written

    def approve_puzzle(self, puzzle_id: str) -> bool:
        """Mark puzzle as approved for book inclusion.

        Returns:
            True if approved; False if not found, or if a book holds it
            (CARD-100).
        """
        return self._set_status(puzzle_id, PuzzleStatus.APPROVED)

    def reject_puzzle(self, puzzle_id: str) -> bool:
        """Mark puzzle as rejected.

        Returns:
            True if rejected; False if not found, or if a book holds it
            (CARD-100).
        """
        return self._set_status(puzzle_id, PuzzleStatus.REJECTED)

    def restore_puzzle(self, puzzle_id: str) -> bool:
        """Restore rejected or approved puzzle back to draft.

        Returns:
            True if restored; False if not found, or if a book holds it
            (CARD-100) — remove it from the book first.
        """
        return self._set_status(puzzle_id, PuzzleStatus.DRAFT)

    def set_batch_status(self, batch_id: str, status: PuzzleStatus) -> BulkOutcome:
        """Move every puzzle of ``batch_id`` that is not in a book to ``status``.

        A puzzle already in a book is left alone: approving or rejecting it in
        bulk would silently detach it from the book's curation state.

        Returns:
            A :class:`BulkOutcome` — what changed, what needed nothing, and
            what a book held back (CARD-068). It was a bare count until the
            page had to explain itself.
        """
        if status is PuzzleStatus.IN_BOOK:
            raise ValueError("in_book is set by assigning to a book, not in bulk")
        changed = unchanged = in_book = 0
        if self._session_factory is None:
            for puzzle in self.puzzles.values():
                if puzzle.get("batch_id") != batch_id:
                    continue
                if puzzle.get("book_id") or puzzle["status"] == PuzzleStatus.IN_BOOK.value:
                    in_book += 1
                elif puzzle["status"] == status.value:
                    unchanged += 1
                else:
                    puzzle["status"] = status.value
                    changed += 1
            return BulkOutcome(changed, unchanged, in_book)

        import uuid as uuid_module
        from nonogram.db.models import Puzzle

        with self._session_factory() as db:
            rows = db.query(Puzzle).filter(Puzzle.batch_id == uuid_module.UUID(batch_id))
            for row in rows:
                if row.book_id is not None or row.status == PuzzleStatus.IN_BOOK.value:
                    in_book += 1
                elif row.status == status.value:
                    unchanged += 1
                else:
                    row.status = status.value
                    changed += 1
        return BulkOutcome(changed, unchanged, in_book)

    def puzzles_with_missing_books(self, known_book_ids=None) -> List[Tuple[str, str]]:
        """``(puzzle_id, book_id)`` for every puzzle naming a book that is gone.

        The state no other query here can reach: :func:`book_membership.backfill`
        walks books, so a puzzle whose book has been deleted is invisible to it
        (CARD-107). This walks the puzzles instead and asks the other way round.

        Ordered by puzzle id so two runs report the same list in the same
        order, which matters for a repair an operator reads before running.

        Args:
            known_book_ids: the ids that exist, used in in-memory mode only.
                The DB branch joins against ``books`` itself, which is
                authoritative whatever the caller believes.
        """
        if self._session_factory is None:
            # In-memory mode has no books table to join against, so the caller
            # supplies the ids — the book manager it is actually working with,
            # not a module singleton that may hold someone else's books. That
            # mistake made every booked puzzle look orphaned, and CARD-100's
            # command test caught it.
            known = {str(b) for b in (known_book_ids or ())}
            found = [
                (puzzle_id, str(puzzle["book_id"]))
                for puzzle_id, puzzle in self.puzzles.items()
                if puzzle.get("book_id") and str(puzzle["book_id"]) not in known
            ]
            return sorted(found)

        from nonogram.db.models import Book, Puzzle

        with self._session_factory() as db:
            rows = (
                db.query(Puzzle.id, Puzzle.book_id)
                .outerjoin(Book, Book.id == Puzzle.book_id)
                .filter(Puzzle.book_id.isnot(None), Book.id.is_(None))
                .order_by(Puzzle.id)
                .all()
            )
            return [(str(pid), str(bid)) for pid, bid in rows]

    def batch_action_counts(self, batch_id: str) -> Dict[str, int]:
        """How many puzzles each bulk action would touch, without touching any.

        The buttons name these numbers in their confirmations, so they are
        computed from the same rules the actions apply rather than from the
        rows a page happens to have rendered. An unknown batch is three zeros,
        not an error: a stale link should disable the buttons, not break the
        page.
        """
        approve = reject = delete_rejected = 0
        rejected = PuzzleStatus.REJECTED.value
        approved = PuzzleStatus.APPROVED.value
        in_book = PuzzleStatus.IN_BOOK.value

        def count(status: str, booked: bool) -> None:
            nonlocal approve, reject, delete_rejected
            if booked or status == in_book:
                return
            approve += status != approved
            reject += status != rejected
            delete_rejected += status == rejected

        if self._session_factory is None:
            for puzzle in self.puzzles.values():
                if puzzle.get("batch_id") == batch_id:
                    count(puzzle["status"], bool(puzzle.get("book_id")))
        else:
            import uuid as uuid_module
            from nonogram.db.models import Puzzle

            try:
                batch_uuid = uuid_module.UUID(batch_id)
            except (ValueError, AttributeError, TypeError):
                return {"approve": 0, "reject": 0, "delete_rejected": 0}
            with self._session_factory() as db:
                for row in db.query(Puzzle).filter(Puzzle.batch_id == batch_uuid):
                    count(row.status, row.book_id is not None)

        return {
            "approve": approve,
            "reject": reject,
            "delete_rejected": delete_rejected,
        }

    def delete_puzzle(self, puzzle_id: str) -> bool:
        """Delete one puzzle, whatever its status (callers check that).

        Returns:
            True if deleted, False if not found
        """
        if self._session_factory is None:
            return self.puzzles.pop(puzzle_id, None) is not None

        import uuid as uuid_module
        from nonogram.db.models import Puzzle

        with self._session_factory() as db:
            row = db.query(Puzzle).filter(Puzzle.id == uuid_module.UUID(puzzle_id)).first()
            if row is None:
                return False
            db.delete(row)
            return True

    def delete_rejected_in_batch(self, batch_id: str) -> BulkOutcome:
        """Delete every rejected puzzle of ``batch_id`` that is not in a book.

        Returns:
            A :class:`BulkOutcome` whose ``changed`` is the number deleted and
            whose ``in_book`` is the number of *rejected* puzzles a book kept
            out of it — the ones the owner asked to be rid of and still has
            (CARD-068). ``unchanged`` is not used: a puzzle that is not
            rejected was never in the scope of this action.
        """
        rejected = PuzzleStatus.REJECTED.value
        if self._session_factory is None:
            doomed, held = [], 0
            for puzzle_id, puzzle in self.puzzles.items():
                if puzzle.get("batch_id") != batch_id or puzzle["status"] != rejected:
                    continue
                if puzzle.get("book_id"):
                    held += 1
                else:
                    doomed.append(puzzle_id)
            for puzzle_id in doomed:
                del self.puzzles[puzzle_id]
            return BulkOutcome(changed=len(doomed), in_book=held)

        import uuid as uuid_module
        from nonogram.db.models import Puzzle

        with self._session_factory() as db:
            rows = db.query(Puzzle).filter(
                Puzzle.batch_id == uuid_module.UUID(batch_id),
                Puzzle.status == rejected,
            ).all()
            doomed = [row for row in rows if row.book_id is None]
            for row in doomed:
                db.delete(row)
            return BulkOutcome(changed=len(doomed), in_book=len(rows) - len(doomed))

    def mark_in_book(self, puzzle_id: str, book_id: str) -> bool:
        """Mark puzzle as included in a specific book.

        Args:
            puzzle_id: ID of puzzle
            book_id: ID of book

        Returns:
            True if marked, False if not found
        """
        if self._session_factory is None:
            # Legacy mode
            if puzzle_id not in self.puzzles:
                return False
            self.puzzles[puzzle_id]["status"] = PuzzleStatus.IN_BOOK.value
            self.puzzles[puzzle_id]["book_id"] = book_id
            return True
        else:
            # DB mode
            import uuid as uuid_module
            from nonogram.db.models import Puzzle

            with self._session_factory() as db:
                puzzle_uuid = uuid_module.UUID(puzzle_id) if isinstance(puzzle_id, str) else puzzle_id
                puzzle = db.query(Puzzle).filter(Puzzle.id == puzzle_uuid).first()
                if not puzzle:
                    return False
                puzzle.status = PuzzleStatus.IN_BOOK.value
                # CARD-100 (AC-6): this branch assigned the str straight to a
                # UUID column and raised, on the same argument the in-memory
                # branch accepts. Nothing in production called it, so nothing
                # noticed.
                puzzle.book_id = (
                    uuid_module.UUID(book_id) if isinstance(book_id, str) else book_id
                )
                return True

    def get_approved_puzzles(self, book_id: str) -> List[Dict[str, Any]]:
        """Get all puzzles approved for a specific book.

        Args:
            book_id: ID of the book

        Returns:
            List of puzzles in the book
        """
        if self._session_factory is None:
            # Legacy mode
            return [
                p
                for p in self.puzzles.values()
                if p.get("book_id") == book_id
            ]
        else:
            # DB mode
            import uuid as uuid_module

            from nonogram.db.models import Puzzle

            with self._session_factory() as db:
                rows = db.query(Puzzle).filter(
                    Puzzle.book_id == (
                        uuid_module.UUID(book_id) if isinstance(book_id, str) else book_id
                    ),
                ).all()
                return [self._row_to_dict(row) for row in rows]

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about puzzles in storage.

        Returns:
            Dict with counts by status
        """
        if self._session_factory is None:
            # Legacy mode
            stats = {
                "total": len(self.puzzles),
                "draft": 0,
                "approved": 0,
                "rejected": 0,
                "in_book": 0,
            }
            for puzzle in self.puzzles.values():
                status = puzzle["status"]
                if status in stats:
                    stats[status] += 1
            # CARD-100: "in a book" is the column, not the status. The status
            # tally above still counts legacy rows that carry it, so count the
            # column here and take whichever is larger rather than double-count.
            stats["in_book"] = max(
                stats["in_book"],
                sum(1 for p in self.puzzles.values() if p.get("book_id")),
            )
            return stats
        else:
            # DB mode
            from nonogram.db.models import Puzzle

            with self._session_factory() as db:
                total = db.query(Puzzle).count()
                draft_count = db.query(Puzzle).filter(Puzzle.status == PuzzleStatus.DRAFT.value).count()
                approved_count = db.query(Puzzle).filter(Puzzle.status == PuzzleStatus.APPROVED.value).count()
                rejected_count = db.query(Puzzle).filter(Puzzle.status == PuzzleStatus.REJECTED.value).count()
                in_book_count = db.query(Puzzle).filter(Puzzle.book_id.isnot(None)).count()

                return {
                    "total": total,
                    "draft": draft_count,
                    "approved": approved_count,
                    "rejected": rejected_count,
                    "in_book": in_book_count,
                }


# Global puzzle review service instance
_puzzle_review_service = PuzzleReviewService()


def get_puzzle_review_service() -> PuzzleReviewService:
    """Get the singleton puzzle review service."""
    return _puzzle_review_service
