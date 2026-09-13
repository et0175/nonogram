"""COMP-006 (Difficulty Scoring) — FR-026 / ADR-0029: one ladder, one classifier.

The one question this module answers: *what kind of reasoning did this puzzle
demand?* — as a tier, and as a single number on the fixed 0..100 scale the
export, the DB column and POL-004's resample predicate have always carried.

A pure function module (ADR-0007, guardrail G-1/G-3): no I/O, **no clock**, no
randomness, no module state, and — the important one — **no solver re-entry**.
Everything it needs has already been measured by the one solve that produced
the candidate; scoring never runs the search again. The resample loop calls
:func:`score_difficulty` once per candidate, so a scorer that solved again
would double the cost of every generation.

The ladder (ADR-0029)
---------------------
The solve settles the grid in three stratified fixed points, each running its
technique to exhaustion on the board the previous one left, and tags every
settled cell with the rung it was settled at:

    simple_overlap  <  line_dp  <  probe_contradiction

A puzzle's difficulty is the **hardest rung its one verifying solve needed**.
Within a rung, puzzles are ordered by ADR-0029's secondary count: the share of
the grid that rung settled. The 0..100 number is a derived *presentation* of
that pair, not the grade itself::

    rung  = the hardest rung with at least one cell settled at it
    share = rung_cells[rung] / total_cells
    score = band_low(rung) + share * band_width(rung)

Monotone propagation is confluent, so the set of cells a rung settles is a
function of the clue set alone — which is what makes the grade a fact about
the puzzle rather than about how the solver walked the grid (ADR-0029/R5).

Where the band edges come from, and why they are not thirds
----------------------------------------------------------
The three bands' edges **are** ADR-0005's two cutoff constants:
``simple_overlap`` 0..33, ``line_dp`` 33..66, ``probe_contradiction`` 66..100
(widths 33, 33, 34). Idealised thirds do not work, and the failure is not
cosmetic: a puzzle that tops out at ``simple_overlap`` has *every* settled cell
at that rung by definition, so its share is exactly ``1.0`` (measured 1.000 in
420 of 420 line-solvable grids). At a band width of 33.33 that scores 33.33 —
above :data:`EASY_MAX_SCORE` — so every Easy puzzle would classify Medium and
the Easy band would be empty (ADR-0029, History 2026-09-13).

With the edges *on* the cutoffs the arithmetic lands where ADR-0029 says it
should, because the cutoffs are inclusive upper bounds:

* a full-share bottom rung scores exactly ``33.0`` and classifies **Easy**;
* a higher rung is "present" only if it settled at least one cell, so its
  share is strictly positive and its score strictly above its band's lower
  edge — which is what makes ADR-0029/R1's cross-rung monotonicity hold by
  construction rather than by calibration.

One consequence is worth naming rather than hiding: **Easy is a single point
on the scale.** Every puzzle that never leaves overlap scores exactly 33.0, so
the within-rung ordering ADR-0005's owed recalibration is waiting on does not
exist inside the bottom band. That is input for the calibration, not a defect
of the mapping — see CARD-076's Worktree notes for the measured distribution.

The fourth tier (ADR-0025)
--------------------------
:class:`Tier` has four members, and only three of them are score bands.
``Tier.GUESS`` is keyed on a *fact about the solve* — ``branch_nodes > 0`` —
never on a threshold (EC-015). So a score alone can no longer classify a
result: :func:`classify` is the single classifier and it takes
``(score, branch_nodes)``, applying EC-015 first and the bands only to the
remainder (ADR-0025/R1, R2). ``Tier.EASY``/``MEDIUM``/``HARD`` therefore
contain only line-solvable puzzles, which is what makes ``--difficulty hard``
promise "logically solvable, and deep" — the printed-book workflow in one
word.

There is exactly one implementation of that rule, here. No other module under
``src/nonogram/`` compares a score against the cutoffs or reads
``branch_nodes`` to decide a tier; ``tests/test_difficulty_tiers.py`` walks the
package with ``ast`` and fails if one starts to.

No clock, no size, no density (NFR-007, CON-014, ADR-0029/R3)
-------------------------------------------------------------
``elapsed_seconds`` is not a member of :class:`SolverSignals` at all. That is
deliberate and structural: the scorer cannot read a clock it was never handed,
so EC-016 ("two signal records differing only in elapsed time score
identically") holds by the shape of the protocol rather than by discipline.
Size and density are gone with it — a rung is not effort, and a 30x30 that
never leaves simple overlap is exactly as Easy as a 10x10 that never does. The
only place an extent appears is as the denominator of the within-rung share.

Retired with ADR-0013: ``SignalWeights``, ``SIGNAL_WEIGHTS``,
``NormalizedSignals``, ``normalize_signals``, ``clue_density``,
``SECONDS_PER_CELL_BUDGET``, ``HARDEST_DENSITY``, ``MIN_SUPPORTED_CELLS``,
``MAX_SUPPORTED_CELLS``, and the public ``tier_for_score``.

Why the signals arrive by protocol, not by import
-------------------------------------------------
:class:`SolverSignals` is a structural :class:`~typing.Protocol`, and
``nonogram.solver.SolveSignals`` satisfies it as-is — pass ``result.signals``
straight in. It is a protocol rather than an import because ADR-0007 forbids
lateral imports between capability modules and ``solver`` is a sibling
capability, not a shared kernel (``tests/test_cli.py`` enforces that on every
module in the package). The dependency runs the other way round: the
orchestrator holds both and hands one to the other.

The same rule is why the three rung names are spelled out here instead of
imported from ``nonogram.solver``. This is the precedent ``propagate.py``'s
``mask_runs`` already set — reimplement natively across a boundary ADR-0007
closes, and cross-check from the test tree, where the import is legal
(``tests/test_difficulty.py`` pins :data:`LADDER` against
``solver.RUNG_ORDER``).

CON-004: this is a classifier of candidates the generator already produced.
Nothing here shapes a grid, and nothing here is a promise about how a puzzle
feels to solve.

Usage::

    from nonogram.clues import compute_clues
    from nonogram.difficulty import classify, score_difficulty
    from nonogram.solver import solve

    clues = compute_clues(grid)
    result = solve(*clues)
    if result.solution_count == 1:
        score = score_difficulty(result.signals)
        tier = classify(score, result.signals.branch_nodes)
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from nonogram.errors import UnsupportedDifficulty

__all__ = [
    "EASY_MAX_SCORE",
    "LADDER",
    "MEDIUM_MAX_SCORE",
    "RUNG_BANDS",
    "RUNG_LINE_DP",
    "RUNG_PROBE_CONTRADICTION",
    "RUNG_SIMPLE_OVERLAP",
    "SCORE_MAX",
    "SCORE_MIN",
    "SolverSignals",
    "TIER_BANDS",
    "Tier",
    "classify",
    "hardest_rung",
    "parse_tier",
    "score_difficulty",
    "tier_of_record",
]

#: The ends of the fixed scale (carried forward from ADR-0013, which is one of
#: the two things about it ADR-0029 kept). Every score lands inside them.
SCORE_MIN = 0.0
SCORE_MAX = 100.0

#: ADR-0005's two tier cutoffs. Unchanged in value by ADR-0029 — which is the
#: point: the ladder was mapped onto *them* rather than the other way round, so
#: no stored grade moves on account of a band edge (CARD-076 guardrail G-5).
#:
#: They are inclusive upper bounds: ``33.0`` is Easy and ``66.0`` is Medium.
#: That is what lets a full-share bottom rung score exactly 33.0 and stay Easy;
#: see the module docstring.
#:
#: Still the single tuning surface ADR-0005 asked for, but what is owed has
#: changed shape. ADR-0029 puts the three rungs *on* these cutoffs, so the
#: tier-per-rung mapping is settled; what remains owed to AC-118's corpus is
#: only whether the within-rung share spreads puzzles usefully inside a band.
#: CARD-076 measured the distribution and deliberately did not retune (G-5).
EASY_MAX_SCORE = 33.0
MEDIUM_MAX_SCORE = 66.0

#: ADR-0029's ladder, lowest rung first. The names are spelled out rather than
#: imported from ``nonogram.solver`` — see the module docstring on ADR-0007 —
#: and are pinned against ``solver.RUNG_ORDER`` from the test tree.
#:
#: ``guess`` is deliberately **not** a rung. A solve that branched is
#: ``Tier.GUESS`` by ADR-0025 and is not graded on this ladder at all.
RUNG_SIMPLE_OVERLAP = "simple_overlap"
RUNG_LINE_DP = "line_dp"
RUNG_PROBE_CONTRADICTION = "probe_contradiction"

#: The ladder as one ordered tuple — the order *is* the grading, so it is a
#: sequence and not a set.
LADDER: tuple[str, ...] = (
    RUNG_SIMPLE_OVERLAP,
    RUNG_LINE_DP,
    RUNG_PROBE_CONTRADICTION,
)


class Tier(StrEnum):
    """FR-008's user-facing difficulty selector: Easy, Medium, Hard or Guess.

    A :class:`~enum.StrEnum` so the tier *is* its ``--difficulty`` spelling —
    the value a user types, an export payload carries and a PDF filename is
    built from are one string, with no lookup table between them. The
    capitalized form AC-020 uses for display is :attr:`label`.

    **Three of the four are score bands; the fourth is not.** :attr:`GUESS` is
    keyed on the solve's ``branch_nodes``, not on a number (ADR-0025/R1,
    EC-015), which is why :func:`classify` takes two arguments and why
    :attr:`band` answers ``None`` for it. Easy, Medium and Hard therefore
    contain only line-solvable puzzles, and ``--difficulty hard`` *is* "deep,
    and never needs a guess".

    ``GUESS``'s measured assignment rate is currently **zero** — no generated
    puzzle in 6,620 (ADR-0029's measurement) or 462 (CARD-076's) required a
    branch after the solve's own one-step lookahead phase. It is kept anyway,
    deliberately: it is the product promise stated as a fact, and a safety net
    for a future source or extent that does produce a branching grid. See
    ADR-0025's History.

    CON-004: a tier is a bucket a *scored* candidate fell into, never a
    construction target. Asking for ``Tier.EASY`` makes the pipeline discard
    candidates that classified elsewhere (POL-004); it does not steer a grid
    toward being easy.
    """

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    GUESS = "guess"

    @property
    def label(self) -> str:
        """The tier as AC-020 writes it — ``"Medium"``, not ``"medium"``.

        Presentational, and ADR-0025 says so explicitly: ``"Guess"`` may be
        renamed (to ``"Expert"``, say) without touching the enum *value*, which
        is what every stored row, export payload and filename depends on.
        """
        return self.value.capitalize()

    @property
    def band(self) -> tuple[float, float] | None:
        """This tier's ``(low, high)`` score band, or ``None`` for :attr:`GUESS`.

        Half-open at the bottom and closed at the top — ``low < score <= high``
        — except :attr:`EASY`, whose band includes :data:`SCORE_MIN` itself.

        ``None`` rather than a fabricated range for :attr:`GUESS`, because it
        does not have one: ADR-0025 breaks ADR-0005's "a tier is a score band"
        model for exactly one member, and a band table that pretended otherwise
        would be the first place somebody re-derived the tier from a number.
        For reporting and for tests that need to see where a band sits;
        :func:`classify` is what a caller should ask.
        """
        return TIER_BANDS.get(self)


#: Each *score-band* tier's ``(low, high)``, derived from the two cutoffs above
#: rather than written out as four numbers — see :meth:`Tier.band` for the
#: open/closed ends. :attr:`Tier.GUESS` is absent by design, not by omission.
#: Read-only: the bands are a fact about :data:`EASY_MAX_SCORE` and
#: :data:`MEDIUM_MAX_SCORE`, so the supported way to move one is to move a
#: cutoff.
TIER_BANDS: Mapping[Tier, tuple[float, float]] = MappingProxyType(
    {
        Tier.EASY: (SCORE_MIN, EASY_MAX_SCORE),
        Tier.MEDIUM: (EASY_MAX_SCORE, MEDIUM_MAX_SCORE),
        Tier.HARD: (MEDIUM_MAX_SCORE, SCORE_MAX),
    }
)

#: The score-band tiers in ladder order — the correspondence ADR-0029 draws
#: between "which rung" and "which band", written once.
_BAND_TIERS: tuple[Tier, ...] = (Tier.EASY, Tier.MEDIUM, Tier.HARD)

#: Each rung's ``(low, high)`` score band — the *same* three bands, read by rung
#: instead of by tier, which is ADR-0029's "the cutoffs now land exactly on rung
#: boundaries" as one table rather than as a comment. Zipped from
#: :data:`TIER_BANDS` rather than restated, so a retune of the cutoffs moves the
#: rungs and the tiers together and the correspondence cannot drift. ``strict``
#: because a ladder and a band list of different lengths is a design change
#: somebody must make on purpose.
RUNG_BANDS: Mapping[str, tuple[float, float]] = MappingProxyType(
    dict(
        zip(
            LADDER,
            (TIER_BANDS[tier] for tier in _BAND_TIERS),
            strict=True,
        )
    )
)


class SolverSignals(Protocol):
    """The solver telemetry this module grades (FR-026, ADR-0029).

    Structural, so ``nonogram.solver.SolveSignals`` satisfies it without
    either module importing the other (see the module docstring on ADR-0007).
    Read-only members, because a scorer has no business writing to what it was
    handed.

    **What is deliberately absent is the contract.** ``elapsed_seconds`` is not
    here, so no term of the score and no input of the tier decision *can* be a
    clock reading: CON-014 and ADR-0029/R3 hold by the shape of this protocol
    rather than by a rule somebody has to remember (EC-016).
    ``line_logic_cells`` is not here either — it survives on ``SolveSignals``
    for NFR-001 reporting but no longer drives anything graded, since the rung
    tags say which technique settled which cell and it does not. Nor is
    ``backtracks``: ``branch_nodes`` already answers the one question EC-015
    asks, and counting refuted assignments beside it would be a second reading
    of the same event.
    """

    @property
    def total_cells(self) -> int:
        """Cells in the grid — the denominator of the within-rung share."""

    @property
    def branch_nodes(self) -> int:
        """Search nodes the solve expanded past the three deduction phases.

        EC-015's whole input: ``> 0`` means the search really had to branch,
        and :func:`classify` answers :attr:`Tier.GUESS` on that fact alone,
        whatever the score. ``0`` exactly when the ladder's three fixed points
        finished the puzzle by themselves.
        """

    @property
    def rung_cells(self) -> Mapping[str, int]:
        """How many cells each :data:`LADDER` rung settled in this solve.

        Carries all three rung names as keys, so this module can index rather
        than ``get``. All-zero for a clue set that is not a puzzle: ADR-0029
        scopes rung attribution to clue sets with exactly one solution, and a
        candidate with 0 or >= 2 solutions has no grade to report (and is
        discarded before it would ever be scored, INV-002/CON-004).
        """


def hardest_rung(rung_cells: Mapping[str, int]) -> str | None:
    """The highest :data:`LADDER` rung that settled at least one cell.

    ADR-0029's grade, before it is turned into a number. ``None`` when nothing
    was settled at any rung — an empty grid, or a clue set that is not a puzzle
    and therefore carries no attribution at all.

    Derived from the counts rather than read off the solver's own ordered
    ``rungs`` list, deliberately: the two are the same fact twice, and
    re-deriving it here from the one input the score already needs makes a
    disagreement between them a test failure rather than a silent regrade.

    A rung name this module does not know is ignored rather than raising. The
    ladder is ADR-0029's design choice, and a solver that grew a fourth rung
    would be a decision to take, not a crash to discover at the scorer.
    """
    present = [rung for rung in LADDER if rung_cells.get(rung, 0) > 0]
    return present[-1] if present else None


def score_difficulty(signals: SolverSignals) -> float:
    """Score one solved candidate on ADR-0029's 0..100 scale (FR-026, AC-118).

    Args:
        signals: The solver telemetry for this candidate — pass
            ``SolveResult.signals``. Only the one solve that already happened
            is read; the search is never re-entered (ADR-0029/R2, guardrail
            G-1).

    Returns:
        A single float in :data:`SCORE_MIN`..:data:`SCORE_MAX`, larger meaning
        deeper line reasoning. Not rounded and not bucketed: the tier is
        :func:`classify`'s to decide, and rounding here would only lose
        information the resample loop's comparisons might want.

    The number is ``band_low(rung) + share * band_width(rung)`` for the hardest
    rung present — see the module docstring for why the band edges are the
    cutoff constants and not thirds.

    Pure and total: no I/O, no clock, no randomness, no solver re-entry, and no
    input it refuses. A candidate with no rung attribution at all scores
    :data:`SCORE_MIN`; that is the "not a puzzle" case, which INV-002 has
    already discarded before anything calls this, so the number means nothing
    rather than meaning "easy".

    ADR-0029/R1's cross-rung monotonicity holds structurally: the share is
    ``<= 1`` so a rung cannot outscore its own band's top, and a rung is
    *present* only if it settled a cell, so its share is ``> 0`` and it cannot
    reach its band's floor. Two puzzles at different top rungs therefore never
    overlap, whatever their extents.
    """
    rung = hardest_rung(signals.rung_cells)
    if rung is None:
        return SCORE_MIN

    total_cells = signals.total_cells
    if total_cells <= 0:  # pragma: no cover - a tagged cell implies a cell
        return SCORE_MIN

    low, high = RUNG_BANDS[rung]
    share = _clamp(signals.rung_cells[rung] / total_cells, 0.0, 1.0)
    return _clamp(low + share * (high - low), SCORE_MIN, SCORE_MAX)


def classify(score: float, branch_nodes: int) -> Tier:
    """The single tier classifier (ADR-0025/R1, R2) — EC-015 first, bands after.

    Args:
        score: :func:`score_difficulty`'s number for this candidate.
        branch_nodes: The *same* solve's branch count. Not a second solve and
            not a re-derivation: the orchestrator takes both off the one
            verifying solve's signals and hands them here together
            (ADR-0029/R2).

    Returns:
        :attr:`Tier.GUESS` whenever the search branched — regardless of score,
        because "requires guessing" is a fact about the solve and never a
        threshold on a number (EC-015) — and otherwise the tier whose band
        holds ``score``.

    This is the only implementation of that rule in the package, which is
    ADR-0025/R2 and is enforced by an ``ast`` walk in
    ``tests/test_difficulty_tiers.py``. A module that compared a score against
    :data:`EASY_MAX_SCORE` itself, or read ``branch_nodes`` to reach a tier,
    would be a second classifier that a retune could silently leave behind.
    """
    if branch_nodes > 0:
        return Tier.GUESS
    return _tier_for_score(score)


def _tier_for_score(score: float) -> Tier:
    """Which *band* a score falls in — :func:`classify`'s second half, and private.

    Private because a score alone can no longer classify a result (ADR-0025's
    Negative says so in as many words): a caller holding only a number cannot
    tell Easy from Guess, and one that reached for this function instead of
    :func:`classify` would be reintroducing exactly the bug the fourth tier
    exists to prevent.

    Total on the whole real line, not just on 0..100: a score below
    :data:`SCORE_MIN` reads as Easy and one above :data:`SCORE_MAX` as Hard.
    :func:`score_difficulty` cannot produce either, and a classifier that
    raised on them would only turn a scale bug into a crash at the point
    furthest from its cause.

    The cutoffs belong to the *lower* band (``33.0`` is Easy, ``66.0`` is
    Medium), which is ADR-0005's ``Easy = [0, 33], Medium = (33, 66],
    Hard = (66, 100]`` read literally — and which is what makes ADR-0029's
    band-edge mapping land a full-share bottom rung on 33.0 rather than a third
    of a point outside it.
    """
    if score <= EASY_MAX_SCORE:
        return Tier.EASY
    if score <= MEDIUM_MAX_SCORE:
        return Tier.MEDIUM
    return Tier.HARD


def tier_of_record(value: object) -> Tier | None:
    """Read a tier back out of stored or submitted text. Total; never raises.

    :func:`parse_tier` is the *input* rule — it rejects, because a user who
    typed ``--difficulty extreme`` needs to be told (AC-021). This is the
    *output* rule, for text that already exists and cannot be argued with: a
    row written months ago, a query string, a book's puzzle dict. There is
    nobody to tell, so an unrecognised value is simply not a tier.

    It exists because the admin surfaces read tiers from rows whose spelling is
    not one thing. A row written through the generation pipeline stores the
    enum *value* (``"easy"``) — ``orchestrator.Puzzle.difficulty_tier`` is a
    :class:`Tier` and a :class:`~enum.StrEnum`'s ``str`` is its value — while
    older rows and hand-entered ones carry the display label (``"Easy"``).
    Comparing against one spelling silently matches none of the other's rows,
    which is not a rendering bug but a *counting* one: it reports zero and
    looks like an empty book rather than like a broken reader.

    Returns:
        The :class:`Tier` this text denotes under either spelling and any
        casing, or ``None`` for ``None``, a blank, a non-string, or a word that
        is not a tier at all.

    Re-grading the rows so that only one spelling exists is CARD-077's job and
    a different kind of act — this function only makes the reader honest about
    what is already on disk, and it keeps working afterwards.
    """
    if not isinstance(value, str):
        return None
    try:
        return parse_tier(value)
    except UnsupportedDifficulty:
        return None


def parse_tier(text: str) -> Tier:
    """Resolve what the user typed into a :class:`Tier` (FR-008, AC-021).

    The domain-side check ``--difficulty`` deliberately does not do in argparse
    (ADR-0010): which tiers exist is a domain rule, so a misspelled tier
    reaches this function as an ordinary string and leaves it as a
    :class:`~nonogram.errors.NonogramError` the CLI maps to an exit code — not
    as an argparse usage error.

    Surrounding whitespace and case are not part of the rule: ``"Medium"`` is
    AC-020's own spelling of the tier whose flag value is ``medium``, and
    refusing it would be pedantry rather than validation.

    Raises:
        UnsupportedDifficulty: ``text`` names no supported tier (AC-021). The
            message lists the tiers that exist — all four of them since
            ADR-0025, read off the enum rather than spelled out, so the message
            and the rule cannot drift.
    """
    try:
        return Tier(text.strip().lower())
    except ValueError:
        supported = ", ".join(tier.value for tier in Tier)
        raise UnsupportedDifficulty(
            f"unsupported difficulty tier {text!r}; supported tiers are: {supported}"
        ) from None


def _clamp(value: float, low: float, high: float) -> float:
    """``value`` confined to ``low..high``."""
    return low if value < low else high if value > high else value
