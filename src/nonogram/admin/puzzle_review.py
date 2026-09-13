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
from nonogram.difficulty import classify, score_difficulty, tier_of_record
from nonogram.errors import NotUniquelySolvable, SolverTimeout
from nonogram.limits import MAX_SIZE, MIN_SIZE
from nonogram.orchestrator import GENERATION_BUDGET_SECONDS
from nonogram.solver import MANY, solve


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
    ) -> Optional[str]:
        """The solver's objection to ``grid``, or ``None`` if it has none.

        The single place either path asks the question, so the write boundary
        and the audit cannot drift into disagreeing about what "a puzzle"
        means. It answers in the audit's voice — a reason, not a refusal —
        because a reason reads correctly in a report *and* inside the
        exception the write path wraps it in, where the reverse is not true.

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
        except (TypeError, ValueError) as exc:
            return f"not a readable grid: {exc}"

        try:
            result = solve(
                row_clues,
                column_clues,
                deadline=time.monotonic() + deadline_seconds,
            )
        except SolverTimeout:
            return (
                f"uniqueness could not be proven within {deadline_seconds}s "
                "— unproven is not proven"
            )

        if result.solution_count != 1:
            counted = "2 or more" if result.solution_count == MANY else "0"
            return (
                f"the clue set has {counted} solutions, and a clue set that is "
                "not uniquely solvable is not a puzzle (FR-006)"
            )
        return None

    def _refuse_unless_uniquely_solvable(
        self, grid: object, *, deadline_seconds: float = GENERATION_BUDGET_SECONDS
    ) -> None:
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
        :meth:`_refuse_unless_shaped_like_a_grid` for why the two differ.

        Raises:
            NotUniquelySolvable: the grid is not a readable grid, its clue set
                has 0 or >= 2 solutions, or the solve passed its deadline
                (ADR-0011) without concluding.
        """
        self._refuse_unless_shaped_like_a_grid(grid)

        objection = self._why_this_is_not_a_puzzle(grid, deadline_seconds=deadline_seconds)
        if objection is not None:
            raise NotUniquelySolvable(f"refusing to store a grid: {objection}")

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
            objection = self._why_this_is_not_a_puzzle(rows, deadline_seconds=deadline_seconds)
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
            strategies_used: List of strategy names
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
        self._refuse_unless_uniquely_solvable(grid)

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
        from sqlalchemy import desc

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
            width, height = filter_opts.size
            if not (MIN_SIZE <= width <= MAX_SIZE and MIN_SIZE <= height <= MAX_SIZE):
                raise ValueError(f"Size dimensions must be {MIN_SIZE}-{MAX_SIZE}")
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
                # Puzzle name filter (free-text search)
                if filter_opts.puzzle_name:
                    pname = puzzle.get("puzzle_name", "").lower()
                    if filter_opts.puzzle_name.lower() not in pname:
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

                # Date range filter
                if filter_opts.date_from:
                    df = datetime.strptime(filter_opts.date_from, "%Y-%m-%d")
                    query = query.filter(Puzzle.created_at >= df)
                if filter_opts.date_to:
                    dt = datetime.strptime(filter_opts.date_to, "%Y-%m-%d")
                    # Add 1 day to make it inclusive of the entire date_to day
                    query = query.filter(Puzzle.created_at < (dt.replace(hour=0, minute=0, second=0) + __import__('datetime').timedelta(days=1)))

                # Free-text puzzle name search
                if filter_opts.puzzle_name:
                    query = query.filter(Puzzle.puzzle_name.ilike(f"%{filter_opts.puzzle_name}%"))

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

            grid, clues_rows, clues_cols, score, tier = self._draw_until_unique(
                width, height
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
                'strategies_used': ['LineLogic', 'ConstraintProp'],
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
            )

        raise NotUniquelySolvable(
            f"no uniquely solvable {width}x{height} grid in {self.MAX_DRAWS} draws "
            f"at density {self.DENSITY}; returning an unchecked grid is what "
            "CARD-080 exists to prevent"
        )
