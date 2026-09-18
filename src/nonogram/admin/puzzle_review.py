"""Puzzle review and filtering service for admin panel.

Handles filtering puzzles by various criteria and managing approval/rejection.
"""

import math
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from datetime import datetime, date, timezone

from nonogram.clues import compute_clues
from nonogram.difficulty import Tier, classify, score_difficulty, tier_of_record
from nonogram.errors import NotUniquelySolvable, SolverTimeout
from nonogram.limits import MAX_SIZE, MIN_SIZE
from nonogram.orchestrator import GENERATION_BUDGET_SECONDS
from nonogram.solver import MANY, RUNG_ORDER, solve


#: Every name FR-029's strategies list can carry, in the order a list is
#: written: ADR-0029's ladder rungs, then ``guess`` when the search branched.
#: A stored list holding anything else was written by an older caller that
#: invented its names (``"LineLogic"``, ``"backtracking"``), so it is not read
#: as a statement about the puzzle — see :meth:`PuzzleReviewService.strategies_for`.
STRATEGY_NAMES: Tuple[str, ...] = (*RUNG_ORDER, Tier.GUESS.value)

#: The longest name a puzzle can be given from the review list.
MAX_PUZZLE_NAME_LENGTH = 120


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
    #: A side range: ``(low, high)`` in cells, either bound optional. A grid
    #: matches when *at least one* of its sides falls inside — so a 20×30 is
    #: found by 25–30 as well as by 10–20. ``size`` above is the exact-extent
    #: filter the API keeps; this is the one the review page's from/to fields
    #: drive, since almost no picture-derived grid is square.
    side_range: Optional[Tuple[Optional[int], Optional[int]]] = None
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
    sort_by: str = "batch_id,-size,quality"  # Default sort: batch DESC, size ASC, quality DESC
    limit: int = 25
    offset: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for API."""
        return {
            "size": self.size,
            "side_range": self.side_range,
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
        }

    @staticmethod
    def from_dict(data: dict) -> "PuzzleFilter":
        """Create PuzzleFilter from dictionary."""
        return PuzzleFilter(
            size=data.get("size"),
            side_range=data.get("side_range"),
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
        )


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
        """
        self._refuse_unless_shaped_like_a_grid(grid)

        # ADR-0011's bound, not a caller's choice — which is why this takes no
        # budget argument. The audit's does, because raising the budget is how
        # an operator asks a deeper question of a table; a *write* that needed
        # longer than the generation budget to be proven was not proven.
        objection, cause, result = self._why_this_is_not_a_puzzle(
            grid, deadline_seconds=GENERATION_BUDGET_SECONDS
        )
        if objection is not None:
            raise NotUniquelySolvable(f"refusing to store a grid: {objection}") from cause
        return result

    @staticmethod
    def _strategies_of(result) -> List[str]:
        """FR-029's list from one solve: its rungs, then ``guess`` if it branched.

        ``guess`` is appended on the tier :func:`classify` returns rather than
        on ``branch_nodes`` read here, so ADR-0025's rule keeps one reader.
        A native reimplementation of ``regrade._strategies_used`` — that
        module imports SQLAlchemy, which this one must not require — held to
        the same answer from the test tree.
        """
        signals = result.signals
        strategies = list(signals.rungs)
        if classify(score_difficulty(signals), signals.branch_nodes) is Tier.GUESS:
            strategies.append(Tier.GUESS.value)
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

    def _parse_sort_string(self, sort_by: str) -> List[Tuple[str, str]]:
        """Parse sort_by string into list of (column, direction) tuples.

        Format: "batch_id,-size,quality" → [("batch_id", "asc"), ("size", "desc"), ("quality", "asc")]
        Prefix with - for descending.

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

        Args:
            query: SQLAlchemy query object
            sort_list: List of (column_name, direction) tuples

        Returns:
            Query with order_by applied
        """
        from nonogram.db.models import Puzzle
        from sqlalchemy import desc, or_

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
        }

        for col_name, direction in sort_list:
            if col_name not in col_map:
                continue
            col = col_map[col_name]
            query = query.order_by(desc(col) if direction == "desc" else col)

        return query

    @staticmethod
    def _side_bounds(side_range) -> Tuple[int, int]:
        """The ``(low, high)`` a side range means, validated.

        An absent bound is the supported limit on that end, so "from 25" and
        "to 15" are both complete requests. Out-of-range or inverted bounds
        raise, the way the exact-extent filter does — a range that can match
        nothing is a mistake to report, not an empty page to puzzle over.
        """
        if not isinstance(side_range, (tuple, list)) or len(side_range) != 2:
            raise ValueError(f"Side range must be a (from, to) pair, got {side_range!r}")
        low, high = side_range
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
        if filter_opts.side_range:
            low, high = self._side_bounds(filter_opts.side_range)
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
                if filter_opts.side_range:
                    low, high = self._side_bounds(filter_opts.side_range)
                    if not any(low <= side <= high for side in (puzzle["width"], puzzle["height"])):
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
                # Quality filter
                if filter_opts.quality_min and puzzle["quality_score"] < filter_opts.quality_min:
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

            # Apply multi-column sort (legacy: sort in Python)
            for col_name, direction in reversed(sort_list):
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
            from sqlalchemy import String, cast, or_
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
                if filter_opts.side_range:
                    low, high = self._side_bounds(filter_opts.side_range)
                    query = query.filter(
                        or_(Puzzle.width.between(low, high), Puzzle.height.between(low, high))
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

    def approve_puzzle(self, puzzle_id: str) -> bool:
        """Mark puzzle as approved for book inclusion.

        Args:
            puzzle_id: ID of puzzle to approve

        Returns:
            True if approved, False if not found
        """
        if self._session_factory is None:
            # Legacy mode
            if puzzle_id not in self.puzzles:
                return False
            self.puzzles[puzzle_id]["status"] = PuzzleStatus.APPROVED.value
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
                puzzle.status = PuzzleStatus.APPROVED.value
                return True

    def reject_puzzle(self, puzzle_id: str) -> bool:
        """Mark puzzle as rejected.

        Args:
            puzzle_id: ID of puzzle to reject

        Returns:
            True if rejected, False if not found
        """
        if self._session_factory is None:
            # Legacy mode
            if puzzle_id not in self.puzzles:
                return False
            self.puzzles[puzzle_id]["status"] = PuzzleStatus.REJECTED.value
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
                puzzle.status = PuzzleStatus.REJECTED.value
                return True

    def restore_puzzle(self, puzzle_id: str) -> bool:
        """Restore rejected or approved puzzle back to draft.

        Args:
            puzzle_id: ID of puzzle to restore

        Returns:
            True if restored, False if not found
        """
        if self._session_factory is None:
            # Legacy mode
            if puzzle_id not in self.puzzles:
                return False
            self.puzzles[puzzle_id]["status"] = PuzzleStatus.DRAFT.value
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
                puzzle.status = PuzzleStatus.DRAFT.value
                return True

    def set_batch_status(self, batch_id: str, status: PuzzleStatus) -> int:
        """Move every puzzle of ``batch_id`` that is not in a book to ``status``.

        A puzzle already in a book is left alone: approving or rejecting it in
        bulk would silently detach it from the book's curation state.

        Returns:
            How many puzzles changed status.
        """
        if status is PuzzleStatus.IN_BOOK:
            raise ValueError("in_book is set by assigning to a book, not in bulk")
        changed = 0
        if self._session_factory is None:
            for puzzle in self.puzzles.values():
                if (
                    puzzle.get("batch_id") == batch_id
                    and not puzzle.get("book_id")
                    and puzzle["status"] not in (PuzzleStatus.IN_BOOK.value, status.value)
                ):
                    puzzle["status"] = status.value
                    changed += 1
            return changed

        import uuid as uuid_module
        from nonogram.db.models import Puzzle

        with self._session_factory() as db:
            rows = db.query(Puzzle).filter(
                Puzzle.batch_id == uuid_module.UUID(batch_id),
                Puzzle.book_id.is_(None),
                Puzzle.status.notin_([PuzzleStatus.IN_BOOK.value, status.value]),
            )
            for row in rows:
                row.status = status.value
                changed += 1
        return changed

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

    def delete_rejected_in_batch(self, batch_id: str) -> int:
        """Delete every rejected puzzle of ``batch_id`` that is not in a book.

        Returns:
            How many puzzles were deleted.
        """
        if self._session_factory is None:
            doomed = [
                puzzle_id
                for puzzle_id, puzzle in self.puzzles.items()
                if puzzle.get("batch_id") == batch_id
                and puzzle["status"] == PuzzleStatus.REJECTED.value
                and not puzzle.get("book_id")
            ]
            for puzzle_id in doomed:
                del self.puzzles[puzzle_id]
            return len(doomed)

        import uuid as uuid_module
        from nonogram.db.models import Puzzle

        with self._session_factory() as db:
            rows = db.query(Puzzle).filter(
                Puzzle.batch_id == uuid_module.UUID(batch_id),
                Puzzle.book_id.is_(None),
                Puzzle.status == PuzzleStatus.REJECTED.value,
            ).all()
            for row in rows:
                db.delete(row)
            return len(rows)

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
                puzzle.book_id = book_id
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
                if p.get("status") == PuzzleStatus.IN_BOOK.value
                and p.get("book_id") == book_id
            ]
        else:
            # DB mode
            from nonogram.db.models import Puzzle

            with self._session_factory() as db:
                rows = db.query(Puzzle).filter(
                    Puzzle.status == PuzzleStatus.IN_BOOK.value,
                    Puzzle.book_id == book_id,
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
            return stats
        else:
            # DB mode
            from nonogram.db.models import Puzzle

            with self._session_factory() as db:
                total = db.query(Puzzle).count()
                draft_count = db.query(Puzzle).filter(Puzzle.status == PuzzleStatus.DRAFT.value).count()
                approved_count = db.query(Puzzle).filter(Puzzle.status == PuzzleStatus.APPROVED.value).count()
                rejected_count = db.query(Puzzle).filter(Puzzle.status == PuzzleStatus.REJECTED.value).count()
                in_book_count = db.query(Puzzle).filter(Puzzle.status == PuzzleStatus.IN_BOOK.value).count()

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


class MockGenerator:
    """A cheap generator for tests and demos that still produces real puzzles.

    "Mock" is historical and now means only *cheap* — it does not call the
    orchestrator, so it skips naming, the retry policies and the image path.
    What it no longer skips is the one thing that makes a grid a puzzle.

    Until CARD-080 it emitted a random 50%-density grid, clue lists of random
    integers **unrelated to that grid**, and a random ``difficulty_score`` and
    tier. Almost none of its output was uniquely solvable, and 29 tests fed it
    to :meth:`PuzzleReviewService.add_puzzle` — so the suite's picture of "a
    stored puzzle" was a non-puzzle with invented clues and an invented grade.
    That is the same defect as ``image_to_puzzle.create_puzzle_from_image``,
    the function that wrote the twenty rows deleted on 2026-09-14, and it was
    still shipping in ``src/`` after that one was removed.

    Three things changed, all of them "ask, don't invent":

    * the clues come from :func:`nonogram.clues.compute_clues` on the grid it
      actually produced (CARD-051's one encoder), so grid and clues agree;
    * the grid is resampled until the solver certifies exactly one solution
      (CON-005), so its output passes the storage guard because it deserves to
      and not because the guard was relaxed;
    * the grade comes from that same solve through the real scorer and
      classifier (ADR-0029, ADR-0025/R2), so no second grading implementation
      lives here either.

    Density is 0.65 rather than 0.5 deliberately. Uniqueness is not uniform in
    density — measured over 20 grids per cell, a random grid is uniquely
    solvable 0/20 at density 0.2 and 0.35, 2-12/20 at 0.5, and 17-18/20 at
    0.65, for sizes 10 to 20. Sparse grids are the hard ones: the structural
    tension that makes a sparse grid uniquely solvable is the same tension that
    makes it hard to find. At 0.65 the loop below almost always succeeds on its
    first or second draw, at a few milliseconds a solve.

    **Every puzzle this emits is Easy, and that is structural rather than a
    tuning choice.** Measured over 25 puzzles at sizes 10/15/20: all Easy, all
    scoring exactly 33. Widening the band does not move it — 0.55-0.75 and
    0.5-0.8 both give the same answer — because a dense random grid that *is*
    uniquely solvable is exactly the kind line logic settles on the bottom rung
    with share 1.0, which pins the score at the Easy band's top edge. So a test
    that needs a second tier cannot get one from here: pin a grid the way
    ``tests/test_admin_regrade.py``'s ``GUESS_GRID`` is pinned — seeded search,
    literal cells, premise asserted against the solver — or it will pass
    without ever exercising the tier it claims to (CARD-080 review, F-004).
    """

    #: Fill density. A measured choice, not a default — see the class
    #: docstring; lowering it makes the resample loop expensive fast.
    DENSITY = 0.65

    #: How many grids to draw before giving up on one puzzle. Generous: the
    #: expected number of draws at DENSITY is under two, so reaching this bound
    #: means something about the solver or the extent has changed, and saying so
    #: loudly beats returning a grid nobody checked.
    MAX_DRAWS = 40

    def __init__(self, seed=None):
        """Initialize the generator. ``seed`` makes a run reproducible."""
        import random
        self.rng = random.Random(seed)

    def generate_batch(self, count, sizes, theme='christmas'):
        """Generate a batch of puzzles, every one of them uniquely solvable.

        Args:
            count: Number of puzzles to generate
            sizes: List of grid sizes as int or (width, height) tuples
                  Examples: [15, 20] or [(20, 20), (36, 20)]
            theme: Theme name

        Returns:
            List of puzzle dicts, in the shape ``add_puzzle`` takes.

        Raises:
            NotUniquelySolvable: no uniquely solvable grid was found for an
                extent within :attr:`MAX_DRAWS` draws. Raised rather than
                returning the last draw: a caller that asked for a puzzle and
                silently got a non-puzzle is the failure this card is about.
        """
        puzzles = []

        for i in range(count):
            size_spec = self.rng.choice(sizes) if sizes else 15

            # Handle both int and (width, height) tuple formats
            if isinstance(size_spec, (tuple, list)):
                width, height = size_spec
            else:
                width = height = size_spec

            grid, clues_rows, clues_cols, score, tier, strategies = (
                self._draw_until_unique(width, height)
            )

            puzzle = {
                'grid': grid,
                'clues_rows': clues_rows,
                'clues_cols': clues_cols,
                'width': width,
                'height': height,
                'theme': theme,
                'difficulty_score': score,
                'difficulty_tier': tier,
                'quality_score': self.rng.randint(1, 100),
                'recognizability': self.rng.choice(['low', 'medium', 'high']),
                'strategies_used': strategies,
            }
            puzzles.append(puzzle)

        return puzzles

    def _draw_until_unique(self, width, height):
        """Draw grids at :attr:`DENSITY` until the solver certifies one.

        The solve that certifies the grid is the solve its grade comes from —
        one solver entry per puzzle, the rule ADR-0029/R2 states for the real
        pipeline and which there is no reason to break here.
        """
        for _ in range(self.MAX_DRAWS):
            grid = [
                [self.rng.random() < self.DENSITY for _ in range(width)]
                for _ in range(height)
            ]
            row_clues, column_clues = compute_clues(grid)
            try:
                result = solve(
                    row_clues,
                    column_clues,
                    deadline=time.monotonic() + GENERATION_BUDGET_SECONDS,
                )
            except SolverTimeout:
                continue
            if result.solution_count != 1:
                continue

            score = score_difficulty(result.signals)
            tier = classify(score, result.signals.branch_nodes)
            return (
                grid,
                [list(run) for run in row_clues],
                [list(run) for run in column_clues],
                math.ceil(score),
                tier.value,
                # FR-029, off the same certifying solve as the grade beside it
                # (CARD-072). Before this the dict below carried a hardcoded
                # ``['LineLogic', 'ConstraintProp']`` — names this system's
                # solver has never produced, stored in the same column the
                # real pipeline writes, where nothing downstream could tell
                # them apart. Borrowed from ``PuzzleReviewService`` rather than
                # copied: one rule for appending ``guess`` (ADR-0025/R2), and
                # a demo generator is not a reason to acquire a second.
                PuzzleReviewService._strategies_of(result),
            )

        raise NotUniquelySolvable(
            f"no uniquely solvable {width}x{height} grid in {self.MAX_DRAWS} draws "
            f"at density {self.DENSITY}; returning an unchecked grid is what "
            "CARD-080 exists to prevent"
        )
