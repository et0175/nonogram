"""COMP-005 line logic — the bitmask half of the solver (ADR-0009, ADR-0012).

This module owns two things and nothing else:

``line_intersection``
    The line solver. Given one line's clue, its length and what is already
    known about it, it returns the cells that are filled in *every* placement
    of that clue and the cells that are empty in every placement — i.e. the
    intersection of all consistent placements, which is exactly the deduction
    a human makes when they overlap a line's leftmost and rightmost fits.
``propagate``
    Applies ``line_intersection`` to every dirty row and column, feeding each
    newly decided cell back to the perpendicular line, until nothing changes
    (the fixed point ADR-0009 describes).
``check_deadline``
    ADR-0011's cooperative deadline check, in one place so the solver's two
    checkpoints (here and at ``search``'s branch node) raise the same error
    with the same wording.
``LineCache``
    A memo of ``line_intersection``'s answers for one solve (CARD-018). The
    probing search in ``search`` asks the same line the same question over and
    over — sibling probes at one node differ in two lines and agree on the
    other ninety-eight — so the memo is what makes probing affordable rather
    than a constant-factor tax.

Representation (ADR-0012)
-------------------------
Every line is a pair of ints: ``filled`` and ``empty``, bit ``i`` set meaning
"cell ``i`` of this line is known filled / known empty". A cell whose bit is
set in neither is unknown; a cell set in both is a contradiction that this
module never constructs. Both orientations are kept in parallel — row masks
indexed by row with column bits, column masks indexed by column with row bits
— which is the "maintaining row and column masks in parallel" option ADR-0012
names, chosen over transposing the board on every pass because a propagation
step only ever touches the handful of cells it just decided.

Why the line logic is native and not built on ``nonogram.clues``
----------------------------------------------------------------
Both worktree notes on CARD-004 say it: ``clues.encode_line`` and
``clues.clue_matches_line`` are scoped to *complete* lines. They read any
falsy cell as empty, so a partially-known line — the only kind that exists
during propagation — is silently misread rather than rejected, and they
allocate a tuple per call in a loop that runs millions of times per generation
run. The three-valued reasoning below is therefore written natively against
the bitmasks, and so is the finished-line encoder ``mask_runs`` that ``search``
uses to re-check a completed grid — ADR-0007 forbids importing another
capability's module laterally in any case, so the solver consumes the clue
*contract* (ADR-0012's boundary tuples) without importing the clue *module*.
The EC-001 property test supplies the independent cross-check, from outside.

Purity (ADR-0007, guardrail G-2)
--------------------------------
No I/O, no randomness, no module-level mutable state. Every function here is a
total function of its arguments; ``propagate`` mutates only the ``Board`` it is
handed. The one clock reading is ADR-0011's cooperative deadline, and it is
opt-in: with ``deadline=None`` — the default, and what every existing caller
and the EC-001 property corpus pass — no clock is consulted at all and the
functions here stay pure in the strict sense.

:class:`LineCache` is mutable, but it is *handed in* by the caller rather than
kept here, so it is one solve's scratch space and not module state: two calls
to ``solve`` share nothing, which is what
``test_solving_the_same_clues_twice_gives_the_same_answer`` pins. It is also
semantically invisible — it only ever returns what :func:`line_intersection`
would have returned for the same arguments, so a run with a memo and a run
without reach the same verdict by the same route.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from nonogram.errors import SolverTimeout

__all__ = [
    "Board",
    "LINE_CACHE_LIMIT",
    "LineCache",
    "canonical_clue",
    "check_deadline",
    "line_intersection",
    "mask_runs",
    "propagate",
]

LineClue = tuple[int, ...]

#: What one line deduction is: the two agreed masks and the placement count,
#: or ``None`` for "this line admits no placement at all".
LineDeduction = tuple[int, int, int] | None

#: Distinguishes "not memoised yet" from a memoised ``None`` (a line that
#: admits no placement) — the latter is a perfectly ordinary cached answer and
#: the single most valuable one to keep, since it is what prunes a branch.
_MISSING: object = object()

#: How many line deductions one solve's memo may hold before it is emptied and
#: refilled. A hard 20x20 solve misses on roughly 25,000 distinct line states,
#: so this leaves comfortable headroom there while bounding the memo's memory
#: at a few tens of megabytes on a 30x30 run that would otherwise accumulate
#: entries for its whole 30-second budget (ADR-0001). Clearing wholesale rather
#: than evicting one entry at a time keeps the hot path a plain dict lookup
#: with no bookkeeping: the memo is an optimisation, and a rebuilt memo costs
#: recomputation, never correctness.
LINE_CACHE_LIMIT = 60_000


def check_deadline(deadline: float | None) -> None:
    """Raise :class:`~nonogram.errors.SolverTimeout` once ``deadline`` has passed.

    ADR-0011's whole enforcement mechanism, in three lines. The solver is
    stopped *cooperatively* — no thread, no subprocess, no signal — by calling
    this at the two checkpoints ADR-0011 names: the top of :func:`propagate`'s
    fixed-point sweep and the top of ``search``'s branch loop.

    Args:
        deadline: An absolute :func:`time.monotonic` reading, or ``None`` to
            disable the check entirely. ``None`` is the default everywhere, so
            a caller that does not care about timeouts (the EC-001 property
            corpus, the directed solver tests) pays a single ``is not None``
            per sweep and never reads the clock.

    Raises:
        SolverTimeout: the deadline is in the past. The message reports the
            overshoot, because "how far past the deadline did the check fire"
            is exactly the granularity question ADR-0011 lists as this
            mechanism's one negative consequence.

    ``time.monotonic`` and not ``time.perf_counter``: the deadline is compared
    against a value the *orchestrator* computed in a different module, so the
    two readings have to come from the same clock, and ADR-0011 names the
    monotonic one. (``SolveSignals.elapsed_seconds`` keeps ``perf_counter``:
    that is a duration measured entirely inside one call, never compared
    against anything from outside it.)
    """
    if deadline is not None:
        overshoot = time.monotonic() - deadline
        if overshoot > 0.0:
            raise SolverTimeout(
                f"solver passed its generation deadline {overshoot:.3f}s ago and "
                f"stopped without a verdict (ADR-0011 cooperative deadline); the "
                f"puzzle is abandoned, not accepted"
            )


def canonical_clue(clue: tuple[int, ...]) -> LineClue:
    """Normalise a clue to its run list: the empty-line marker becomes ``()``.

    ``clues.encode_line`` emits ``(0,)`` for a line with no filled cells
    (AC-013). The placement DP wants "a list of runs", and an empty line has
    zero runs, so the marker is stripped here — once, at the boundary — rather
    than special-cased inside the hot loop. A bare ``()`` is accepted as the
    same thing so a caller that dropped the marker is not silently misread as
    something else.

    Raises:
        ValueError: a run is not a positive integer. That is a malformed clue,
            i.e. a programming error at the call site, not a puzzle that
            happens to be unsolvable — reporting it as "0 solutions" would
            hide the bug behind a plausible-looking domain answer.
    """
    if clue == (0,) or clue == ():
        return ()
    for run in clue:
        if not isinstance(run, int) or isinstance(run, bool) or run <= 0:
            raise ValueError(
                f"malformed clue {clue!r}: runs must be positive ints, or the "
                f"single empty-line marker (0,)"
            )
    return tuple(clue)


def line_intersection(
    runs: LineClue,
    length: int,
    known_filled: int,
    known_empty: int,
) -> tuple[int, int, int] | None:
    """Deduce the cells every valid placement of ``runs`` agrees on.

    Args:
        runs: The line's clue in canonical form (see :func:`canonical_clue`) —
            positive run lengths, ``()`` for an empty line.
        length: Number of cells in the line.
        known_filled: Bitmask of cells already known to be filled.
        known_empty: Bitmask of cells already known to be empty.

    Returns:
        ``(filled, empty, placements)`` — the cells filled in *every*
        consistent placement, the cells empty in every consistent placement,
        and how many consistent placements there are. The two masks are
        supersets of the corresponding input mask, since a known cell is
        trivially agreed on by every placement consistent with it. ``None``
        when no placement of ``runs`` is consistent with what is known, which
        is a contradiction the caller must treat as "this branch has no
        solution".

    ``placements`` is the line's remaining freedom, and it is counted here
    because the same DP walk already visits every placement: it costs one
    addition per state and gives the search a far sharper "most constrained"
    measure than counting unknown cells does (a line with twenty unknown cells
    and two possible placements is nearly settled; one with four unknown cells
    and six placements is not).

    The algorithm is a DP over ``(position, run index)`` states. From each
    state a placement either leaves the current cell empty and moves on, or
    starts run ``index`` exactly here; every placement corresponds to exactly
    one path through those states, so OR-ing each transition's cell masks
    accumulates the union over all placements without ever enumerating them
    one by one (there can be astronomically many). A cell filled in every
    placement is then one that appears in the filled union and never in the
    empty union, and vice versa.

    The state space is ``length x (len(runs) + 1)`` — at most 50 x 26 for the
    largest supported grid — with O(1) work per state. It is evaluated bottom
    up, from the end of the line backwards, rather than as a memoised
    recursion: every transition reads a state strictly further along the line,
    so a plain reverse loop has them all in hand. That matters because this
    function is *the* hot path (ADR-0012's "millions of intersections per
    generation run"), and at these sizes CPython's per-call overhead for the
    recursive form costs several times the arithmetic it wraps.
    """
    if length < 0:
        raise ValueError(f"line length must be non-negative, got {length}")
    # Cheap impossibility check: the runs plus one mandatory gap between each
    # adjacent pair cannot be squeezed into the line.
    if sum(runs) + len(runs) - 1 > length:
        return None

    full = (1 << length) - 1
    if not runs:
        # An empty line: one placement, every cell empty — but only if nothing
        # is already known to be filled.
        return None if known_filled else (0, full, 1)
    if known_filled | known_empty == full:
        # The line is already fully decided, which happens constantly near the
        # leaves of the search. Checking the finished line against its clue
        # directly is a single pass, where the DP would be O(length x runs).
        return (known_filled, known_empty, 1) if mask_runs(known_filled, length) == runs else None

    run_count = len(runs)
    states = run_count + 1
    size = (length + 1) * states
    # Flat arrays indexed by ``pos * states + idx``: the union of filled cells,
    # the union of empty cells, and the number of placements, for the tail of
    # the line from ``pos`` on with runs ``idx..`` still to place. A count of
    # zero means that state admits no placement at all.
    union_filled = [0] * size
    union_empty = [0] * size
    counts = [0] * size

    # Base row (``pos == length``): the line is over, which is a valid
    # placement only if every run has been placed.
    counts[length * states + run_count] = 1

    # ``need[idx]`` cells are required to lay out runs ``idx..`` with their
    # mandatory gaps. A state with fewer cells left than that admits no
    # placement, so it is skipped entirely and keeps its zero count — which
    # cuts the state space roughly in half on a long line with many runs.
    need = [0] * states
    for idx in range(run_count - 1, -1, -1):
        need[idx] = need[idx + 1] + runs[idx] + (1 if idx + 1 < run_count else 0)

    lowest_idx = run_count
    for pos in range(length - 1, -1, -1):
        offset = pos * states
        next_offset = offset + states
        pos_is_filled = (known_filled >> pos) & 1
        pos_bit = 1 << pos
        remaining = length - pos
        while lowest_idx and need[lowest_idx - 1] <= remaining:
            lowest_idx -= 1
        for idx in range(run_count, lowest_idx - 1, -1):
            filled = 0
            empty = 0
            count = 0

            # Transition 1: leave cell ``pos`` empty and carry on.
            if not pos_is_filled:
                rest = next_offset + idx
                rest_count = counts[rest]
                if rest_count:
                    count = rest_count
                    filled = union_filled[rest]
                    empty = union_empty[rest] | pos_bit

            # Transition 2: start run ``idx`` at cell ``pos``.
            if idx < run_count:
                end = pos + runs[idx]
                if end <= length:
                    run_mask = ((1 << runs[idx]) - 1) << pos
                    if not known_empty & run_mask:
                        if end == length:
                            # The run ends the line: no separating gap needed,
                            # but no run may be left unplaced.
                            if idx + 1 == run_count:
                                count += 1
                                filled |= run_mask
                        elif not (known_filled >> end) & 1:
                            # One mandatory empty cell separates this run from
                            # the next; the line resumes after it.
                            rest = (end + 1) * states + idx + 1
                            rest_count = counts[rest]
                            if rest_count:
                                count += rest_count
                                filled |= union_filled[rest] | run_mask
                                empty |= union_empty[rest] | (1 << end)

            union_filled[offset + idx] = filled
            union_empty[offset + idx] = empty
            counts[offset + idx] = count

    placements = counts[0]
    if not placements:
        return None
    # Every placement assigns every cell, so a cell in exactly one union is
    # one all placements agree on; a cell in both unions stays unknown.
    return (union_filled[0] & ~union_empty[0], union_empty[0] & ~union_filled[0], placements)


def mask_runs(filled: int, length: int) -> LineClue:
    """Run-length encode a fully decided line straight from its filled mask.

    The bitmask twin of ``clues.encode_line``, for the one case where the line
    is complete and the DP would be wasted work. It is also what verifies
    finished grids: ``search._verified_grid`` re-encodes every completed line
    with *this* function, natively, and never calls ``clues.compute_clues`` —
    ADR-0007 forbids ``solver/`` importing the ``clues`` capability module
    laterally, and ``tests/test_cli.py`` enforces that. Independence is bought
    back from the test tree instead, where the import is legal: ``mask_runs``
    is pinned against ``clues.encode_line`` there.
    """
    runs: list[int] = []
    run = 0
    for pos in range(length):
        if (filled >> pos) & 1:
            run += 1
        elif run:
            runs.append(run)
            run = 0
    if run:
        runs.append(run)
    return tuple(runs)


@dataclass(slots=True)
class LineCache:
    """One solve's memo of :func:`line_intersection`, kept per line (CARD-018).

    The probing search asks the same line the same question relentlessly. Two
    sibling probes at one node assign different values to *one* cell, so the
    ninety-eight lines they do not touch are re-examined in identical states;
    and two nodes in different subtrees routinely arrive at the same state for
    a given line by different routes. Measured on the 20x20 mid-density grids
    CARD-018 exists for, 84-89% of all line deductions in a solve are repeats,
    and memoising them cuts a solve's wall clock by about a factor of five —
    which is what turns probing from a constant-factor tax into a net win.

    Why per line and not one flat dict
    ----------------------------------
    Keyed by ``(runs, length, known_filled, known_empty)`` a single dict would
    hash the clue tuple on every lookup, on the hot path, to buy sharing
    between two lines that happen to have the same clue *and* the same state —
    rare, and worth less than it costs. One dict per line lets the key collapse
    to a single int (see :meth:`deduce`), which hashes in constant time.

    Why it is not module state
    --------------------------
    It is created by :func:`~nonogram.solver.search.solve` and dies with the
    call, so two solves share nothing and the solver stays the pure function
    ADR-0007 and the EC-001 corpus rely on. Passing ``cache=None`` (the
    default) disables it entirely, which is what keeps every pre-CARD-018
    caller — and every test that calls :func:`propagate` directly — unchanged.
    """

    #: One memo per row, indexed by row, and one per column. Each maps a
    #: packed ``(known_filled, known_empty)`` state to that line's deduction.
    rows: list[dict[int, LineDeduction]]
    columns: list[dict[int, LineDeduction]]
    #: How many entries all the memos hold between them, so the limit can be
    #: enforced without walking them.
    entries: int
    limit: int

    @classmethod
    def blank(cls, height: int, width: int, limit: int = LINE_CACHE_LIMIT) -> LineCache:
        """An empty memo sized for a ``height`` x ``width`` board."""
        return cls(
            rows=[{} for _ in range(height)],
            columns=[{} for _ in range(width)],
            entries=0,
            limit=limit,
        )

    def deduce(
        self,
        memo: dict[int, LineDeduction],
        runs: LineClue,
        length: int,
        known_filled: int,
        known_empty: int,
    ) -> LineDeduction:
        """:func:`line_intersection`, answered from ``memo`` when it can be.

        Args:
            memo: This line's memo — ``self.rows[r]`` or ``self.columns[c]``.
                Passed in rather than looked up here so the caller, which
                already knows which line it is working on, does not pay an
                index dispatch per lookup. **One memo belongs to one line**:
                see the key note below.
            runs, length, known_filled, known_empty: Exactly
                :func:`line_intersection`'s arguments, and the answer is
                exactly its answer.

        The key packs the two masks into one int: shifting ``known_empty`` up
        by ``length`` makes the pair injective without allocating a tuple. That
        is why a memo may only ever be used for *one* line — the key does not
        carry ``runs`` or ``length``, so feeding two different lines through
        one memo would let their states collide. Every caller here holds a
        memo indexed by the very line it is deducing, which makes that
        structural rather than a rule to remember.
        """
        key = (known_empty << length) | known_filled
        deduced = memo.get(key, _MISSING)
        if deduced is _MISSING:
            deduced = line_intersection(runs, length, known_filled, known_empty)
            if self.entries >= self.limit:
                self.clear()
            memo[key] = deduced
            self.entries += 1
        return deduced  # type: ignore[return-value]

    def clear(self) -> None:
        """Drop everything memoised so far, keeping the memo bounded."""
        for memo in self.rows:
            memo.clear()
        for memo in self.columns:
            memo.clear()
        self.entries = 0


@dataclass(slots=True)
class Board:
    """The solver's three-valued knowledge of one grid, as ADR-0012 bitmasks.

    Row masks are indexed by row and carry column bits; column masks are
    indexed by column and carry row bits. The two are redundant by
    construction and :func:`propagate` is the only thing that writes them, so
    they cannot drift apart.

    ``decided`` is the running count of cells known to be filled or empty. It
    is maintained incrementally because "how many cells did line logic alone
    settle" is one of the FR-009 difficulty signals this card has to emit, and
    recounting it by popcount on every pass would be pure waste.

    ``row_placements`` / ``column_placements`` cache how many placements each
    line still admits, as last computed by :func:`propagate`. A line is
    re-examined whenever anything writes into it, so at a fixed point these
    are current, and the branching heuristic reads them instead of recomputing
    a line DP per candidate cell.
    """

    height: int
    width: int
    row_clues: tuple[LineClue, ...]
    column_clues: tuple[LineClue, ...]
    row_filled: list[int]
    row_empty: list[int]
    column_filled: list[int]
    column_empty: list[int]
    row_placements: list[int]
    column_placements: list[int]
    decided: int

    @classmethod
    def blank(
        cls,
        row_clues: tuple[LineClue, ...],
        column_clues: tuple[LineClue, ...],
    ) -> Board:
        """A board where every cell is unknown, sized from the two clue sets."""
        height = len(row_clues)
        width = len(column_clues)
        return cls(
            height=height,
            width=width,
            row_clues=row_clues,
            column_clues=column_clues,
            row_filled=[0] * height,
            row_empty=[0] * height,
            column_filled=[0] * width,
            column_empty=[0] * width,
            # Filled in by the first propagation sweep, which examines every
            # line; until then the count is unknown, not zero.
            row_placements=[-1] * height,
            column_placements=[-1] * width,
            decided=0,
        )

    def clone(self) -> Board:
        """A copy that can be mutated without touching this one.

        Backtracking's undo step, and the reason ADR-0012 calls it "essentially
        free": the masks are immutable ints, so four shallow list copies of at
        most 50 elements each are the entire cost of saving a search node.
        """
        return Board(
            height=self.height,
            width=self.width,
            row_clues=self.row_clues,
            column_clues=self.column_clues,
            row_filled=self.row_filled.copy(),
            row_empty=self.row_empty.copy(),
            column_filled=self.column_filled.copy(),
            column_empty=self.column_empty.copy(),
            row_placements=self.row_placements.copy(),
            column_placements=self.column_placements.copy(),
            decided=self.decided,
        )

    def cell_is_known(self, row: int, column: int) -> bool:
        """Is the cell at ``(row, column)`` already decided either way?"""
        return bool((self.row_filled[row] | self.row_empty[row]) >> column & 1)

    def assign(self, row: int, column: int, filled: bool) -> None:
        """Record one cell's value in both orientations (the branch step).

        The caller is responsible for marking ``row`` and ``column`` dirty; a
        cell that is already known is a programming error, not a no-op, since
        every caller here picks an explicitly unknown cell.
        """
        if self.cell_is_known(row, column):
            raise ValueError(f"cell ({row}, {column}) is already decided")
        if filled:
            self.row_filled[row] |= 1 << column
            self.column_filled[column] |= 1 << row
        else:
            self.row_empty[row] |= 1 << column
            self.column_empty[column] |= 1 << row
        self.decided += 1


def propagate(
    board: Board,
    dirty_rows: list[bool],
    dirty_columns: list[bool],
    deadline: float | None = None,
    cache: LineCache | None = None,
) -> bool:
    """Run line logic over the dirty lines until nothing more can be deduced.

    Args:
        board: Mutated in place with everything the line logic settles.
        dirty_rows: ``dirty_rows[r]`` — row ``r`` needs (re)examining. Consumed:
            every flag is cleared by the time this returns.
        dirty_columns: The same for columns.
        deadline: ADR-0011's cooperative deadline — an absolute
            :func:`time.monotonic` reading, or ``None`` (the default) for no
            deadline at all.
        cache: One solve's :class:`LineCache`, or ``None`` (the default) to
            call :func:`line_intersection` directly every time. Purely a speed
            choice: the memo returns what the function would have returned, so
            the deductions, the fixed point and the verdict are identical
            either way (CARD-018).

    Returns:
        ``True`` if the board is still consistent (a fixed point was reached),
        ``False`` the moment some line admits no placement at all — i.e. this
        branch of the search is contradictory and can be abandoned.

    Raises:
        SolverTimeout: ``deadline`` passed. Checked once per sweep of the outer
            loop, which is ADR-0011's "each propagation fixed point": the check
            fires before the first sweep and again before every re-sweep, so a
            propagation that keeps finding more to deduce cannot outrun the
            deadline by more than one sweep's work.

    A line is re-examined whenever a perpendicular line writes into it, so at
    the fixed point *every* line is known to admit at least one placement
    given the board's final state. That is what lets ``search`` treat a fully
    decided board as a solution: with no unknown cells left, "admits at least
    one placement" and "matches its clue" are the same statement.

    Why the check sits on the outer loop and not deeper (CARD-006)
    --------------------------------------------------------------
    One sweep is at most ``height + width`` line DPs — 60 of them at the
    30x30 upper bound, each O(length x runs) — so the overshoot this
    granularity admits is bounded by a few tens of milliseconds against a
    30-second budget (ADR-0001), which is the "small overshoot" ADR-0011 trades
    for portability. Pushing the check one level down, into the per-line loops,
    would multiply the clock reads by ~100 for an overshoot improvement of the
    same few tens of milliseconds — invisible against the budget, but a real
    cost on the 10x10..30x30 line-solvable grids that dominate NFR-001's p95
    and reach their fixed point in a handful of sweeps.
    """
    height = board.height
    width = board.width
    row_clues = board.row_clues
    column_clues = board.column_clues
    # Bound once rather than tested per line: ``deduce is None`` is the whole
    # "no memo" branch, and with a memo the bound method skips an attribute
    # lookup on a path that runs hundreds of thousands of times per solve.
    deduce = cache.deduce if cache is not None else None
    row_memos = cache.rows if cache is not None else ()
    column_memos = cache.columns if cache is not None else ()

    pending = True
    while pending:
        check_deadline(deadline)
        pending = False

        for row in range(height):
            if not dirty_rows[row]:
                continue
            dirty_rows[row] = False
            if deduce is None:
                deduced = line_intersection(
                    row_clues[row], width, board.row_filled[row], board.row_empty[row]
                )
            else:
                deduced = deduce(
                    row_memos[row],
                    row_clues[row],
                    width,
                    board.row_filled[row],
                    board.row_empty[row],
                )
            if deduced is None:
                return False
            filled, empty, placements = deduced
            board.row_placements[row] = placements
            new_filled = filled & ~board.row_filled[row]
            new_empty = empty & ~board.row_empty[row]
            if not (new_filled or new_empty):
                continue
            board.row_filled[row] = filled
            board.row_empty[row] = empty
            board.decided += new_filled.bit_count() + new_empty.bit_count()
            row_bit = 1 << row
            bits = new_filled
            while bits:
                column = (bits & -bits).bit_length() - 1
                bits &= bits - 1
                board.column_filled[column] |= row_bit
                dirty_columns[column] = True
                pending = True
            bits = new_empty
            while bits:
                column = (bits & -bits).bit_length() - 1
                bits &= bits - 1
                board.column_empty[column] |= row_bit
                dirty_columns[column] = True
                pending = True

        for column in range(width):
            if not dirty_columns[column]:
                continue
            dirty_columns[column] = False
            if deduce is None:
                deduced = line_intersection(
                    column_clues[column],
                    height,
                    board.column_filled[column],
                    board.column_empty[column],
                )
            else:
                deduced = deduce(
                    column_memos[column],
                    column_clues[column],
                    height,
                    board.column_filled[column],
                    board.column_empty[column],
                )
            if deduced is None:
                return False
            filled, empty, placements = deduced
            board.column_placements[column] = placements
            new_filled = filled & ~board.column_filled[column]
            new_empty = empty & ~board.column_empty[column]
            if not (new_filled or new_empty):
                continue
            board.column_filled[column] = filled
            board.column_empty[column] = empty
            board.decided += new_filled.bit_count() + new_empty.bit_count()
            column_bit = 1 << column
            bits = new_filled
            while bits:
                row = (bits & -bits).bit_length() - 1
                bits &= bits - 1
                board.row_filled[row] |= column_bit
                dirty_rows[row] = True
                pending = True
            bits = new_empty
            while bits:
                row = (bits & -bits).bit_length() - 1
                bits &= bits - 1
                board.row_empty[row] |= column_bit
                dirty_rows[row] = True
                pending = True

    return True
