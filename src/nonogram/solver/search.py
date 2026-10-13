"""COMP-005 search — counting solutions with fail-fast (ADR-0009, FR-006).

The public entry point is :func:`solve`. It takes clues in CARD-002's boundary
type and answers the one question CAP-003 exists to answer: does this clue set
have no solution, exactly one, or more than one?

Shape of the solve (ADR-0009, CARD-018, ADR-0029)
-------------------------------------------------
0. Run ADR-0029's ladder as three stratified fixed points, each continuing from
   the board the previous one left (:func:`solve`): the knowledge-relative
   overlap rule alone (``simple_overlap``), then the full placement
   intersection (``line_dp``), then probe refutation (``probe_contradiction``).
   The first two together *are* line logic's first fixed point — monotone
   propagation is confluent, so splitting it in two and running the cheaper
   technique to exhaustion first settles exactly the same cells — which is why
   ``line_logic_cells`` and the undecided mask are read between levels 2 and 3
   and mean what they always meant.
1. If levels 1 and 2 fully decide the board, it is the only solution reachable
   without lookahead and the solve is over.
1b. Otherwise run round 0's plain descent once, bounded by its own node limit,
   *purely to detect* :data:`MANY`. Rung attribution is reported only for a
   clue set with exactly one solution (ADR-0029, 2026-09-12 scoping), so a
   clue set this round shows to be ambiguous has nothing for level 3 to
   attribute and is answered here, with the two witnesses the round found. A
   round that instead ran out of nodes, or finished with 0 or 1 solutions, has
   proved nothing this solve keeps: its findings *and* its counters are
   discarded whole — the same treatment a :data:`_CUT_OFF` round gets — and
   the solve carries on from step 2 as though it had never run. A uniquely
   solvable clue set therefore always reaches level 3, with fresh counters, so
   its tags stay complete and order-independent.
2. Otherwise level 3 probes every still-unknown cell with both values, forcing
   the survivor wherever one value contradicts, to a fixed point. If *that*
   completes the board the solve is over too — with ``branch_nodes == 0``,
   because no search node was ever expanded. That is the point of making
   probing a phase rather than search work: a puzzle a refuted probe finishes
   is gradeable on this ladder (Hard) instead of being ``Tier.GUESS`` under
   ADR-0025 for work the search happened to do.
3. Otherwise search, from the level-3 fixed point. At every node a *pass* takes some
   set of unknown cells and, for each, tentatively assigns both values and
   propagates. A value whose propagation contradicts cannot appear in any
   solution, so the other value is forced and is applied for real; if both
   contradict, the whole node is refuted. Only when a pass forces nothing does
   the search actually branch, keeping the two boards the pass already
   produced as its children.
4. *How wide that pass looks is the round's business.* Round 0 looks at one
   cell — the single most constrained one, exactly the cell the pre-CARD-018
   search would have guessed at — which makes it a plain descent with a free
   contradiction check and nothing else. Later rounds *probe*: they look at
   the ``probe_width`` most constrained cells at once, which prunes far harder
   and costs proportionally more (see :data:`_SEARCH_ROUNDS`).
5. Stop the instant a *second* distinct solution is recorded (AC-017).
6. If a pass over the tree exceeds its node limit without settling the verdict,
   restart it with a wider probe and a larger limit (see
   :data:`_SEARCH_ROUNDS`). The limits grow without bound, so the search is
   still complete; what changes is that a hard instance is not held hostage to
   one heuristic's first guess.

The search is iterative rather than recursive. Depth is bounded by the number
of guesses, which at the 30x30 upper bound (ADR-0001) can exceed CPython's
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

What else the answer carries (CARD-073, FR-024 and FR-029's solver half)
------------------------------------------------------------------------
Three things the search already knew and used to throw away, now reported —
none of which changes a verdict, a stopping point or a signal any earlier
caller reads (EC-012):

* the cells line logic left undecided at its **first** fixed point, which is
  the same fixed point ``line_logic_cells`` is counted at (the end of level 2);
* on :data:`MANY`, the *second* solution — the very one whose discovery stops
  the fail-fast search, kept rather than dropped, so the pair is free;
* the ADR-0029 ladder rung that settled each cell, which under the revised
  ladder is simply *the level whose fixed point first settled it*: level 1
  tags ``simple_overlap``, level 2 ``line_dp``, level 3
  ``probe_contradiction``. All of it inside the single verifying solve
  (ADR-0029/R2) and with no clock in it (ADR-0029/R3).

A cell the *search* settles carries no rung at all. That is not an omission:
below a guess, which cell a refutation reaches depends on where the search
branched, so a tag written there would be a fact about the search order rather
than about the clue set — exactly what ADR-0029/R5 forbids. A puzzle whose
search ran at all is ``Tier.GUESS`` under ADR-0025 and is not graded on this
ladder anyway.

Seeded counts, and the chooser on top of them (CARD-214)
--------------------------------------------------------
:func:`solve` answers a second question since CARD-214, through the same
machinery: *how many solutions are there given that these cells are known?*
The ``givens`` keyword is a grid-shaped partial assignment
(:data:`Givens` — ``True`` filled, ``False`` empty, ``None`` unknown) seeded
into the board with :meth:`~nonogram.solver.propagate.Board.assign` **before**
the first propagation round, so every level of the ladder, the search and the
CON-005 re-encode backstop treat a given exactly as they treat a cell line
logic settled. Nothing about the verdicts moves: ``givens=None`` (the default)
builds the same blank board the solver always built, which is what keeps every
existing caller and every recorded verdict byte-identical (guardrail G-3).

Seeding is sound for the same one-line reason probing is: propagation only ever
writes cells every *remaining* solution agrees on, and a given removes from
consideration exactly the solutions that disagree with it. So the seeded count
is the number of solutions of the clue set that extend the givens — which is 0
when a given contradicts the clues (the propagation refuses a line, and that is
a count, not an exception: AC-8), and at most the unseeded count.

:func:`choose_givens` is the consumer this was added for: the smallest thing
that turns an ambiguous picture into a puzzle *without changing the picture*.
It solves, and while the count is ``MANY`` it reveals the first cell (by row
then column) on which the two witnesses disagree, to the value the real
solution grid holds, and solves again. Pure — no rng, no clock of its own, no
host state — so the same grid yields the same givens in the same order on every
machine, which is the reproducibility ADR-0024/R4 fixes for the repair pair and
this card needs for the same reason. The *policy* that calls it (when a reveal
is allowed, how many cells may be revealed, and the fresh re-verify that
accepts the result) is the orchestrator's, not this module's.

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
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from nonogram.errors import GivenCellsCapExceeded
from nonogram.solver.propagate import (
    RUNG_LINE_DP,
    RUNG_ORDER,
    RUNG_PROBE_CONTRADICTION,
    RUNG_SIMPLE_OVERLAP,
    Board,
    LineCache,
    LineClue,
    RungTagger,
    canonical_clue,
    check_deadline,
    mask_runs,
    propagate,
    propagate_overlap,
)

__all__ = [
    "MANY",
    "RUNG_ORDER",
    "Givens",
    "SolveResult",
    "SolveSignals",
    "choose_givens",
    "revealed_cells",
    "solve",
]

Grid = list[list[bool]]
ClueSet = tuple[tuple[int, ...], ...]
#: A grid-shaped partial assignment: ``True`` filled, ``False`` empty, ``None``
#: unknown, one entry per cell (CARD-214).
#:
#: Deliberately a plain nested list of builtins rather than a value object or a
#: list of ``(row, column, value)`` triples. It crosses module boundaries —
#: ``solve`` takes one, :func:`choose_givens` returns one, the orchestrator
#: carries one on the aggregate, and later cards render and persist it — and a
#: *type* at that boundary would have to be imported from here, which ADR-0007
#: forbids for a capability module reaching sideways into another (``export/``
#: and the admin layer may not import ``solver/``). A structure made of
#: builtins needs no import at all, which is the same reason a solution grid
#: crosses as ``list[list[bool]]`` and not as the internal bitmask pair
#: (ADR-0012, guardrail G-5).
Givens = list[list[bool | None]]
#: One ADR-0029 rung name per cell, ``None`` where no deduction phase of the
#: solve settled the cell (see :attr:`SolveResult.rung_tags`).
RungTags = list[list[str | None]]

#: The rung histogram of a solve that settled nothing — every rung present with
#: a count of zero, so a consumer can index any rung without a ``get``. Shared
#: and read-only, which is why it can be a plain dataclass default.
_NO_RUNG_CELLS: Mapping[str, int] = MappingProxyType(dict.fromkeys(RUNG_ORDER, 0))

#: The reported ``solution_count`` for a clue set with more than one solution.
#: The search stops here by design (AC-017), so the value means ">= 2" and
#: never "exactly 2".
MANY = 2

#: Round 0's "probe width": not a width at all, but the marker for the round
#: that does not probe. See :data:`_SEARCH_ROUNDS`.
_NO_PROBE = 0

#: The restart schedule (CARD-018): ``(probe_width, node_limit)`` per round.
#:
#: ``probe_width`` is how many of the most constrained unknown cells a probing
#: pass examines, and ``node_limit`` how many search nodes the round may visit
#: before it is abandoned and the next one started.
#:
#: **Round 0 does not probe at all** (:data:`_NO_PROBE`). It looks at the one
#: cell the pre-CARD-018 heuristic would have guessed at (:func:`_branch_cell`)
#: and branches there, so it is the old search plus a free contradiction check
#: — and it is bounded, so a board it cannot settle quickly falls through to
#: the probing rounds rather than grinding on.
#:
#: That escape hatch is not decoration; it is what the first cut of this card
#: got wrong (review cycle 1, F-002). Probing every node from node 0 pays for
#: pruning on boards that need none: at 20x20 and 10-25% density a candidate is
#: massively ambiguous, a second solution turns up a couple of hundred nodes in,
#: and the tree probing builds there is the *same size* as the plain one — 7,329
#: nodes against 4,139 on one measured request — for 3.4x the cost per node.
#: Measured over that request's twenty candidates: plain 0.37s, probing 2.29s.
#: The cell ranking matters as much as the width does, which is why round 0
#: keeps the old heuristic rather than taking the top of the probe ranking:
#: width 1 over the *probe* ranking does not finish that request at all.
#:
#: The probing rounds exist for the minority round 0 cannot finish, and they
#: widen on both axes at once, because measurement showed the two failures are
#: different: some instances are hard because one early guess was wrong (a
#: re-run that branches elsewhere finds a solution in milliseconds) and others
#: because the inference is too weak to prune (a wider probe cuts them from
#: tens of seconds to one).
#:
#: Past the last entry the probe width stays put and the node limit keeps
#: multiplying by :data:`_NODE_LIMIT_GROWTH`, so the limit is unbounded in the
#: limit and a search that needs the whole tree eventually gets it. That is
#: what keeps restarting *complete*: a verdict is only ever taken from a round
#: that finished on its own terms, never from one that ran out of nodes.
_SEARCH_ROUNDS: tuple[tuple[int, int], ...] = (
    (_NO_PROBE, 400),
    (8, 400),
    (16, 1200),
    (32, 3600),
    (64, 10800),
)

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
    #: Search nodes the solve expanded past line logic — one per board taken
    #: off the search stack, whether the search went on to guess there, settled
    #: it by forced deduction, or refuted it outright. ADR-0013's "backtracking
    #: amount" term (see ADR-0013's 2026-08-30 History note).
    #:
    #: Before CARD-018 this was "how many times the search had to guess a
    #: cell", and the two were the same number, because guessing was the only
    #: thing a node could do. CARD-018's probing gave a node two more
    #: outcomes — deduce, and refute — and counting only the guesses would then
    #: report 0 for a puzzle whose whole search was forced deductions past a
    #: stalled fixed point, i.e. score real search work as free. What the term
    #: has always been *for* is how much the search had to do beyond line
    #: logic, and that is what it still counts. ``0`` exactly when line logic
    #: alone finished the puzzle, which is the anchor AC-023 rests on.
    #:
    #: Counted for the restart round that produced the verdict, not summed over
    #: the abandoned ones (CARD-018 review cycle 1, F-001): a puzzle's
    #: difficulty is a property of the puzzle, and adding in the nodes of
    #: rounds whose findings were thrown away would make two equally hard
    #: puzzles score differently according to how unlucky one heuristic got.
    branch_nodes: int
    #: How many tentative cell assignments ran straight into a contradiction —
    #: a subtree proved empty without being descended into. Distinct from
    #: ``branch_nodes``: a puzzle can expand many nodes and never backtrack.
    #: Before CARD-018 the search discovered these by guessing and having
    #: propagation refuse the guess; it now discovers most of them by probing,
    #: which is the same event found earlier, so the same assignments are
    #: counted — one per refuted assignment, and two when both values of one
    #: cell are refuted.
    #:
    #: Telemetry only: ADR-0013's formula does not read this field (see
    #: ``difficulty.SolverSignals``), which is why probing finding *more* of
    #: them than guessing did changes no score. Scoped to the deciding round,
    #: like ``branch_nodes``.
    backtracks: int
    #: Wall-clock seconds for the whole solve, from a monotonic clock.
    #:
    #: Telemetry, and only telemetry (ADR-0029/R3, CON-014, guardrail G-5):
    #: NFR-001 is measured by it, and no rung tag, no rung list and no
    #: difficulty term may read it. It is the one field here a second run on a
    #: slower machine changes, which is exactly why nothing graded may depend
    #: on it.
    elapsed_seconds: float
    #: How many cells each ADR-0029 rung settled in this solve. Always carries
    #: all three rung names as keys, so a consumer can index rather than
    #: ``get``; the values sum to the number of tagged cells in
    #: :attr:`SolveResult.rung_tags`, which is the whole grid exactly when the
    #: three deduction phases finished the puzzle without the search.
    #:
    #: ADR-0029/R1's within-rung order (cells at the top rung / total cells)
    #: is computed from this by COMP-006; the solver counts and does not grade
    #: (CARD-073 guardrail G-4 — CARD-076 owns the formula).
    rung_cells: Mapping[str, int] = _NO_RUNG_CELLS
    #: The distinct rungs the deciding solve used, in ladder order — FR-029's
    #: strategies list as the solver sees it. ``guess`` is **not** appended
    #: here even when the search branched: ADR-0025 keys that on
    #: :attr:`branch_nodes`, and CARD-072 appends it where the list is
    #: persisted and exported. Empty for a solve that settled nothing — and
    #: empty, with an all-zero :attr:`rung_cells`, for every clue set whose
    #: ``solution_count`` is not 1, which has no grade to report (ADR-0029,
    #: 2026-09-12 scoping; see :attr:`SolveResult.rung_tags`).
    rungs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SolveResult:
    """What :func:`solve` answers: a count, its witnesses, and the signals.

    Everything past ``signals`` was added by CARD-073 and is purely additive
    (EC-012): the three pre-existing fields keep their pre-existing meaning for
    every caller — the orchestrator's ``solution_count == 1`` gate, COMP-006's
    signals protocol and EC-001's oracle cross-check read exactly what they
    read before — and no verdict changed. Every addition crosses the boundary
    as a grid-shaped ``list[list[...]]``; the solver's internal filled/empty int
    bitmask pair does not appear here in either direction (ADR-0012, G-3).
    """

    #: ``0``, ``1``, or :data:`MANY` (``2``, meaning ">= 2").
    solution_count: int
    #: The solution grid in the ADR-0012 boundary type when
    #: ``solution_count == 1``; ``None`` when there is no solution. When there
    #: is more than one, this is the first solution found — a witness, not
    #: "the" solution, and callers gated on uniqueness must not use it.
    solution: Grid | None
    signals: SolveSignals
    #: On :data:`MANY`, a *second* solution, distinct cell by cell from
    #: :attr:`solution` (TERM-009); ``None`` for every other count (FR-024,
    #: AC-107). It is not found on purpose — it is the very solution whose
    #: discovery makes the count ``MANY`` and stops the fail-fast search
    #: (AC-017), kept instead of dropped. Nothing about when the search stops
    #: changed to produce it.
    #:
    #: The two witnesses are what ADR-0024's repair reads: they agree on every
    #: cell line logic settled, so the cells they disagree on are exactly the
    #: ambiguity, and every one of them is inside :attr:`undecided_mask`
    #: (EC-011).
    second_witness: Grid | None = None
    #: The cells line logic left undecided at its **first** propagation fixed
    #: point, grid-shaped, ``True`` for undecided (FR-024, AC-108). Reported for
    #: every count — empty for a line-solvable puzzle (AC-109), and still
    #: reported when the count is ``0`` (AC-110), where it describes the cells
    #: that were still open when propagation ran into the contradiction.
    #:
    #: POL-002's nudge (CARD-075) picks the cells it perturbs from here, which
    #: is why it is the *first* fixed point and not the deciding round's: it is
    #: a property of the clue set, independent of how the search that followed
    #: chose to branch.
    undecided_mask: Grid = field(default_factory=list)
    #: The ADR-0029 ladder rung that settled each cell, grid-shaped: the level
    #: at whose fixed point the cell was first settled. ``None`` for a cell no
    #: deduction phase reached — every cell of a grid the search only completed
    #: by guessing past the stalled level-3 fixed point, for instance, since
    #: ``guess`` is not a rung of this ladder and a deduction taken below a
    #: guess is a fact about the search order rather than about the clue set
    #: (ADR-0029/R5).
    #:
    #: Computed inside the one verifying solve (ADR-0029/R2): the three phases
    #: tag as they deduce, each continuing from the board the previous left.
    #: There is no second :func:`solve` entry, no reset and no re-propagation
    #: for classification, and there is no clock in any tag (ADR-0029/R3).
    #:
    #: **Reported only when ``solution_count == 1``** (ADR-0029, 2026-09-12
    #: scoping). A clue set with 0 or >= 2 solutions is not a puzzle: it has no
    #: grade and no strategies list, so every cell comes back ``None`` and
    #: :attr:`SolveSignals.rungs` comes back empty, whatever the deduction
    #: phases happened to settle on the way to that verdict.
    rung_tags: RungTags = field(default_factory=list)

    @property
    def is_unique(self) -> bool:
        """Exactly one solution — the INV-002 gate CARD-005's loop retries on."""
        return self.solution_count == 1

    @property
    def witnesses(self) -> tuple[Grid, ...]:
        """The solutions this solve actually has in hand: 0, 1 or 2 grids.

        A convenience over :attr:`solution` and :attr:`second_witness` for the
        consumers that want "whatever was found" rather than the verdict —
        ADR-0024's repair, which needs the pair, and the EC-011 property test,
        which checks every one of them re-encodes to the input clues.
        """
        return tuple(
            grid for grid in (self.solution, self.second_witness) if grid is not None
        )


def solve(
    row_clues: ClueSet,
    column_clues: ClueSet,
    *,
    givens: Givens | None = None,
    deadline: float | None = None,
) -> SolveResult:
    """Count a clue set's solutions, stopping at two (FR-006).

    Args:
        row_clues: One clue tuple per row, top to bottom, in CARD-002's
            boundary type — ``(0,)`` for an empty line (AC-013).
        column_clues: One clue tuple per column, left to right.
        givens: A grid-shaped partial assignment seeded into the board before
            the first propagation round (:data:`Givens`), or ``None`` (the
            default) for the blank board the solver always started from.
            ``solution_count`` then means "solutions consistent with the clues
            **and** the givens": the question is narrowed, nothing about how it
            is answered changes. Keyword-only and defaulted for the same reason
            ``deadline`` is — it is not part of the question most callers ask,
            and with it absent every existing caller's verdict, signals and
            witnesses are byte-identical to what they were (CARD-214 guardrail
            G-3).

            A given that contradicts the clues yields ``solution_count = 0``,
            not an exception (AC-8): a partial assignment no solution extends
            is a fact about the count, exactly as a contradictory clue set is
            (AC-016). A *malformed* one — the wrong shape for the clues — is
            a ``ValueError``, exactly as a malformed clue is.
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
        when the count is 1 and the FR-009 signals either way — plus, since
        CARD-073 and without any verdict changing: the first fixed point's
        undecided mask for every count (FR-024), a second witness when the
        count is :data:`MANY`, and the ADR-0029 rung that settled each cell.

        Under a ``givens`` the same fields describe the *seeded* question. Two
        of them are worth naming because they are honestly different rather
        than broken: ``line_logic_cells`` counts the given cells too (they are
        known at the first fixed point, which is what that signal measures),
        and a given cell carries no rung tag, because no rung of ADR-0029's
        ladder deduced it — it was handed over. Neither is read on the seeded
        path by anything that grades a *puzzle*: the grades on record all come
        from unseeded solves.

    Raises:
        ValueError: the clue set is malformed — a run that is not a positive
            int, or the empty-line marker used alongside other runs — or
            ``givens`` is not shaped like the puzzle the clues describe. Not a
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

    # Shape-checked before anything else, so a malformed partial assignment is
    # always the ``ValueError`` the contract promises rather than whatever the
    # early exits below would have returned for the clues alone.
    _check_givens_shape(givens, height, width)

    def finish(
        count: int,
        solution: Grid | None,
        branches: int,
        backtracks: int,
        line_logic_cells: int,
        undecided_mask: Grid,
        rung_tags: RungTags,
        second_witness: Grid | None = None,
    ) -> SolveResult:
        """Stamp the elapsed time on and return — every exit goes through here.

        The rung histogram and the ordered rung list are counted here, from the
        tags the solve produced, so there is exactly one place they can come
        from and they cannot disagree with the per-cell tags (ADR-0029/R2).

        It is also the one place ADR-0029's 2026-09-12 scoping is applied: rung
        attribution is reported *only* for a clue set with exactly one
        solution. A clue set with 0 or >= 2 solutions is not a puzzle — it has
        no grade and no strategies list — so whatever the deduction phases
        happened to tag on the way to that verdict is dropped here rather than
        reported as a grade of a thing that has none.
        """
        if count != 1:
            rung_tags = [[None] * width for _ in range(height)]
        rung_cells = dict.fromkeys(RUNG_ORDER, 0)
        for tag_row in rung_tags:
            for tag in tag_row:
                if tag is not None:
                    rung_cells[tag] += 1
        if givens is not None:
            # The seeded path's share of the CON-005 self-check (see the module
            # docstring): every witness is already re-encoded against the clues
            # by ``_verified_grid``, and this adds the other half of the seeded
            # question — that it also extends the assignment it was counted
            # under. Monotone seeding makes it unreachable (nothing ever
            # un-decides a cell), which is exactly why it is cheap to assert
            # and why a failure here would be a solver defect rather than a
            # puzzle outcome. Only on the seeded path, so the default path does
            # not pay a cell walk it cannot fail.
            for witness in (solution, second_witness):
                if witness is not None:
                    _check_respects_givens(witness, givens)
        return SolveResult(
            solution_count=count,
            solution=solution,
            second_witness=second_witness,
            undecided_mask=undecided_mask,
            rung_tags=rung_tags,
            signals=SolveSignals(
                line_logic_cells=line_logic_cells,
                total_cells=total_cells,
                branch_nodes=branches,
                backtracks=backtracks,
                elapsed_seconds=time.perf_counter() - started,
                rung_cells=MappingProxyType(rung_cells),
                rungs=tuple(rung for rung in RUNG_ORDER if rung_cells[rung]),
            ),
        )

    # A solution's filled cells are counted once by the row clues and once by
    # the column clues, so unequal totals mean there is nothing to search for.
    # Only an early exit — the search below would reach the same verdict.
    if sum(sum(clue) for clue in rows) != sum(sum(clue) for clue in columns):
        # No board was ever built, so nothing was decided and every cell is
        # open: the mask reports that rather than being withheld, because
        # AC-110 asks for a mask on *every* zero-solution verdict and "no cell
        # was settled" is the honest answer for a clue set the solver refused
        # before line logic ran.
        return finish(
            0,
            None,
            0,
            0,
            0,
            [[True] * width for _ in range(height)],
            [[None] * width for _ in range(height)],
        )

    if total_cells == 0:
        # A grid with no cells: the empty grid is its only candidate, and it
        # is a solution exactly when every line's clue is the empty marker
        # (the sum check above has already established that). Handled here
        # because a zero-row grid has no cells to re-encode its column clues
        # from, so the verification below would misread it as a defect.
        return finish(
            1,
            [[] for _ in range(height)],
            0,
            0,
            0,
            [[] for _ in range(height)],
            [[] for _ in range(height)],
        )

    # One memo per solve, created here and dropped when this call returns, so
    # the solver keeps no state between calls (CARD-018; the memo only ever
    # returns what ``line_intersection`` would have).
    cache = LineCache.blank(height, width)

    board = Board.blank(rows, columns)
    if givens is not None:
        # CARD-214: the partial assignment goes in *before* level 1, through
        # the same :meth:`Board.assign` the search uses for a branch, so there
        # is no second way for a cell to become known and every phase below
        # reads a given exactly as it reads a deduction. Level 1 starts with
        # every line dirty anyway, so the seeded knowledge is used from the
        # first sweep.
        _seed_givens(board, givens)
    #: ADR-0029's per-cell rung map, written by the three phases below and by
    #: nobody else. One grid, shared across the phases, so a rung is claimed by
    #: the first level to settle the cell and no later level can overwrite it —
    #: which is what "the level at whose fixed point it was first settled"
    #: means, expressed as data rather than as a rule.
    tags: RungTags = [[None] * width for _ in range(height)]

    # ------------------------------------------------------------------
    # Level 1 (ADR-0029): the knowledge-relative overlap rule, to a fixed
    # point over rows and columns. Cheapest rung first (ADR-0029/R2).
    # ------------------------------------------------------------------
    board.tagger = RungTagger(tags, RUNG_SIMPLE_OVERLAP)
    if not propagate_overlap(board, [True] * height, [True] * width, deadline):
        return finish(0, None, 0, 0, board.decided, _undecided_mask(board), tags)

    # ------------------------------------------------------------------
    # Level 2: the full placement intersection, continuing from level 1's
    # board and starting with *every* line dirty. That last detail is what
    # makes levels 1 and 2 together reach exactly the fixed point a single
    # ``propagate`` from the blank board reaches — monotone propagation is
    # confluent, but only if every line is examined at least once under the
    # dearer rule (CON-005: no verdict may move).
    # ------------------------------------------------------------------
    board.tagger = RungTagger(tags, RUNG_LINE_DP)
    if not propagate(board, [True] * height, [True] * width, deadline, cache):
        return finish(0, None, 0, 0, board.decided, _undecided_mask(board), tags)
    # Detached the moment line logic's fixed point is reached, so nothing level
    # 3 or the search does can reach it even by accident. (It could not anyway —
    # ``Board.clone`` drops it and both only ever propagate clones — but the
    # root board outlives this line, and a live tagger on it would be a loaded
    # gun for the next card that adds a caller.)
    board.tagger = None

    # Everything settled up to here came from line logic alone (FR-009), which
    # is levels 1 and 2 and *not* level 3: ``line_logic_cells`` keeps exactly
    # the meaning every existing consumer reads it with. Computed once, here,
    # because it does not depend on how the search that may follow chooses to
    # branch — and neither does the undecided mask (FR-024), which is the same
    # fixed point read cell by cell.
    line_logic_cells = board.decided
    undecided_mask = _undecided_mask(board)

    if board.decided == total_cells:
        return finish(
            1, _verified_grid(board), 0, 0, line_logic_cells, undecided_mask, tags
        )

    # ------------------------------------------------------------------
    # Is this clue set a puzzle at all? (ADR-0029, 2026-09-12 scoping.)
    #
    # Level 3 exists to *attribute* — it is the dearest rung of the ladder, and
    # the ladder grades puzzles. A clue set with two solutions has no grade and
    # no strategies list (``finish`` drops the tags), so every lookahead level 3
    # would run on it is work whose only product is thrown away. On the
    # generator's discard path that is the whole cost: a 20x20 candidate at 20%
    # density leaves ~300 cells open at line logic's fixed point, so level 3
    # pays ~600 propagations to force almost nothing — a massively ambiguous
    # board is exactly the board single-cell lookahead cannot refute anything
    # on — while round 0's plain descent finds a second solution a couple of
    # hundred nodes in.
    #
    # So round 0 runs first, bounded by its own node limit, purely as a MANY
    # detector. Two solutions is a verdict on its own terms: both are verified
    # against the clues (:func:`_verified_grid`), sibling branches are disjoint,
    # and the board it searched is line logic's fixed point, which every
    # solution extends. Anything else — a cut-off, or a round that finished with
    # 0 or 1 solutions — proves nothing that this solve is willing to keep, so
    # its findings *and* its counters are discarded whole, exactly as a
    # :data:`_CUT_OFF` round's are, and the solve proceeds as if it had never
    # run. A uniquely solvable clue set therefore always reaches level 3 with
    # fresh counters, and its attribution is as complete and as
    # order-independent as it was before this check existed.
    speculative_width, speculative_limit = _round(0)
    speculative_counters = _Counters()
    speculative = _search(
        board,
        cache,
        speculative_width,
        speculative_limit,
        0,
        deadline,
        speculative_counters,
    )
    if speculative is not _CUT_OFF and len(speculative) == MANY:  # type: ignore[arg-type]
        # This round *is* the deciding round, so its counters are the signals,
        # exactly as they would be if it had been reached through the restart
        # loop below (F-001: the reported signals describe the round that
        # settled the verdict and no other).
        witnesses: list[Grid] = speculative  # type: ignore[assignment]
        return finish(
            MANY,
            witnesses[0],
            speculative_counters.branch_nodes,
            speculative_counters.backtracks,
            line_logic_cells,
            undecided_mask,
            tags,
            witnesses[1],
        )

    # ------------------------------------------------------------------
    # Level 3: probe refutation, to a fixed point, continuing from level 2's
    # board. Everything it settles is ``probe_contradiction``.
    # ------------------------------------------------------------------
    board, contradicted = _probe_fixed_point(board, cache, deadline, tags)
    if not contradicted and board.decided == total_cells:
        # No node was ever expanded, so ``branch_nodes`` is 0 and ADR-0025
        # grades this puzzle on the ladder rather than as Tier.GUESS.
        return finish(
            1, _verified_grid(board), 0, 0, line_logic_cells, undecided_mask, tags
        )

    # One counter set per round, so the signals returned describe the round
    # that actually produced the verdict (F-001). An abandoned round proved
    # nothing and contributes nothing, to the count as to the signals.
    round_index = 0
    while True:
        probe_width, node_limit = _round(round_index)
        counters = _Counters()
        found = _search(
            board, cache, probe_width, node_limit, round_index, deadline, counters
        )
        if found is not _CUT_OFF:
            solutions = found  # type: ignore[assignment]
            break
        round_index += 1

    count = len(solutions)
    solution = solutions[0] if solutions else None
    # The second solution the fail-fast search stopped on *is* FR-024's second
    # witness — kept, not sought. ``len(solutions) <= MANY`` by construction,
    # and sibling branches are disjoint, so when there are two they differ in
    # at least the cell their branch fixed (TERM-009).
    second_witness = solutions[1] if len(solutions) > 1 else None
    return finish(
        count,
        solution,
        counters.branch_nodes,
        counters.backtracks,
        line_logic_cells,
        undecided_mask,
        tags,
        second_witness,
    )


def choose_givens(
    grid: Grid,
    row_clues: ClueSet,
    column_clues: ClueSet,
    *,
    cap: int,
    deadline: float | None = None,
) -> Givens:
    """Which cells of ``grid`` to reveal so that its clues have one solution.

    CARD-214's chooser: the third recovery option, and the only one that leaves
    the picture alone. POL-001 redraws it, POL-002 nudges its pixels and
    POL-006 flips a pair inside the ambiguity (ADR-0024); this reveals cells of
    the solution instead, which changes no cell of the grid and no clue of it
    (INV-001 untouched) and buys uniqueness at the price of giving some of the
    answer away.

    A *value*, computed in nothing's place: the returned assignment is handed
    back for the caller to verify and to carry, and this function mutates
    neither ``grid`` nor anything else.

    How it chooses, and why that way:

    * solve; if the count is already 1 there is nothing to reveal and the
      all-``None`` assignment comes back, so an already-unique picture is left
      exactly as it is (AC-2);
    * on :data:`MANY`, take the cells the two witnesses disagree on — the
      ambiguity the solver has just *located*, which is where a reveal can
      possibly help and where ADR-0024's repair reads from too — and reveal the
      **first by (row, column)**, to the value ``grid`` itself holds. First by
      (row, column) is ADR-0024/R4's rule, adopted here for ADR-0024/R4's
      reason: a seed must replay, so the choice has to be a function of the
      grid and the solver's report and of nothing else;
    * solve again, with the reveal in place, and repeat.

    Progress is structural rather than hoped for, in both directions.

    *It always advances.* A disagreement cell is undecided in the solve that
    reported it (EC-011: propagation only writes cells every solution agrees
    on), so it is never a cell already revealed; each round therefore reveals
    one *new* cell and the unknown count strictly falls. Revealing everything
    would leave exactly one solution, so the loop terminates with or without
    ``cap`` — ``cap`` is there because a puzzle needing a large share of its
    own answer given away is not a puzzle, not because the loop might run away.

    *It never advances into a contradiction.* The two witnesses differ at the
    chosen cell, so one of them holds ``True`` there and the other ``False``;
    whichever value ``grid`` has, one of the two still satisfies the new
    assignment. A reveal can therefore never drop the count to 0 — which is why
    a 0 here means the clues have no solution *at all* and so cannot be any
    grid's encoding, rather than meaning "the reveals went wrong".

    Args:
        grid: The solution grid the clues came from. Every revealed cell takes
            *this* grid's value, which is what makes the result a partial
            picture of the real answer rather than a constraint invented to
            force uniqueness.
        row_clues: ``grid``'s row clues, in CARD-002's boundary type.
        column_clues: ``grid``'s column clues.
        cap: The most cells that may be revealed. **Required, with no default**:
            how much of the answer it is acceptable to give away is a policy
            judgement, it lives with the orchestrator's other bounds
            (``MAX_GIVEN_CELL_SHARE_PERCENT``), and a default here would be a
            second place to read it from. ``0`` is meaningful — "tell me
            whether this needs any reveal at all".
        deadline: ADR-0011's cooperative deadline, passed through to every
            solve unchanged. This function reads no clock itself; the solver
            raises :class:`~nonogram.errors.SolverTimeout` from its own
            checkpoints and it travels out of here uncaught, because a
            timed-out solve has no verdict to chose from.

    Returns:
        A :data:`Givens` the size of ``grid``, with ``None`` everywhere except
        the revealed cells. Empty (all ``None``) exactly when the clues already
        have one solution.

    Raises:
        GivenCellsCapExceeded: ``cap`` cells were revealed and the count was
            still :data:`MANY`. The grid is not altered and no puzzle is
            produced; the orchestrator lets this travel out, where the CLI maps
            it with the other "no usable puzzle" failures.
        ValueError: ``row_clues``/``column_clues`` are not ``grid``'s own
            run-length encoding — the caller has broken INV-001. Seen in one of
            two ways, neither of them possible for matching input: a solve that
            reports **0** solutions (the clues have no solution whatsoever, so
            they encode no grid — see the progress argument above for why a
            *reveal* cannot produce this), or one that reports **1** whose
            single solution is not ``grid`` (if the grid satisfies the clues
            and only one thing does, the grid is what comes back). Raised
            loudly rather than reported as "cannot be made unique": a chooser
            that quietly returned reveals making some *other* grid unique would
            hand back a puzzle whose answer is not the picture it came from,
            which is the one outcome this policy exists to prevent.

    Pure (ADR-0007): no filesystem, no rng, no host state, no module state, and
    no clock of its own — so the same grid gives the same cells in the same
    order in any process (EC(ADR-0024/R4)).
    """
    width = len(column_clues)
    givens: Givens = [[None] * width for _ in grid]
    revealed = 0
    while True:
        result = solve(row_clues, column_clues, givens=givens, deadline=deadline)
        if result.solution_count == 1:
            if result.solution != grid:
                raise ValueError(_not_the_grids_own_clues(revealed, "its solution"))
            return givens
        if result.solution_count == 0:
            raise ValueError(_not_the_grids_own_clues(revealed, "no solution"))
        if revealed == cap:
            raise GivenCellsCapExceeded(
                f"revealing {revealed} cell{'s' if revealed != 1 else ''} did "
                f"not make this picture uniquely solvable, and the cap is "
                f"{cap}: the picture is left unchanged rather than altered to "
                f"fit"
            )
        row, column = _first_disagreement_cell(result)
        givens[row][column] = grid[row][column]
        revealed += 1


def revealed_cells(givens: Givens | None) -> tuple[tuple[int, int, bool], ...]:
    """The revealed cells of ``givens`` as ``(row, column, value)``, row-major.

    A reader for the boundary type, for the callers that want the cells rather
    than the grid shape — the orchestrator's count, and the tests' "which cells
    and to what value". Row-major order, which for a :data:`Givens` produced by
    :func:`choose_givens` is *not* the order they were revealed in; nothing
    reads the reveal order, and the cells chosen are a set, so ordering them
    by position is the stable way to compare two runs.

    ``()`` for ``None`` and for an all-``None`` assignment, which are the same
    statement to every consumer: nothing was revealed.

    Not importable by ``export/`` or the admin layer (ADR-0007 forbids a
    capability module importing another). That is deliberate and is why the
    boundary type is plain builtins: a consumer on the wrong side of that rule
    reimplements these three lines natively, the way
    :func:`~nonogram.solver.propagate.mask_runs` reimplements a clue check
    rather than importing ``clues``.
    """
    if not givens:
        return ()
    return tuple(
        (row_index, column_index, value)
        for row_index, row in enumerate(givens)
        for column_index, value in enumerate(row)
        if value is not None
    )


def _not_the_grids_own_clues(revealed: int, observed: str) -> str:
    """The INV-001 refusal message, one wording for both ways of seeing it."""
    return (
        f"the clues passed in are not the run-length encoding of the grid "
        f"passed in (INV-001): after revealing {revealed} cell(s) of the grid, "
        f"the clues have {observed} elsewhere. choose_givens reveals cells of "
        f"the grid it is given, so it can only answer for that grid's own clues"
    )


def _first_disagreement_cell(result: SolveResult) -> tuple[int, int]:
    """The first cell by (row, column) on which the two witnesses differ.

    Raises:
        RuntimeError: the result has no witness pair, or the pair agrees
            everywhere. Both are unreachable for a :data:`MANY` verdict — the
            second witness is returned with it and is distinct from the first
            cell by cell (TERM-009, FR-024) — and both would make this function
            silently reveal nothing, which is the one shape of bug that could
            turn the reveal loop into a loop. A solver defect, not a puzzle
            outcome (CON-005), so it is loud.
    """
    first, second = result.solution, result.second_witness
    if first is not None and second is not None:
        for row_index, (left, right) in enumerate(zip(first, second, strict=True)):
            for column_index, (one, other) in enumerate(zip(left, right, strict=True)):
                if one != other:
                    return row_index, column_index
    raise RuntimeError(  # pragma: no cover - MANY always carries two witnesses
        f"a solution_count of {result.solution_count} came back without two "
        f"witnesses that disagree anywhere; this is a solver defect (CON-005), "
        f"not a puzzle outcome"
    )


def _check_givens_shape(givens: Givens | None, height: int, width: int) -> None:
    """Refuse a partial assignment that is not shaped like the puzzle.

    One entry per cell, no shorthand: a ragged or short ``givens`` would
    otherwise seed *some* of the cells the caller meant and silently count a
    different question than the one asked. Reported as a ``ValueError`` because
    that is how :func:`solve` already reports a malformed clue set, and for the
    same reason — it is not a fact about any puzzle.
    """
    if givens is None:
        return
    if len(givens) != height:
        raise ValueError(
            f"givens has {len(givens)} row(s) but the clues describe {height}"
        )
    for row_index, row in enumerate(givens):
        if len(row) != width:
            raise ValueError(
                f"givens row {row_index} has {len(row)} cell(s) but the clues "
                f"describe {width}"
            )


def _seed_givens(board: Board, givens: Givens) -> None:
    """Write a partial assignment into a blank board, cell by cell.

    Through :meth:`~nonogram.solver.propagate.Board.assign` rather than into
    the masks directly: that method writes both orientations and maintains
    ``decided``, and routing the seed through it is what makes a given
    indistinguishable from a branch assignment to everything downstream. The
    board is blank when this runs, so no cell can already be known — and
    ``assign`` would refuse if one were, which is the right answer to a caller
    that seeded twice.
    """
    for row_index, row in enumerate(givens):
        for column_index, value in enumerate(row):
            if value is not None:
                board.assign(row_index, column_index, bool(value))


def _check_respects_givens(grid: Grid, givens: Givens) -> None:
    """The seeded half of the CON-005 self-check (see the module docstring).

    Raises:
        RuntimeError: a counted witness disagrees with the assignment it was
            counted under. Unreachable — seeding is monotone and nothing in the
            solver ever un-decides a cell — and a wrong answer that crashes is
            recoverable where one that looks right is not.
    """
    for row_index, row in enumerate(givens):
        for column_index, value in enumerate(row):
            if value is not None and grid[row_index][column_index] != value:
                raise RuntimeError(  # pragma: no cover - seeding is monotone
                    f"solver counted a solution whose cell "
                    f"({row_index}, {column_index}) is "
                    f"{grid[row_index][column_index]} against a given of "
                    f"{value}; this is a solver defect (CON-005), not a puzzle "
                    f"outcome"
                )


@dataclass(slots=True)
class _Counters:
    """FR-009's two search signals, for one restart round.

    Scoped to a round rather than to the whole solve (CARD-018 review cycle 1,
    F-001), and only the round that settles the verdict is ever reported: a
    round abandoned at its node limit has proved nothing about the puzzle, so
    letting its nodes into ADR-0013's score would be measuring the heuristic's
    luck instead of the puzzle's difficulty.
    """

    #: Search nodes expanded — every board this round took off its stack,
    #: whether it went on to guess there, settle it by forced values, or refute
    #: it. ``0`` exactly when line logic alone finished the puzzle.
    branch_nodes: int = 0
    #: Refuted assignments: every tentative cell value propagation ruled out,
    #: which is a subtree the search proved empty without descending into it.
    #: Both values of a cell refuted counts as two, because two assignments
    #: were refuted.
    backtracks: int = 0


@dataclass(frozen=True, slots=True)
class _Pending:
    """A branch not taken yet: assign ``value`` at ``(row, column)`` on ``board``.

    Round 0's laziness in one object (:func:`_descend`). ``board`` is the
    parent at its fixed point, so the assignment and its propagation are
    exactly the work the eager path would have done — deferred, not skipped,
    and paid for only if the search comes back for this branch at all. It
    cannot change a verdict: the sibling is always on the stack beneath its
    partner, so both values of the cell are always explored.
    """

    board: Board
    row: int
    column: int
    value: bool


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
        root: The board at ADR-0029's level-3 fixed point — everything the
            three deduction phases could settle without guessing. Cloned rather
            than mutated, so every round starts from the same place and the
            caller can run this as many times as it likes.
        cache: The solve's line memo. Deliberately *shared* across rounds —
            what a line deduces from a given state does not depend on which
            round asked, so a restart re-treads its predecessor's ground at
            memo speed rather than recomputing it.
        probe_width: How many candidate cells each pass examines, or
            :data:`_NO_PROBE` for round 0's plain one-cell descent.
        node_limit: Give up and return :data:`_CUT_OFF` after this many nodes.
        round_index: 0 for the first round, which follows the branch heuristic
            exactly; later rounds spread their branch choice across the
            candidates the probes found equally live (see :func:`_diversified`).
        counters: Mutated with this round's branch and refutation counts.

    The search writes no rung tags. Everything ADR-0029's ladder can say about
    a clue set was said by the three phases that ran before this one; a
    deduction made *below* a tentative branch is a fact about where the search
    guessed, not about the puzzle (ADR-0029/R5), and a puzzle that got here is
    ``Tier.GUESS`` under ADR-0025 rather than graded on the ladder.

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
    stack: list[Board | _Pending] = [root.clone()]
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
        item = stack.pop()
        nodes += 1
        if isinstance(item, _Pending):
            # Round 0's deferred second value (see :func:`_descend`): the
            # assignment is made and propagated only now, because the search
            # actually came back for it. A contradiction here is the classic
            # backtrack — the subtree is empty and was never entered.
            survived, item = _probe(
                item.board, item.row, item.column, item.value, deadline, cache
            )
            if not survived:
                counters.backtracks += 1
                continue
        board = item
        # FR-009's ``branch_nodes``: one per node this round expands. It is
        # this round's own count, never a running total across the rounds it
        # abandoned (F-001) — ``counters`` is rebuilt per round by
        # :func:`solve`, and only the round that settles the verdict is
        # reported.
        counters.branch_nodes += 1
        outcome = _expand(
            board, cache, probe_width, round_index, nodes, deadline, counters
        )
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
) -> tuple[Board, Board | _Pending | None] | None:
    """Probe one node until it is settled, refuted, or ready to branch.

    Returns:
        ``None`` if the node is refuted — no solution extends this board.
        ``(board, None)`` if probing settled it completely; that board is a
        solution. ``(first, second)`` otherwise: the two branches to explore,
        in the order to explore them.

    The loop is the probing pass described in the module docstring. Each pass
    walks the ``probe_width`` most constrained unknown cells, tries both values
    of each, and acts on the outcome; a pass that forced at least one value
    starts over, because the board it is reasoning about has changed and the
    cells worth probing may have too. A pass that forces nothing has reached
    the limit of what this inference can see, and the node branches.

    Round 0 does not come through here at all: it is :func:`_descend`, the
    plain one-cell guess, and :data:`_SEARCH_ROUNDS` explains why it has to be.

    The soundness of every step here is the argument in the module docstring:
    a contradicting probe rules its value out of *every* solution, so forcing
    the other one — and keeping the propagated board that came with it —
    discards nothing.
    """
    if probe_width == _NO_PROBE:
        return _descend(board, cache, deadline, counters)

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
        forced_a_value = False

        for row, column in _probe_candidates(board, probe_width):
            if board.cell_is_known(row, column):
                # An earlier forced value in this same pass settled it.
                continue
            filled_ok, filled_child = _probe(board, row, column, True, deadline, cache)
            empty_ok, empty_child = _probe(board, row, column, False, deadline, cache)

            if not filled_ok and not empty_ok:
                # Neither value survives, so nothing extends this board. Two
                # assignments were refuted here, and ``backtracks`` counts
                # refuted assignments (F-001).
                counters.backtracks += 2
                return None
            if not filled_ok or not empty_ok:
                # Exactly one survives, so it is not a guess at all: it is a
                # deduction, and the probe already propagated its consequences.
                # The *other* value was refuted, which is the one backtrack.
                counters.backtracks += 1
                survivor = empty_child if not filled_ok else filled_child
                board = survivor
                forced_a_value = True
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

        if forced_a_value:
            continue
        if best is None:
            # A pass that neither forced a value nor found one to branch on,
            # on a board that still has unknown cells, would be the search
            # silently declaring a live node dead — the one shape of bug
            # CON-005 forbids. It is unreachable: the loop returns early when
            # the board is complete, so an incomplete board has an unknown
            # cell; :func:`_probe_candidates` ranks *every* unknown cell before
            # taking its first ``probe_width``, and :func:`_branch_cell` always
            # names one. Left as a loud failure rather than a comment because a
            # candidate ranking that returned nothing would otherwise report
            # "no solutions" for a solvable puzzle — the exact shape CON-005
            # forbids.
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


def _descend(
    board: Board,
    cache: LineCache,
    deadline: float | None,
    counters: _Counters,
) -> tuple[Board, _Pending | None] | None:
    """Round 0's node: guess at one cell, propagating only what is needed.

    The pre-CARD-018 search, restated against this module's node contract. It
    picks the one cell :func:`_branch_cell` names, tries the better-supported
    value, and — if that value survives — hands the *other* value back as a
    :class:`_Pending`, unpropagated, to be paid for only if the search ever
    comes back for it. That laziness is the whole point: a node costs one
    propagation here against a probing node's ``2 * probe_width``.

    Same three outcomes as :func:`_expand`, and sound for the same reason: if
    the first value's propagation contradicts, no solution assigns it, so the
    other value is forced rather than guessed (and if that contradicts too,
    nothing extends this board). Both values are still always reachable.

    Why this round exists at all, and why it uses this ranking rather than the
    probe ranking, is :data:`_SEARCH_ROUNDS`' story: on a massively ambiguous
    board a second solution is a couple of hundred plain nodes away, and
    probing to get there is pure overhead. It is not merely a width choice —
    taking the top *one* cell of the *probe* ranking, on the 20x20 density-10
    request that motivated this split, failed to finish two of that request's
    twenty candidates in 85s and 253s, where this ranking settles every one of
    them in about 30ms.
    """
    total_cells = board.height * board.width
    while True:
        check_deadline(deadline)
        if board.decided == total_cells:
            return board, None

        row, column = _branch_cell(board)
        preferred = _preferred_value(board, cache, row, column)
        survived, child = _probe(board, row, column, preferred, deadline, cache)
        if survived:
            return child, _Pending(board, row, column, not preferred)

        # The preferred value is impossible, so the other one is forced. Not a
        # guess: the same deduction a probing pass would have made.
        counters.backtracks += 1
        survived, child = _probe(board, row, column, not preferred, deadline, cache)
        if not survived:
            counters.backtracks += 1
            return None
        board = child


def _preferred_value(
    board: Board, cache: LineCache, row: int, column: int
) -> bool:
    """Which value of ``(row, column)`` to try first: the better-supported one.

    "Support" is the product of the placements the cell's row still admits and
    the placements its column still admits, once the cell is forced that way —
    the exact fraction of the two lines' surviving placements that agree with
    the value. Both values are always explored, so this only decides which
    subtree is entered first, but on an under-constrained grid it decides it
    well, because following it is following the puzzle's own bias.
    """
    column_bit = 1 << column
    row_bit = 1 << row
    filled_support = _support(
        cache, cache.rows[row], board.row_clues[row], board.width,
        board.row_filled[row] | column_bit, board.row_empty[row],
    ) * _support(
        cache, cache.columns[column], board.column_clues[column], board.height,
        board.column_filled[column] | row_bit, board.column_empty[column],
    )
    empty_support = _support(
        cache, cache.rows[row], board.row_clues[row], board.width,
        board.row_filled[row], board.row_empty[row] | column_bit,
    ) * _support(
        cache, cache.columns[column], board.column_clues[column], board.height,
        board.column_filled[column], board.column_empty[column] | row_bit,
    )
    return filled_support >= empty_support


def _branch_cell(board: Board) -> tuple[int, int]:
    """The most constrained unknown cell: ``(row, column)`` (ADR-0009).

    "Most constrained" is measured by how many placements a line still admits,
    not by how many of its cells are unknown. Placement count is the line's
    actual remaining freedom: a 50-cell line with twenty unknown cells but only
    two possible placements is one guess away from being settled, while a line
    with four unknown cells and six placements is not. Propagation already
    computed and cached those counts, so the heuristic is a scan of two int
    lists rather than a re-run of the line DP.

    The cell chosen is the intersection of the least-free line with the
    least-free perpendicular line through it — so both of the lines a guess
    triggers propagation on are near-forced, which is what makes a wrong guess
    surface as a contradiction immediately instead of hundreds of levels deep.

    Ties break toward the lowest index, keeping the choice deterministic and
    the whole solve reproducible for a given clue set.

    Both orientations are considered, because a nearly-forced column constrains
    a cell exactly as much as a nearly-forced row does.

    Raises:
        RuntimeError: the board has no unknown cell. The caller checks for
            completion before asking, so this is a solver defect, not an
            outcome — and it is the same "nothing to branch on" shape
            :func:`_expand` refuses to treat as "no solutions".
    """
    best_freedom = -1
    best_is_row = True
    best_index = -1

    for row in range(board.height):
        if board.width == (board.row_filled[row] | board.row_empty[row]).bit_count():
            continue  # fully decided: nothing here to branch on
        freedom = board.row_placements[row]
        if best_index < 0 or freedom < best_freedom:
            best_freedom = freedom
            best_is_row = True
            best_index = row
    for column in range(board.width):
        decided = (board.column_filled[column] | board.column_empty[column]).bit_count()
        if board.height == decided:
            continue
        freedom = board.column_placements[column]
        if best_index < 0 or freedom < best_freedom:
            best_freedom = freedom
            best_is_row = False
            best_index = column

    if best_index < 0:  # pragma: no cover - the caller checks for completion
        raise RuntimeError("no unknown cell to branch on: the board is complete")

    if best_is_row:
        unknown_bits = ~(board.row_filled[best_index] | board.row_empty[best_index])
        best_cell = -1
        best_cross = -1
        for column in range(board.width):
            if not (unknown_bits >> column) & 1:
                continue
            cross = board.column_placements[column]
            if best_cell < 0 or cross < best_cross:
                best_cell = column
                best_cross = cross
        return best_index, best_cell

    unknown_bits = ~(board.column_filled[best_index] | board.column_empty[best_index])
    best_cell = -1
    best_cross = -1
    for row in range(board.height):
        if not (unknown_bits >> row) & 1:
            continue
        cross = board.row_placements[row]
        if best_cell < 0 or cross < best_cross:
            best_cell = row
            best_cross = cross
    return best_cell, best_index


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



def _undecided_mask(board: Board) -> Grid:
    """FR-024's mask: which cells this board still leaves open, grid-shaped.

    Read off the *first* fixed point's masks, at the one seam ADR-0012 allows
    the bitmasks to be converted at, and in the same boundary type
    (``list[list[bool]]``) as a solution grid — the int pair itself never
    leaves the package in either direction (guardrail G-3).
    """
    return [
        [
            not ((board.row_filled[row] | board.row_empty[row]) >> column) & 1
            for column in range(board.width)
        ]
        for row in range(board.height)
    ]


def _lookahead(
    board: Board,
    row: int,
    column: int,
    value: bool,
    deadline: float | None,
    cache: LineCache,
) -> tuple[bool, Board]:
    """:func:`_probe`, for ADR-0029's level 3 rather than for the search.

    Byte for byte the same operation — assign on a clone, propagate the two
    lines through the cell, report whether the board survived — and it is a
    separate function on purpose, not by oversight. ``_probe`` is the search's
    unit of work: ``backtracks`` counts its refusals, and
    ``tests/test_solver.py`` spies on it to check that the signals describe the
    *deciding round* and nothing else. Level 3 runs before any round exists, so
    routing its lookahead through the same name would either mis-attribute its
    refutations to a round or, under that spy, to no round at all.
    """
    child = board.clone()
    child.assign(row, column, value)
    dirty_rows = [False] * board.height
    dirty_columns = [False] * board.width
    dirty_rows[row] = True
    dirty_columns[column] = True
    return propagate(child, dirty_rows, dirty_columns, deadline, cache), child


def _probe_fixed_point(
    board: Board,
    cache: LineCache,
    deadline: float | None,
    tags: RungTags,
) -> tuple[Board, bool]:
    """ADR-0029 level 3: refuted probes, to a fixed point.

    Every still-unknown cell is tried with both values. A value whose
    propagation contradicts cannot appear in any solution, so the other one is
    forced — and applied for real, cascade and all — and the pass starts over.
    A full pass that forces nothing *is* the fixed point, which is the
    definition the ADR gives and the one this loop implements literally: no
    cap, no budget, no width limit and no ordering heuristic, because any of
    those would make which cell got which rung a fact about the solver rather
    than about the clue set (ADR-0029/R5, ADR-0029/R1).

    Order-independence is not an accident of the traversal either. The rule is
    monotone — a board that knows more refutes at least as much — and every
    application is sound, so the closure is the same whichever fair order the
    cells are visited in. Row-major here, mirrored under transposition, and the
    same set of cells at the end.

    Args:
        board: Line logic's fixed point (levels 1 and 2). Never mutated: each
            forced value replaces it with the probe's own propagated child.
        tags: Mutated in place — every cell this phase settles is tagged
            ``probe_contradiction``, by diffing the phase's end state against
            its start rather than by watching individual deductions, since a
            deduction's cascade is exactly the part that is order-sensitive.

    Returns:
        ``(board, contradicted)``. ``contradicted`` is ``True`` when some cell
        had *both* values refuted, which proves no solution extends the board
        at all. The verdict is then left to the search rather than reported
        here: ``branch_nodes`` and ``backtracks`` are the search's account of
        its own work, and a zero-solution clue set that reported neither would
        be claiming line logic had settled it. The board returned in that case
        is the last consistent one, which is what the search starts from.
    """
    height = board.height
    width = board.width
    total_cells = height * width
    before_filled = board.row_filled.copy()
    before_empty = board.row_empty.copy()

    contradicted = False
    changed = True
    while changed and board.decided < total_cells:
        check_deadline(deadline)
        changed = False
        unknown = [
            (row, column)
            for row in range(height)
            for column in range(width)
            if not board.cell_is_known(row, column)
        ]
        for row, column in unknown:
            if board.cell_is_known(row, column):
                # An earlier forced value in this same pass settled it.
                continue
            filled_ok, filled_child = _lookahead(board, row, column, True, deadline, cache)
            empty_ok, empty_child = _lookahead(board, row, column, False, deadline, cache)
            if not filled_ok and not empty_ok:
                contradicted = True
                break
            if filled_ok and empty_ok:
                continue
            board = filled_child if filled_ok else empty_child
            changed = True
            if board.decided == total_cells:
                break
        if contradicted:
            break

    for row in range(height):
        bits = (board.row_filled[row] | board.row_empty[row]) & ~(
            before_filled[row] | before_empty[row]
        )
        line = tags[row]
        while bits:
            column = (bits & -bits).bit_length() - 1
            bits &= bits - 1
            line[column] = RUNG_PROBE_CONTRADICTION
    return board, contradicted


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
