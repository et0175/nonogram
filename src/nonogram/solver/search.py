"""COMP-005 search — counting solutions with fail-fast (ADR-0009, FR-006).

The public entry point is :func:`solve`. It takes clues in CARD-002's boundary
type and answers the one question CAP-003 exists to answer: does this clue set
have no solution, exactly one, or more than one?

Shape of the search (ADR-0009, CARD-018)
----------------------------------------
1. Run :func:`~nonogram.solver.propagate.propagate` over every line to a fixed
   point. Cells settled here are settled by line logic alone — the count at
   this first fixed point is FR-009's "cells solved before the first branch".
2. If the board is fully decided, that is the only solution reachable without
   guessing, and the search is over.
3. Otherwise *probe*: take the most constrained unknown cells, and for each one
   tentatively assign both values and propagate. A value whose propagation
   contradicts cannot appear in any solution, so the other value is forced and
   is applied for real; if both contradict, the whole node is refuted. Only
   when a probing pass forces nothing does the search actually branch, on the
   cell whose two probes propagated furthest, keeping the two boards the probes
   already produced as its children.
4. Stop the instant a *second* distinct solution is recorded (AC-017).
5. If a pass over the tree exceeds its node limit without settling the verdict,
   restart it with a wider probe and a larger limit (see
   :data:`_SEARCH_ROUNDS`). The limits grow without bound, so the search is
   still complete; what changes is that a hard instance is not held hostage to
   one heuristic's first guess.

The search is iterative rather than recursive. Depth is bounded by the number
of guesses, which at the 50x50 upper bound (ADR-0001) can exceed CPython's
default recursion limit on a pathological puzzle; an explicit stack makes the
worst case a memory question instead of a ``RecursionError``.

Why probing is sound (CARD-018 guardrail G-3)
---------------------------------------------
The one thing this must never do is discard a branch that still contains a
solution, and the argument is short because it rests entirely on what
:func:`~nonogram.solver.propagate.propagate` already promised.

Propagation only ever writes cells that *every* placement of some line agrees
on, given what is already known. So for any board ``B``, every solution that
extends ``B`` also extends the board propagation leaves behind, and propagation
returns ``False`` only when some line admits no placement at all — which means
no solution extends ``B``. Now probe cell ``c`` with value ``v``:

* If the probe contradicts, no solution extends ``B + (c = v)``. Since ``c`` is
  either filled or empty in every solution, every solution extending ``B``
  extends ``B + (c = ¬v)``. Forcing ``¬v`` therefore discards nothing, and
  keeping the probe's own propagated board discards nothing either — its extra
  cells are forced deductions from a board every remaining solution extends.
* If *both* probes contradict, no solution extends ``B`` at all, so refuting
  the node discards nothing.
* If neither contradicts, nothing is deduced and nothing is discarded: the two
  probe boards become the node's two children, and their union covers every
  solution extending ``B`` because they disagree only on ``c``.

Every deduction the probing pass makes is of one of those three shapes, so no
solution is ever lost — and none is ever gained either, which is the other half
of CON-005. Branch ordering and the restart schedule move work around; neither
can add or remove a solution, because both children of a branch are always
explored and a cut-off pass is discarded whole rather than half-believed.

Why counting stops at two (FR-006)
----------------------------------
``solution_count`` is ``0``, ``1`` or :data:`MANY` (``2``, read as ">= 2").
CARD-005 calls this on every candidate grid it generates, and the only thing
it ever asks is "is it exactly 1?" — enumerating the 40,000 solutions of a
sloppy clue set to answer "not 1" would make the uniqueness check the most
expensive part of generation for the least useful information.

Self-check before counting (CON-005)
------------------------------------
CON-005 is the model's one mandatory constraint and ADR-0009 is explicit that
a hand-rolled search is where a false-positive uniqueness verdict would hide.
So every completed board is re-encoded from its finished masks and compared
against the clues it was solved from before it is allowed to count as a
solution. A mismatch is a solver bug, not a puzzle outcome, so it raises
rather than being quietly discarded: a wrong answer that crashes is
recoverable, a wrong answer that looks right is what CON-005 forbids.

That re-encoding is done natively (``propagate.mask_runs``) rather than
through ``clues.encode_line``, even though the grid is complete by then and
CARD-002's function would be safe on it. ADR-0007 forbids lateral imports
between capability modules, and ``clues`` is COMP-004's capability, not a
shared kernel — ``tests/test_cli.py`` enforces that on every module in the
package. The solver consumes the clue *contract* (the boundary tuples of
ADR-0012) without importing the clue *module*. Independence from the solver's
own code is what the EC-001 property test provides, and it does cross-check
against ``clues.compute_clues`` from outside.

The cooperative deadline (ADR-0011, CARD-006)
---------------------------------------------
:func:`solve` takes an optional absolute ``deadline`` and threads it into the
two checkpoints ADR-0011 names: every propagation fixed point (inside
:func:`~nonogram.solver.propagate.propagate`) and every branch node (the top of
the search loop below). Once it passes, the solver raises
:class:`~nonogram.errors.SolverTimeout` instead of returning a verdict — a
timed-out solve has *no* answer, which is what keeps CON-005 true: the search
is stopped between whole steps, never mid-deduction, so it can never abandon
with a half-formed uniqueness verdict. The deadline itself is the
orchestrator's (COMP-002) to compute, once per generation request; the solver
only reads the clock against it.

Out of scope here (guardrail G-5): no difficulty scoring (CARD-009 consumes
:class:`SolveSignals`), no retry loop (CARD-005).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from nonogram.solver.propagate import (
    Board,
    LineCache,
    LineClue,
    canonical_clue,
    check_deadline,
    mask_runs,
    propagate,
)

__all__ = ["MANY", "SolveResult", "SolveSignals", "solve"]

Grid = list[list[bool]]
ClueSet = tuple[tuple[int, ...], ...]

#: The reported ``solution_count`` for a clue set with more than one solution.
#: The search stops here by design (AC-017), so the value means ">= 2" and
#: never "exactly 2".
MANY = 2

#: The restart schedule (CARD-018): ``(probe_width, node_limit)`` per round.
#:
#: ``probe_width`` is how many of the most constrained unknown cells a probing
#: pass examines, and ``node_limit`` how many search nodes the round may visit
#: before it is abandoned and the next one started.
#:
#: Round 0 is deliberately cheap and deliberately *undiversified*: it probes a
#: narrow front and takes the heuristic's own best branch, which is what keeps
#: the overwhelming majority of clue sets — everything line logic nearly
#: settles, every puzzle in the EC-001 corpus — on the same short path they
#: were on before this schedule existed. The later rounds exist for the
#: minority that round 0 cannot finish, and they widen on both axes at once,
#: because measurement showed the two failures are different: some instances
#: are hard because one early guess was wrong (a re-run that branches
#: elsewhere finds a solution in milliseconds) and others because the inference
#: is too weak to prune (a wider probe cuts them from tens of seconds to one).
#:
#: Past the last entry the probe width stays put and the node limit keeps
#: multiplying by :data:`_NODE_LIMIT_GROWTH`, so the limit is unbounded in the
#: limit and a search that needs the whole tree eventually gets it. That is
#: what keeps restarting *complete*: a verdict is only ever taken from a round
#: that finished on its own terms, never from one that ran out of nodes.
_SEARCH_ROUNDS: tuple[tuple[int, int], ...] = ((8, 400), (16, 1200), (32, 3600), (64, 10800))

#: How much the node limit grows per round once :data:`_SEARCH_ROUNDS` is
#: exhausted. Geometric growth bounds the total cost of the abandoned rounds at
#: a constant multiple of the one that finally succeeds.
_NODE_LIMIT_GROWTH = 3

#: Returned by :func:`_search` when a round hit its node limit. Distinct from
#: an empty solution list, which is the real verdict "no solutions exist".
_CUT_OFF: object = object()

_MASK64 = (1 << 64) - 1


@dataclass(frozen=True, slots=True)
class SolveSignals:
    """The raw solver telemetry FR-009 scores and NFR-001 is measured by.

    Emitted now, scored never — guardrail G-5 puts the formula in CARD-009
    (ADR-0013). Recording them here is what stops that card having to reopen
    the search's control flow to instrument it.
    """

    #: Cells decided by line logic alone, before the first guess (ADR-0013
    #: normalises this against ``total_cells``). Equal to ``total_cells`` when
    #: the puzzle never needed a guess.
    line_logic_cells: int
    #: Cells in the grid — ADR-0013's size-relative denominator.
    total_cells: int
    #: How many times the search had to guess a cell because propagation
    #: stalled. ADR-0013's "backtracking amount" term.
    branch_nodes: int
    #: How many guesses ran straight into a contradiction. Distinct from
    #: ``branch_nodes``: a puzzle can branch a lot and never backtrack.
    backtracks: int
    #: Wall-clock seconds for the whole solve, from a monotonic clock.
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class SolveResult:
    """What :func:`solve` answers: a count, a witness, and the signals."""

    #: ``0``, ``1``, or :data:`MANY` (``2``, meaning ">= 2").
    solution_count: int
    #: The solution grid in the ADR-0012 boundary type when
    #: ``solution_count == 1``; ``None`` when there is no solution. When there
    #: is more than one, this is the first solution found — a witness, not
    #: "the" solution, and callers gated on uniqueness must not use it.
    solution: Grid | None
    signals: SolveSignals

    @property
    def is_unique(self) -> bool:
        """Exactly one solution — the INV-002 gate CARD-005's loop retries on."""
        return self.solution_count == 1


def solve(
    row_clues: ClueSet,
    column_clues: ClueSet,
    *,
    deadline: float | None = None,
) -> SolveResult:
    """Count a clue set's solutions, stopping at two (FR-006).

    Args:
        row_clues: One clue tuple per row, top to bottom, in CARD-002's
            boundary type — ``(0,)`` for an empty line (AC-013).
        column_clues: One clue tuple per column, left to right.
        deadline: ADR-0011's cooperative deadline — an absolute
            :func:`time.monotonic` reading past which the search gives up, or
            ``None`` (the default) to run to completion however long it takes.
            Keyword-only, and defaulted, because it is not part of the question
            being asked: a caller that only wants the uniqueness verdict — the
            EC-001 property corpus, every directed solver test — is unchanged
            by its existence, which is ADR-0011's "every caller must now
            account for it" consequence paid down to nothing.

    Returns:
        A :class:`SolveResult` whose ``solution_count`` is ``0`` (AC-016),
        ``1`` (AC-015) or :data:`MANY` (AC-017), carrying the solution grid
        when the count is 1 and the FR-009 signals either way.

    Raises:
        ValueError: the clue set is malformed — a run that is not a positive
            int, or the empty-line marker used alongside other runs. Not a
            domain outcome: an unsolvable puzzle is reported as
            ``solution_count = 0``, never as an exception.
        SolverTimeout: ``deadline`` passed before the count was settled
            (ADR-0011). Deliberately an exception and not a fourth
            ``solution_count`` value: a timeout is not a verdict about the
            puzzle, and a caller that pattern-matched it as one would either
            discard a good candidate or, worse, retry a request that is out of
            time (INV-002, and the orchestrator's own retry contract).

    Pure (ADR-0007, guardrail G-2) for a given ``deadline``: no filesystem, no
    CLI, no randomness, no module state. With the default ``deadline=None`` no
    clock is read at all, which is why EC-001's property test needs no fixture
    and why the solver's answers do not depend on how fast the machine is.

    A ``nonogram.clues.Clues`` unpacks straight into the two arguments::

        result = solve(*compute_clues(grid))
    """
    started = time.perf_counter()

    rows = tuple(canonical_clue(clue) for clue in row_clues)
    columns = tuple(canonical_clue(clue) for clue in column_clues)
    height = len(rows)
    width = len(columns)
    total_cells = height * width

    def finish(
        count: int,
        solution: Grid | None,
        branches: int,
        backtracks: int,
        line_logic_cells: int,
    ) -> SolveResult:
        """Stamp the elapsed time on and return — every exit goes through here."""
        return SolveResult(
            solution_count=count,
            solution=solution,
            signals=SolveSignals(
                line_logic_cells=line_logic_cells,
                total_cells=total_cells,
                branch_nodes=branches,
                backtracks=backtracks,
                elapsed_seconds=time.perf_counter() - started,
            ),
        )

    # A solution's filled cells are counted once by the row clues and once by
    # the column clues, so unequal totals mean there is nothing to search for.
    # Only an early exit — the search below would reach the same verdict.
    if sum(sum(clue) for clue in rows) != sum(sum(clue) for clue in columns):
        return finish(0, None, 0, 0, 0)

    if total_cells == 0:
        # A grid with no cells: the empty grid is its only candidate, and it
        # is a solution exactly when every line's clue is the empty marker
        # (the sum check above has already established that). Handled here
        # because a zero-row grid has no cells to re-encode its column clues
        # from, so the verification below would misread it as a defect.
        return finish(1, [[] for _ in range(height)], 0, 0, 0)

    # One memo per solve, created here and dropped when this call returns, so
    # the solver keeps no state between calls (CARD-018; the memo only ever
    # returns what ``line_intersection`` would have).
    cache = LineCache.blank(height, width)

    board = Board.blank(rows, columns)
    dirty_rows = [True] * height
    dirty_columns = [True] * width
    if not propagate(board, dirty_rows, dirty_columns, deadline, cache):
        return finish(0, None, 0, 0, board.decided)

    # Everything settled up to here came from line logic alone (FR-009). It is
    # computed once, outside the restart loop below, because it does not depend
    # on how the search that follows chooses to branch.
    line_logic_cells = board.decided

    if board.decided == total_cells:
        return finish(1, _verified_grid(board), 0, 0, line_logic_cells)

    counters = _Counters()
    round_index = 0
    while True:
        probe_width, node_limit = _round(round_index)
        found = _search(board, cache, probe_width, node_limit, round_index, deadline, counters)
        if found is not _CUT_OFF:
            solutions = found  # type: ignore[assignment]
            break
        round_index += 1

    count = len(solutions)
    solution = solutions[0] if solutions else None
    return finish(
        count, solution, counters.branch_nodes, counters.backtracks, line_logic_cells
    )


@dataclass(slots=True)
class _Counters:
    """FR-009's two search signals, accumulated across every restart round.

    They are counted per solve rather than per round on purpose: what CARD-009
    scores is how much work the puzzle cost, and a puzzle that needed three
    rounds cost all three.
    """

    #: Search nodes expanded — every board the search took off its stack,
    #: whether it went on to branch there, settle it by forced values, or
    #: refute it. ``0`` exactly when line logic alone finished the puzzle.
    branch_nodes: int = 0
    #: Refuted assignments: every probe that ran into a contradiction, which is
    #: a subtree the search proved empty without descending into it.
    backtracks: int = 0


def _round(index: int) -> tuple[int, int]:
    """The ``(probe_width, node_limit)`` for restart round ``index``."""
    if index < len(_SEARCH_ROUNDS):
        return _SEARCH_ROUNDS[index]
    probe_width, node_limit = _SEARCH_ROUNDS[-1]
    return probe_width, node_limit * _NODE_LIMIT_GROWTH ** (index - len(_SEARCH_ROUNDS) + 1)


def _search(
    root: Board,
    cache: LineCache,
    probe_width: int,
    node_limit: int,
    round_index: int,
    deadline: float | None,
    counters: _Counters,
) -> list[Grid] | object:
    """One restart round: the whole tree, or :data:`_CUT_OFF` if it ran long.

    Args:
        root: The board at line logic's first fixed point. Cloned rather than
            mutated, so every round starts from the same place and the caller
            can run this as many times as it likes.
        cache: The solve's line memo. Deliberately *shared* across rounds —
            what a line deduces from a given state does not depend on which
            round asked, so a restart re-treads its predecessor's ground at
            memo speed rather than recomputing it.
        probe_width: How many candidate cells each probing pass examines.
        node_limit: Give up and return :data:`_CUT_OFF` after this many nodes.
        round_index: 0 for the first round, which follows the branch heuristic
            exactly; later rounds spread their branch choice across the
            candidates the probes found equally live (see :func:`_diversified`).
        counters: Mutated with this round's node and refutation counts.

    Returns:
        The solutions found — at most :data:`MANY`, and every one of them
        verified — or :data:`_CUT_OFF`. A cut-off round's partial findings are
        thrown away rather than carried forward: a round that did not finish
        has proved nothing about how many solutions exist, and mixing its
        solutions into the next round's would risk counting one twice.

    Appending without a duplicate check is safe: sibling branches are disjoint
    by construction. A branch fixes one cell that was unknown at its node and
    explores each of its two values in a separate subtree, so any two grids
    found under different siblings differ in at least that cell — no grid is
    reachable down two branches. Hence ``len(solutions) == MANY`` really does
    mean two *distinct* solutions, which is what FR-006 counts.
    """
    solutions: list[Grid] = []
    stack: list[Board] = [root.clone()]
    nodes = 0
    while stack and len(solutions) < MANY:
        # ADR-0011's second checkpoint. It sits at the top of the loop that
        # takes work off the stack, so it covers every node the search visits,
        # including the ones refuted by probing without a frame ever being
        # pushed — the expensive shape of a hard instance is a long run of
        # exactly those.
        check_deadline(deadline)
        if nodes >= node_limit:
            return _CUT_OFF
        board = stack.pop()
        nodes += 1
        counters.branch_nodes += 1
        outcome = _expand(board, cache, probe_width, round_index, nodes, deadline, counters)
        if outcome is None:
            continue
        settled, alternative = outcome
        if alternative is None:
            solutions.append(_verified_grid(settled))
            continue
        stack.append(alternative)
        stack.append(settled)
    return solutions


def _expand(
    board: Board,
    cache: LineCache,
    probe_width: int,
    round_index: int,
    node_index: int,
    deadline: float | None,
    counters: _Counters,
) -> tuple[Board, Board | None] | None:
    """Probe one node until it is settled, refuted, or ready to branch.

    Returns:
        ``None`` if the node is refuted — no solution extends this board.
        ``(board, None)`` if probing settled it completely; that board is a
        solution. ``(first, second)`` otherwise: the two boards to explore, in
        the order to explore them.

    The loop is the probing pass described in the module docstring. Each pass
    walks the most constrained unknown cells, tries both values of each, and
    acts on the outcome; a pass that forced at least one value starts over,
    because the board it is reasoning about has changed and the cells worth
    probing may have too. A pass that forces nothing has reached the limit of
    what this inference can see, and the node branches.

    The soundness of every step here is the argument in the module docstring:
    a contradicting probe rules its value out of *every* solution, so forcing
    the other one — and keeping the propagated board that came with it —
    discards nothing.
    """
    height = board.height
    width = board.width
    total_cells = height * width
    row_memos = cache.rows
    column_memos = cache.columns

    while True:
        check_deadline(deadline)
        if board.decided == total_cells:
            return board, None

        pool: list[tuple[Board, Board]] = []
        best: tuple[Board, Board] | None = None
        best_score = -1
        forced = False

        for row, column in _probe_candidates(board, probe_width):
            if board.cell_is_known(row, column):
                # An earlier forced value in this same pass settled it.
                continue
            filled_ok, filled_child = _probe(board, row, column, True, deadline, cache)
            empty_ok, empty_child = _probe(board, row, column, False, deadline, cache)

            if not filled_ok and not empty_ok:
                # Neither value survives, so nothing extends this board.
                counters.backtracks += 1
                return None
            if not filled_ok or not empty_ok:
                # Exactly one survives, so it is not a guess at all: it is a
                # deduction, and the probe already propagated its consequences.
                counters.backtracks += 1
                board = empty_child if not filled_ok else filled_child
                forced = True
                if board.decided == total_cells:
                    return board, None
                continue

            filled_gain = filled_child.decided - board.decided
            empty_gain = empty_child.decided - board.decided
            # Value order: the value more of the two lines' placements agree
            # with goes first. Both are always explored, so this only decides
            # which subtree is entered first — but on an under-constrained grid
            # it decides it well, because it is the exact fraction of this
            # line's surviving placements that fill the cell, and following it
            # is following the puzzle's own bias.
            column_bit = 1 << column
            row_bit = 1 << row
            filled_support = _support(
                cache, row_memos[row], board.row_clues[row], width,
                board.row_filled[row] | column_bit, board.row_empty[row],
            ) * _support(
                cache, column_memos[column], board.column_clues[column], height,
                board.column_filled[column] | row_bit, board.column_empty[column],
            )
            empty_support = _support(
                cache, row_memos[row], board.row_clues[row], width,
                board.row_filled[row], board.row_empty[row] | column_bit,
            ) * _support(
                cache, column_memos[column], board.column_clues[column], height,
                board.column_filled[column], board.column_empty[column] | row_bit,
            )
            pair = (
                (filled_child, empty_child)
                if filled_support >= empty_support
                else (empty_child, filled_child)
            )
            pool.append(pair)
            # Branch where *both* subtrees are already well constrained: the
            # weaker side is what a wrong guess has to be disproved through, so
            # the cell whose worse side propagates furthest is the cell whose
            # mistake costs least to find.
            score = min(filled_gain, empty_gain) * (total_cells + 1) + filled_gain + empty_gain
            if score > best_score:
                best_score = score
                best = pair

        if forced:
            continue
        if best is None:
            # A pass that neither forced a value nor found one to branch on,
            # on a board that still has unknown cells, would be the search
            # silently declaring a live node dead — the one shape of bug
            # CON-005 forbids. It is unreachable: the loop returns early when
            # the board is complete, so an incomplete board has an unknown
            # cell, and :func:`_probe_candidates` ranks *every* unknown cell
            # before taking its first ``probe_width``. Left as a loud failure
            # rather than a comment because the cheap way to break it — a
            # probe width of 0, which slices the candidate list to nothing —
            # would otherwise report "no solutions" for a solvable puzzle.
            raise RuntimeError(
                f"probing produced no branch for a board with "
                f"{total_cells - board.decided} unknown cells (probe width "
                f"{probe_width}); this is a solver defect (CON-005), not a "
                f"puzzle outcome"
            )
        if round_index == 0 or len(pool) == 1:
            return best
        return pool[_diversified(round_index, node_index, len(pool))]


def _probe(
    board: Board,
    row: int,
    column: int,
    value: bool,
    deadline: float | None,
    cache: LineCache,
) -> tuple[bool, Board]:
    """Assign ``(row, column) = value`` on a copy and propagate it.

    Returns ``(survived, child)``. ``survived`` is ``False`` when propagation
    found a line with no placement left, which is a proof that no solution
    assigns that cell that value. The child board is returned either way: when
    it survives it is a ready-made search child or, if its sibling did not, a
    ready-made forced deduction — the propagation is never done twice.

    Only the two lines through the cell are marked dirty, which is exactly the
    seam the assignment opened; everything else is at a fixed point already and
    :func:`~nonogram.solver.propagate.propagate` will re-dirty whatever the
    cascade touches.
    """
    child = board.clone()
    child.assign(row, column, value)
    dirty_rows = [False] * board.height
    dirty_columns = [False] * board.width
    dirty_rows[row] = True
    dirty_columns[column] = True
    return propagate(child, dirty_rows, dirty_columns, deadline, cache), child


def _probe_candidates(board: Board, limit: int) -> list[tuple[int, int]]:
    """The ``limit`` most constrained unknown cells, most constrained first.

    "Most constrained" is the product of the placements the cell's row still
    admits and the placements its column still admits — the same measure the
    pre-CARD-018 branch heuristic used, and for the same reason: placement
    count is a line's actual remaining freedom, where unknown-cell count is
    only a proxy for it. Propagation cached those counts, so this is a scan of
    two int lists and a sort, not a re-run of the line DP.

    The cap is what makes probing affordable. Probing every unknown cell of a
    20x20 costs a fifth of a second per node, which no amount of pruning pays
    back; probing the eight tightest costs a few milliseconds and finds most of
    what the full sweep would, because a contradiction has to surface through
    some line, and the tightest lines are where there is least room for it to
    hide. Rounds past the first widen the cap (:data:`_SEARCH_ROUNDS`) rather
    than lifting it.

    ``limit`` must be at least 1. Returning an empty list for a board that
    still has unknown cells would leave :func:`_expand` with nothing to branch
    on, and :func:`_expand` raises rather than guessing what that meant.
    """
    ranked: list[tuple[int, int, int]] = []
    width = board.width
    full = (1 << width) - 1
    column_placements = board.column_placements
    for row in range(board.height):
        unknown = ~(board.row_filled[row] | board.row_empty[row]) & full
        if not unknown:
            continue
        freedom = board.row_placements[row]
        while unknown:
            column = (unknown & -unknown).bit_length() - 1
            unknown &= unknown - 1
            ranked.append((freedom * column_placements[column], row, column))
    ranked.sort()
    return [(row, column) for _, row, column in ranked[:limit]]


def _support(
    cache: LineCache,
    memo: dict[int, tuple[int, int, int] | None],
    runs: LineClue,
    length: int,
    known_filled: int,
    known_empty: int,
) -> int:
    """How many placements of ``runs`` survive the given knowledge; 0 if none.

    Answered through the memo, and in practice almost always *from* it: the
    probe that just ran asked its own row and column this very question as its
    first act, so the value ordering above rides along on work already done.
    """
    deduced = cache.deduce(memo, runs, length, known_filled, known_empty)
    return 0 if deduced is None else deduced[2]


def _diversified(round_index: int, node_index: int, count: int) -> int:
    """Which of ``count`` equally live branches this node takes, past round 0.

    A restart that re-ran the same heuristic would re-walk the same tree and
    learn nothing, so rounds after the first spread their branch choice over
    all the candidates probing found live. What makes that worth doing is that
    the instances round 0 cannot finish are overwhelmingly instances where one
    early branch went the wrong way: measured on the 20x20 grids CARD-018
    exists for, a re-run that branches elsewhere settles 21 of 26 such
    instances in well under a second, where re-running the same order settles
    none of them — by construction, since it would visit the same nodes again.

    The choice is a hash of ``(round_index, node_index)``, not a random draw:
    the solver has no randomness (ADR-0007) and must answer the same clue set
    the same way every time, which
    ``test_solving_the_same_clues_twice_gives_the_same_answer`` pins. Mixing in
    the node index rather than only the round is what makes a round differ from
    its predecessor at *every* depth instead of only at the root.
    """
    mixed = (round_index * 0x9E3779B97F4A7C15 + node_index * 0xD1B54A32D192ED03) & _MASK64
    mixed ^= mixed >> 30
    mixed = (mixed * 0xBF58476D1CE4E5B9) & _MASK64
    mixed ^= mixed >> 27
    mixed = (mixed * 0x94D049BB133111EB) & _MASK64
    mixed ^= mixed >> 31
    return mixed % count



def _to_grid(board: Board) -> Grid:
    """A fully decided board in the ADR-0012 boundary type (``list[list[bool]]``).

    The bitmask-to-boundary seam ADR-0012 flags as the place off-by-one and
    bit-order bugs live, so it is one expression, used by exactly one caller,
    and covered directly by ``TestSolver_*`` round-trip tests.
    """
    return [
        [bool((board.row_filled[row] >> column) & 1) for column in range(board.width)]
        for row in range(board.height)
    ]


def _verified_grid(board: Board) -> Grid:
    """Convert a completed board to a grid, refusing to return a wrong one.

    The CON-005 backstop described in the module docstring: every line of the
    finished board is re-encoded from its mask and compared with the clue it
    was solved from, in *both* orientations, before the grid is handed back to
    be counted.

    This is not a tautology, which is the only reason it is worth its cost.
    The search reaches this point by way of the placement DP, its fixed-point
    sweep and the bitmask/boundary conversion; :func:`~nonogram.solver.propagate.mask_runs`
    walks the finished masks cell by cell and shares none of that machinery. A
    dropped fixed point, a bit-order slip in the conversion, or an off-by-one
    in a line's placement all show up here as a mismatch.

    Raises:
        RuntimeError: the completed grid does not encode back to the clues it
            was solved from. Unreachable unless the solver is broken, which is
            precisely why it is not silently swallowed.
    """
    for row in range(board.height):
        found = mask_runs(board.row_filled[row], board.width)
        if found != board.row_clues[row]:
            raise _defect("row", row, board.row_clues[row], found)
    for column in range(board.width):
        found = mask_runs(board.column_filled[column], board.height)
        if found != board.column_clues[column]:
            raise _defect("column", column, board.column_clues[column], found)
    return _to_grid(board)


def _defect(orientation: str, index: int, expected: LineClue, found: LineClue) -> RuntimeError:
    return RuntimeError(
        f"solver completed a grid whose {orientation} {index} encodes to "
        f"{found} but was solved from clue {expected}; this is a solver defect "
        f"(CON-005), not a puzzle outcome"
    )
