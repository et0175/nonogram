"""COMP-006 (Difficulty Scoring) — FR-009 / ADR-0013: five signals, one score.

The one question this module answers: *how hard was this puzzle to solve?* —
as a single number on a fixed 0..100 scale, where 0 is "fell out of line logic
with no guessing at all" and 100 is "the search fought for every cell".

A pure function module (ADR-0007, card guardrail): no I/O, no clock, no
randomness, no module state, and — the important one — **no solver re-entry**.
Everything it needs has already been measured by the one solve that produced
the candidate; scoring never runs the search again. CARD-010's resample loop
calls :func:`score_difficulty` once per candidate, so a scorer that solved
again would double the cost of every generation.

Why the signals arrive by protocol, not by import
-------------------------------------------------
:class:`SolverSignals` is a structural :class:`~typing.Protocol`, and
``nonogram.solver.SolveSignals`` satisfies it as-is — pass ``result.signals``
straight in. It is a protocol rather than an import because ADR-0007 forbids
lateral imports between capability modules and ``solver`` is a sibling
capability, not a shared kernel (``tests/test_cli.py`` enforces that on every
module in the package). The dependency runs the other way round: the
orchestrator holds both and hands one to the other.

The formula (ADR-0013)
----------------------
Three of FR-009's five signals measure *effort* — how much work the solve
actually cost — and are combined by the fixed-weight sum ADR-0013 adopts:

    effort = W.line_logic  * (1 - line-logic coverage)
           + W.backtracking * (branch nodes / total cells, capped at 1)
           + W.solve_time   * (elapsed / a size-relative time budget, capped)

The other two — size and clue density — are *normalizers*, not difficulty in
their own right, exactly as ADR-0013 requires ("size and density act as
NORMALIZERS on the other signals rather than as independent additive terms in
their own right"). Size is already inside the first three terms as their
denominator; on top of that, the two of them scale the effort score by a
bounded relief factor, so a structurally easy shape (small, or lopsidedly
sparse/dense) discounts the effort it took, and a structurally hard one
(large, mid-density) does not:

    relief = 1 - W.size * (1 - size pressure) - W.density * (1 - density pressure)
    score  = 100 * effort * relief

Both readings of ADR-0013 are honoured by that shape, and they are what pins
it down between them: all five signals are in the score with fixed weights
from one named, tunable table (AC-022), and size and density enter only
multiplicatively — never as additive terms of their own — which is what makes
AC-023 true *by construction* rather than by tuning:

    A puzzle solved entirely by line logic with zero backtracking has
    line-logic gap 0 and branch pressure 0, so its effort is at most
    ``W.solve_time`` and its score at most ``100 * W.solve_time`` — no matter
    how big it is, how dense it is, or how the relief factor comes out, since
    relief only ever multiplies a number that is already near zero.

With the weights below that ceiling is 15 points on a 100-point scale, i.e.
such a puzzle cannot leave the easiest band of the scale (ADR-0005 puts the
Easy cutoff at 33) even on a machine slow enough to burn its whole solve-time
budget on a single propagation sweep. In practice a line-logic-only solve
finishes in a thousandth of that budget and scores a small fraction of a
point.

The bands drawn on that scale (ADR-0005)
----------------------------------------
:class:`Tier` and :func:`tier_for_score` split the same 0..100 range into
ADR-0005's three equal bands — Easy ``[0, 33]``, Medium ``(33, 66]``, Hard
``(66, 100]`` — from the two named cutoffs :data:`EASY_MAX_SCORE` and
:data:`MEDIUM_MAX_SCORE`. They live here rather than in the orchestrator for
the reason ADR-0005 gives: cutoffs and weights are one tuning surface, and the
resample loop, the CLI and Increment 2's tertile checkpoint all have to agree
on which band a score is in. :func:`parse_tier` is the same module's answer to
"is ``--difficulty extreme`` a tier?" (AC-021) — a domain rule, kept out of
argparse (ADR-0010).

Guardrail G-5 / CON-004: this is a heuristic classifier of candidates the
generator already produced. Nothing here shapes a grid, and nothing here is a
promise about a puzzle's solving experience.

Usage::

    from nonogram.clues import compute_clues
    from nonogram.difficulty import score_difficulty
    from nonogram.solver import solve

    clues = compute_clues(grid)
    result = solve(*clues)
    if result.is_unique:
        score = score_difficulty(result.signals, clues.rows)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from nonogram.errors import UnsupportedDifficulty

__all__ = [
    "EASY_MAX_SCORE",
    "MAX_SUPPORTED_CELLS",
    "MEDIUM_MAX_SCORE",
    "MIN_SUPPORTED_CELLS",
    "NormalizedSignals",
    "SCORE_MAX",
    "SCORE_MIN",
    "SIGNAL_WEIGHTS",
    "SignalWeights",
    "SolverSignals",
    "TIER_BANDS",
    "Tier",
    "clue_density",
    "normalize_signals",
    "parse_tier",
    "score_difficulty",
    "tier_for_score",
]

#: One clue tuple per line, in the ADR-0012 boundary type.
ClueSet = tuple[tuple[int, ...], ...]

#: The ends of ADR-0013's fixed scale. Every score lands inside them.
SCORE_MIN = 0.0
SCORE_MAX = 100.0

#: ADR-0005's two tier cutoffs, drawn on the scale above: the 0..100 range is
#: split into three equal-width bands — Easy ``[0, 33]``, Medium ``(33, 66]``,
#: Hard ``(66, 100]``. They live here, next to :data:`SIGNAL_WEIGHTS`, and not
#: in the orchestrator, because ADR-0005 puts cutoffs and weights on the same
#: "tunable later" axis: a retune driven by real score distributions moves both
#: from one place, and there is exactly one answer to "which band is this
#: score in" for the resample loop, the CLI and Increment 2's tertile
#: checkpoint to share (CARD-010 point 2).
#:
#: Provisional by ADR-0005's own admission — an equal split is "divide by
#: three", not calibration — which is why they are named constants a developer
#: can move rather than a threshold recomputed per run: resample behaviour has
#: to be the same on the same inputs from one run to the next.
EASY_MAX_SCORE = 33.0
MEDIUM_MAX_SCORE = 66.0


class Tier(StrEnum):
    """FR-008's user-facing difficulty selector: Easy, Medium or Hard.

    A :class:`~enum.StrEnum` so the tier *is* its ``--difficulty`` spelling —
    the value a user types, an export payload carries and (CARD-014) a PDF
    filename is built from are one string, with no lookup table between them.
    The capitalized form AC-020 uses for display is :attr:`label`.

    The members carry no thresholds of their own: :func:`tier_for_score` is the
    single classifier and :data:`TIER_BANDS` the single table, both derived
    from :data:`EASY_MAX_SCORE`/:data:`MEDIUM_MAX_SCORE`, so a retune cannot
    move a band without moving the classification with it.

    CON-004 / guardrail G-3: a tier is a bucket a *scored* candidate fell into,
    never a construction target. Asking for ``Tier.EASY`` makes the pipeline
    discard candidates that scored outside the Easy band (POL-004); it does not
    steer a grid toward being easy, and it promises nothing about how the
    puzzle feels to solve.
    """

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    @property
    def label(self) -> str:
        """The tier as AC-020 writes it — ``"Medium"``, not ``"medium"``."""
        return self.value.capitalize()

    @property
    def band(self) -> tuple[float, float]:
        """This tier's ``(low, high)`` score band (ADR-0005).

        Half-open at the bottom and closed at the top — ``low < score <= high``
        — except :attr:`EASY`, whose band includes :data:`SCORE_MIN` itself.
        :meth:`contains` is what a caller should ask; this is for reporting the
        band and for tests that need to see where it sits.
        """
        return TIER_BANDS[self]

    def contains(self, score: float) -> bool:
        """Does ``score`` fall in this tier's band? (POL-004's condition.)

        Asked through :func:`tier_for_score` rather than by comparing against
        :attr:`band` a second time, so "which tier is this score" and "is this
        score in that tier" cannot disagree at a boundary.
        """
        return tier_for_score(score) is self


#: Each tier's ``(low, high)`` band, derived from the two cutoffs above rather
#: than written out as four numbers — see :meth:`Tier.band` for the open/closed
#: ends. Read-only: the bands are a fact about :data:`EASY_MAX_SCORE` and
#: :data:`MEDIUM_MAX_SCORE`, so the supported way to move one is to move a
#: cutoff.
TIER_BANDS: Mapping[Tier, tuple[float, float]] = MappingProxyType(
    {
        Tier.EASY: (SCORE_MIN, EASY_MAX_SCORE),
        Tier.MEDIUM: (EASY_MAX_SCORE, MEDIUM_MAX_SCORE),
        Tier.HARD: (MEDIUM_MAX_SCORE, SCORE_MAX),
    }
)


def tier_for_score(score: float) -> Tier:
    """Which tier a score falls in (ADR-0005).

    Total on the whole real line, not just on 0..100: a score below
    :data:`SCORE_MIN` reads as Easy and one above :data:`SCORE_MAX` as Hard.
    :func:`score_difficulty` cannot produce either, and a classifier that
    raised on them would only turn a scale bug into a crash at the point
    furthest from its cause.

    The cutoffs belong to the *lower* band (``33.0`` is Easy, ``66.0`` is
    Medium), which is ADR-0005's ``Easy = [0, 33], Medium = (33, 66],
    Hard = (66, 100]`` read literally.
    """
    if score <= EASY_MAX_SCORE:
        return Tier.EASY
    if score <= MEDIUM_MAX_SCORE:
        return Tier.MEDIUM
    return Tier.HARD


def parse_tier(text: str) -> Tier:
    """Resolve what the user typed into a :class:`Tier` (FR-008, AC-021).

    The domain-side check ``--difficulty`` deliberately does not do in argparse
    (ADR-0010, guardrail G-4): which tiers exist is a domain rule, so a
    misspelled tier reaches this function as an ordinary string and leaves it
    as a :class:`~nonogram.errors.NonogramError` the CLI maps to an exit code —
    not as an argparse usage error.

    Surrounding whitespace and case are not part of the rule: ``"Medium"`` is
    AC-020's own spelling of the tier whose flag value is ``medium``, and
    refusing it would be pedantry rather than validation.

    Raises:
        UnsupportedDifficulty: ``text`` names no supported tier (AC-021). The
            message lists the three that exist, since the user's next move is
            to pick one of them.
    """
    try:
        return Tier(text.strip().lower())
    except ValueError:
        supported = ", ".join(tier.value for tier in Tier)
        raise UnsupportedDifficulty(
            f"unsupported difficulty tier {text!r}; supported tiers are: {supported}"
        ) from None

#: The supported grid range (docs/requirements.md decision 6: 10x10..50x50), in
#: cells — the denominators the size normalizer stretches between. A grid
#: outside the range clamps rather than raising: an out-of-size puzzle is an
#: input-validation matter for COMP-002, and a scorer is the wrong place to
#: discover it.
MIN_SUPPORTED_CELLS = 10 * 10
MAX_SUPPORTED_CELLS = 50 * 50

#: The density at which a grid is hardest to solve, and so where the density
#: normalizer peaks. ADR-0013: "both very sparse and very dense grids tend to
#: be easier," so difficulty is measured as *nearness* to this midpoint.
HARDEST_DENSITY = 0.5

#: The size-relative wall-clock budget one cell is worth, in seconds — the
#: denominator that turns an absolute elapsed time into a 0..1 signal.
#: Derived from NFR-001/ADR-0001's 5-second p95 cap for grids up to 20x20:
#: 5s / 400 cells. A solve that spends its whole size-scaled budget scores the
#: term at 1.0; the usual sub-second solve scores a small fraction of it.
SECONDS_PER_CELL_BUDGET = 5.0 / (20 * 20)


@dataclass(frozen=True, slots=True)
class SignalWeights:
    """ADR-0013's tunable weight table — the whole calibration surface.

    One named constant set, deliberately separate from the solver, because
    FR-010 requires the difficulty estimate to be "tunable later without
    changing the solver" and ADR-0013 expects these numbers to be recalibrated
    once real score distributions exist. Retuning this table is the supported
    way to move the scale; editing the formula is not.

    The three effort weights sum to 1.0, which is what keeps the score inside
    0..100, and the two normalizer weights sum to at most 1.0, which is what
    keeps the relief factor positive — so scaling can only ever discount an
    effort score, never invert or erase it. Both are checked on construction
    rather than left as a comment, because a retune that quietly broke either
    one would not fail anywhere else: it would just silently move the scale
    that ADR-0005's tier cutoffs are drawn on.
    """

    #: Weight of the cells line logic could *not* settle before the first guess.
    line_logic: float
    #: Weight of the branch count, relative to the grid's own cell count.
    backtracking: float
    #: Weight of wall-clock time, relative to the grid's own time budget.
    solve_time: float
    #: How much of the score a minimum-size grid is relieved of.
    size: float
    #: How much of the score a fully sparse or fully dense grid is relieved of.
    density: float

    def __post_init__(self) -> None:
        effort = self.line_logic + self.backtracking + self.solve_time
        if abs(effort - 1.0) > 1e-9:
            raise ValueError(
                "the three effort weights (line_logic, backtracking, "
                f"solve_time) must sum to 1.0 to keep the score within "
                f"{SCORE_MIN}..{SCORE_MAX}; got {effort}"
            )
        if min(self.size, self.density) < 0.0 or self.size + self.density > 1.0:
            raise ValueError(
                "the normalizer weights (size, density) must be non-negative "
                "and sum to at most 1.0 so that size and density can only "
                f"discount an effort score; got {self.size} + {self.density}"
            )


#: The weights in force. Provisional by ADR-0013's own admission ("the weights
#: are guesses until real score distributions are observed"): backtracking
#: leads, because needing a guess at all is the thing that makes a nonogram
#: feel hard, but not by so much that the common zero-branch puzzle loses all
#: differentiation — which is exactly why ADR-0013 rejected the
#: backtracking-dominant alternative. Wall-clock time is kept in the score as
#: FR-009 lists it, but weighted lightest of the three, because it is the only
#: signal that varies with the machine rather than with the puzzle.
SIGNAL_WEIGHTS = SignalWeights(
    line_logic=0.40,
    backtracking=0.45,
    solve_time=0.15,
    size=0.15,
    density=0.15,
)


class SolverSignals(Protocol):
    """The solver telemetry this module scores (FR-009, ADR-0009).

    Structural, so ``nonogram.solver.SolveSignals`` satisfies it without
    either module importing the other (see the module docstring on ADR-0007).
    Read-only members, because a scorer has no business writing to what it was
    handed.

    ``backtracks`` is deliberately *not* part of this protocol even though the
    solver reports it: ADR-0013 names branch nodes as the backtracking-amount
    term, and counting dead-end guesses a second time alongside them would
    weight the same phenomenon twice.
    """

    @property
    def line_logic_cells(self) -> int:
        """Cells settled by line logic alone, before the first guess."""

    @property
    def total_cells(self) -> int:
        """Cells in the grid — ADR-0013's size-relative denominator."""

    @property
    def branch_nodes(self) -> int:
        """Search nodes the solver had to expand past line logic.

        Before CARD-018 this read "guesses the search had to make because
        propagation stalled", and the two were the same number, because
        guessing was all a node could do. CARD-018's probing gave a node two
        further outcomes — deduce, and refute — so the count is now over the
        nodes expanded rather than the guesses alone (ADR-0013, History
        2026-08-30). It is still ``0`` exactly when line logic alone finished
        the puzzle, which is what AC-023's easy anchor rests on, and it still
        grows with how much the search had to do, which is what the weight is
        for.
        """

    @property
    def elapsed_seconds(self) -> float:
        """Wall-clock seconds the whole solve took."""


@dataclass(frozen=True, slots=True)
class NormalizedSignals:
    """FR-009's five signals, each mapped onto 0..1 (ADR-0013).

    Every member reads in the same direction — *larger means harder* — which
    is what lets :func:`score_difficulty` be a plain weighted combination with
    no sign juggling, and what makes the AC-023 anchor legible: the two terms
    that dominate the score are both exactly 0 for a puzzle that never needed
    a guess.

    Exposed (rather than kept inside the scoring function) because a single
    score is opaque when a puzzle lands in an unexpected band, and the resample
    loop's diagnostics, tuning work on :data:`SIGNAL_WEIGHTS`, and this card's
    own monotonicity tests all need to see which term moved.
    """

    #: Cells line logic could *not* settle, as a fraction of the grid: 0.0 when
    #: the puzzle needed no guess at all, 1.0 when line logic settled nothing.
    line_logic_gap: float
    #: Branch nodes per cell, capped at 1.0 — the grid's own size is the
    #: denominator, so a big puzzle is not "hard" for being big.
    branch_pressure: float
    #: Elapsed time against the grid's size-scaled budget, capped at 1.0.
    time_pressure: float
    #: Where the grid sits in the supported 10x10..50x50 range: 0.0 at the
    #: smallest supported grid, 1.0 at the largest.
    size_pressure: float
    #: Nearness to the hardest density: 1.0 at :data:`HARDEST_DENSITY`, 0.0 at
    #: a wholly empty or wholly filled grid.
    density_pressure: float


def clue_density(clues: ClueSet, total_cells: int) -> float:
    """The fraction of the grid a clue set says is filled, in 0..1.

    Computed here rather than plumbed through the solver because it is not a
    solver-internal signal at all: it is a property of the clues the caller
    already holds, and reading it off them keeps COMP-005's reporting surface
    to the things only the search knows.

    Either orientation may be passed — the row clues and the column clues of
    one grid encode the same filled cells, so they give the same density. The
    ``(0,)`` empty-line marker (AC-013) contributes 0 and needs no special
    case.

    A grid with no cells has no density; 0.0 is returned rather than raising,
    and :func:`normalize_signals` never lets that value reach the score.
    """
    if total_cells <= 0:
        return 0.0
    filled = sum(sum(clue) for clue in clues)
    return _clamp(filled / total_cells, 0.0, 1.0)


def normalize_signals(signals: SolverSignals, clues: ClueSet) -> NormalizedSignals:
    """Map FR-009's five raw signals onto ADR-0013's 0..1 scales.

    Args:
        signals: What the one solve of this candidate measured — pass
            ``SolveResult.signals`` straight in.
        clues: The candidate's clues, in either orientation, for the density
            normalizer (see :func:`clue_density`).

    Returns:
        The five :class:`NormalizedSignals`, each in 0..1 and each reading
        larger-means-harder.

    Every ratio is clamped, so a signal outside its expected range (a solve
    timed at a negative delta by a clock adjustment, a grid outside the
    supported size range, a branch count that exceeds the cell count on a
    pathological puzzle) bends the score toward an end of the scale instead of
    pushing it off the scale entirely. An empty grid normalizes to all-zero:
    there is nothing to solve, so there is no difficulty to report.
    """
    total_cells = signals.total_cells
    if total_cells <= 0:
        return NormalizedSignals(0.0, 0.0, 0.0, 0.0, 0.0)

    coverage = _clamp(signals.line_logic_cells / total_cells, 0.0, 1.0)
    time_budget = SECONDS_PER_CELL_BUDGET * total_cells
    density = clue_density(clues, total_cells)
    size_span = MAX_SUPPORTED_CELLS - MIN_SUPPORTED_CELLS

    return NormalizedSignals(
        line_logic_gap=1.0 - coverage,
        branch_pressure=_clamp(signals.branch_nodes / total_cells, 0.0, 1.0),
        time_pressure=_clamp(signals.elapsed_seconds / time_budget, 0.0, 1.0),
        size_pressure=_clamp((total_cells - MIN_SUPPORTED_CELLS) / size_span, 0.0, 1.0),
        # Distance from the hardest midpoint, re-read as nearness to it: at
        # HARDEST_DENSITY the distance is 0 and the term peaks at 1.0; at
        # either extreme the distance is 0.5 — the largest it can be — and the
        # term bottoms out at 0.0.
        density_pressure=_clamp(
            1.0 - abs(density - HARDEST_DENSITY) / HARDEST_DENSITY, 0.0, 1.0
        ),
    )


def score_difficulty(
    signals: SolverSignals,
    clues: ClueSet,
    *,
    weights: SignalWeights = SIGNAL_WEIGHTS,
) -> float:
    """Score one solved candidate on ADR-0013's 0..100 scale (FR-009, AC-022).

    Args:
        signals: The solver telemetry for this candidate — pass
            ``SolveResult.signals``. Only the one solve that already happened
            is used; the search is never re-entered.
        clues: The candidate's clues, in either orientation, for the density
            normalizer.
        weights: The weight table to score with. Defaults to
            :data:`SIGNAL_WEIGHTS`; keyword-only and injectable so tuning
            experiments and tests can vary the calibration without reaching
            into module state, which there is none of.

    Returns:
        A single float in :data:`SCORE_MIN`..:data:`SCORE_MAX`, larger meaning
        harder. Not rounded and not bucketed: the tiers ADR-0005 draws on this
        scale are CARD-010's, and rounding here would only lose information
        the resample loop's comparisons might want.

    Pure and total: no I/O, no clock, no randomness, no solver re-entry, and no
    input it refuses. It does not check that the candidate was *uniquely*
    solvable — that is INV-002's gate and the caller's to apply before it gets
    here — so the signals of a non-unique or unsolvable clue set score without
    complaint, and the number means nothing in that case.

    AC-023 holds structurally, not by calibration: a candidate solved entirely
    by line logic with zero backtracking zeroes both of the terms that carry
    ``1 - weights.solve_time`` of the scale between them, so its score cannot
    exceed ``SCORE_MAX * weights.solve_time`` whatever its size and density do
    to the relief factor. See the module docstring.
    """
    normalized = normalize_signals(signals, clues)

    effort = (
        weights.line_logic * normalized.line_logic_gap
        + weights.backtracking * normalized.branch_pressure
        + weights.solve_time * normalized.time_pressure
    )
    # Size and density never add to the score — they only ever discount it,
    # which is what keeps a large easy puzzle from out-scoring a small hard
    # one on cell count alone (ADR-0013) and what leaves AC-023's anchor at
    # zero regardless of either.
    relief = (
        1.0
        - weights.size * (1.0 - normalized.size_pressure)
        - weights.density * (1.0 - normalized.density_pressure)
    )

    return _clamp(SCORE_MAX * effort * relief, SCORE_MIN, SCORE_MAX)


def _clamp(value: float, low: float, high: float) -> float:
    """``value`` confined to ``low..high``."""
    return low if value < low else high if value > high else value
