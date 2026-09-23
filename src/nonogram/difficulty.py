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

The rung bands: where a score comes from, and why they are not thirds
---------------------------------------------------------------------
:data:`RUNG_BANDS` is the ladder's own table, and it is what
:func:`score_difficulty` reads: ``simple_overlap`` 0..33, ``line_dp`` 33..66,
``probe_contradiction`` 66..100 (widths 33, 33, 34), exactly as ADR-0029 draws
them. Idealised thirds do not work, and the failure is not cosmetic: a puzzle
that tops out at ``simple_overlap`` has *every* settled cell at that rung by
definition, so its share is exactly ``1.0`` (measured 1.000 in 420 of 420
line-solvable grids). At a band width of 33.33 that scores 33.33 — above
:data:`EASY_MAX_SCORE` — so every Easy puzzle would classify Medium and the
Easy band would be empty (ADR-0029, History 2026-09-13).

With the edges where they are the arithmetic lands where ADR-0029 says it
should, because :func:`classify`'s cutoffs are inclusive upper bounds:

* a full-share bottom rung scores exactly ``33.0`` and classifies **Easy**;
* a higher rung is "present" only if it settled at least one cell, so its
  share is strictly positive and its score strictly above its band's lower
  edge — which is what makes ADR-0029/R1's cross-rung monotonicity hold by
  construction rather than by calibration.

One consequence is worth naming rather than hiding: **Easy is a single point
on the scale.** Every puzzle that never leaves overlap scores exactly 33.0, so
there is no within-rung ordering inside the bottom band at all. That is input
for the calibration below, not a defect of the mapping.

The tier bands: two tables now, and that is the point (CARD-137)
----------------------------------------------------------------
:data:`RUNG_BANDS` and :data:`TIER_BANDS` were **one** table until CARD-137 —
the rung table was literally ``zip(LADDER, TIER_BANDS.values())``, because
ADR-0029's History of 2026-09-13 concluded that "ADR-0005's cutoffs now land
exactly on rung boundaries", so a tier *was* a rung: Easy = never left
overlap, Medium = needed the full placement intersection, Hard = needed a
refuted probe.

That identity is what made **Medium unreachable**. Needing the placement DP
somewhere and no probe anywhere is a narrow accident of a random draw: the
owner measured 5 Medium puzzles in 300 on production, and this project's own
database held 10 easy / 2 medium / 9 hard. Meanwhile the Hard rows' scores
spread 67..99 — a puzzle with one probed cell in an otherwise line-solvable
grid and a puzzle probed almost everywhere wore the same label, although
:func:`score_difficulty`'s within-rung share already told them apart.

So the two tables now genuinely diverge, and the divergence is the whole
change:

===================  ==========================  =========================
score                rung (``RUNG_BANDS``)       tier (``TIER_BANDS``)
===================  ==========================  =========================
``[0, 33]``          ``simple_overlap``          Easy
``(33, 66]``         ``line_dp``                 Medium
``(66, 90]``         ``probe_contradiction``     Medium
``(90, 100]``        ``probe_contradiction``     Hard
===================  ==========================  =========================

:data:`EASY_MAX_SCORE` still coincides with the top of the bottom rung, so
Easy still means exactly "the overlap rule finished it". :data:`MEDIUM_MAX_SCORE`
deliberately coincides with nothing on the ladder: it sits *inside* the probe
rung's band, at ``(90 - 66) / 34`` = **70.6% of the grid**. Medium therefore
means "the hardest rung was ``probe_contradiction`` but it settled at most
70.6% of the grid — or the puzzle topped out at ``line_dp``"; Hard means
"probing settled more than 70.6% of the grid, and line logic got essentially
nowhere". **A tier boundary that sits inside a rung's band is what makes
Medium reachable at all** (CARD-137, owner decision 2026-09-23).

Because the two tables are now different facts, :data:`RUNG_BANDS` is written
out rather than derived from :data:`TIER_BANDS`: deriving it would re-assert
an identity this module has stopped believing in, and the next retune of a
*tier* cutoff would silently re-scale every *score*.

**No stored grade moves on account of this.** The score mapping is
:data:`RUNG_BANDS` and it is untouched, so every puzzle scores exactly what it
scored before; what moved is only which tier a given score is filed under, and
re-filing stored rows is the admin panel's existing ``POST /regrade`` action
(ADR-0031/R3: no migration runs, no production database is touched here).

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
    "RUNG_LINE_DP_MAX_SCORE",
    "RUNG_OVERLAP_MAX_SCORE",
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

#: ADR-0005's two tier cutoffs — the single tuning surface it asked for, and
#: the *only* thing CARD-137 changed. They are inclusive upper bounds:
#: ``33.0`` is Easy and ``90.0`` is Medium.
#:
#: :data:`EASY_MAX_SCORE` is unchanged since ADR-0005 and still coincides with
#: the top of the bottom rung's band, which is what lets a full-share
#: ``simple_overlap`` puzzle score exactly 33.0 and stay Easy — Easy therefore
#: still means exactly "the overlap rule finished it".
#:
#: :data:`MEDIUM_MAX_SCORE` moved from ``66.0`` to ``90.0`` on the owner's
#: decision of 2026-09-23 (CARD-137), which is the recalibration ADR-0005 has
#: been owed since ADR-0029. At ``66.0`` it coincided with a rung boundary and
#: Medium meant "topped out at ``line_dp``" — measured at 5 puzzles in 300 on
#: production. At ``90.0`` it coincides with nothing on the ladder and sits
#: *inside* the probe rung's band, at ``(90 - 66) / 34`` = 70.6% of the grid:
#: Medium is "a little non-trivial work", Hard is "a lot". See the module
#: docstring for the two-table arithmetic and for why no stored grade moves.
EASY_MAX_SCORE = 33.0
MEDIUM_MAX_SCORE = 90.0

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

    **Every member is a score band** (ADR-0005, ADR-0031). ADR-0025 added a
    fourth, ``GUESS``, keyed on the solve's ``branch_nodes`` rather than on a
    number; CARD-098 retired it, and with it the two shapes it forced —
    :func:`classify` taking a second argument, and :attr:`band` answering
    ``None`` for one member.

    It was retired on evidence: its measured assignment rate was **zero**
    everywhere anyone looked — 0 of 6,620 (ADR-0029), 0 of 462 (CARD-076), 0
    of 16 stored rows, and CARD-072 established *why*: no random draw in the
    supported range branches at all after the solve's one-step lookahead
    phase, so the tier was not merely rare but unreachable from generation.

    ADR-0025's own argument for keeping it — a safety net for a future source
    that does branch — is answered rather than dismissed: branching is still
    reported, as the ``guess`` **strategy** (FR-029,
    :data:`nonogram.solver.STRATEGY_GUESS`). The fact survives; only the claim
    that it is a *difficulty* does not.

    CON-004: a tier is a bucket a *scored* candidate fell into, never a
    construction target. Asking for ``Tier.EASY`` makes the pipeline discard
    candidates that classified elsewhere (POL-004); it does not steer a grid
    toward being easy.
    """

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    @property
    def label(self) -> str:
        """The tier as AC-020 writes it — ``"Medium"``, not ``"medium"``.

        Presentational, and ADR-0025 says so explicitly: ``"Guess"`` may be
        renamed (to ``"Expert"``, say) without touching the enum *value*, which
        is what every stored row, export payload and filename depends on.
        """
        return self.value.capitalize()

    @property
    def band(self) -> tuple[float, float]:
        """This tier's ``(low, high)`` score band.

        Half-open at the bottom and closed at the top — ``low < score <= high``
        — except :attr:`EASY`, whose band includes :data:`SCORE_MIN` itself.

        Total since CARD-098: every tier has a band again, because the one
        member that did not is gone. For reporting and for tests that need to
        see where a band sits; :func:`classify` is what a caller should ask.

        **Not the same thing as a rung's band** since CARD-137. ``MEDIUM``
        spans ``(33, 90]`` and so covers the whole of ``line_dp`` and the lower
        70.6% of ``probe_contradiction``; ``HARD`` is the top of that one rung.
        :data:`RUNG_BANDS` is the other table, and the module docstring is
        where the two are drawn side by side.
        """
        return TIER_BANDS[self]


#: Each tier's ``(low, high)``, derived from the two cutoffs above rather than
#: written out as six numbers — see :meth:`Tier.band` for the open/closed ends.
#: Every member of :class:`Tier` is a key: since CARD-098 there is no tier that
#: is not a band.
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

#: ADR-0029's two *rung* boundaries on the 0..100 scale. They are not the tier
#: cutoffs, and since CARD-137 only the first of them coincides with one:
#: :data:`EASY_MAX_SCORE` is 33.0 too (so Easy is exactly the bottom rung),
#: while :data:`MEDIUM_MAX_SCORE` is 90.0 and lies *inside* the band that
#: starts here at 66.0. Moving one of these re-scales every score; moving a
#: tier cutoff re-files scores that do not change. Two different acts, two
#: different constants — see the module docstring.
RUNG_OVERLAP_MAX_SCORE = 33.0
RUNG_LINE_DP_MAX_SCORE = 66.0

#: Each rung's ``(low, high)`` score band — the table :func:`score_difficulty`
#: reads, and the one thing "no stored grade moves" is a statement about.
#:
#: Written out rather than zipped from :data:`TIER_BANDS`, which is how it was
#: built until CARD-137. The zip encoded ADR-0029's claim that a tier *is* a
#: rung; that claim is what made Medium unreachable, and the cutoff move
#: retired it. Deriving one table from the other now would re-assert it, and
#: would make the next retune of a tier cutoff silently re-scale every score.
RUNG_BANDS: Mapping[str, tuple[float, float]] = MappingProxyType(
    {
        RUNG_SIMPLE_OVERLAP: (SCORE_MIN, RUNG_OVERLAP_MAX_SCORE),
        RUNG_LINE_DP: (RUNG_OVERLAP_MAX_SCORE, RUNG_LINE_DP_MAX_SCORE),
        RUNG_PROBE_CONTRADICTION: (RUNG_LINE_DP_MAX_SCORE, SCORE_MAX),
    }
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
    rung present, over :data:`RUNG_BANDS` — the *ladder's* table, not the tier
    table, and the one CARD-137 deliberately did not touch so that no stored
    grade moves. See the module docstring for why those edges are 33/66 and
    not thirds.

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


def classify(score: float) -> Tier:
    """The single tier classifier (ADR-0031) — which band holds ``score``.

    Args:
        score: :func:`score_difficulty`'s number for this candidate.

    Returns:
        The tier whose band holds ``score``.

    One argument again since CARD-098. ADR-0025 gave this function a second —
    the solve's ``branch_nodes`` — so that a branching solve could answer
    ``Tier.GUESS`` regardless of score; ADR-0031 retired that tier, and the
    fact it carried is now reported as the ``guess`` *strategy* instead
    (:data:`nonogram.solver.STRATEGY_GUESS`), which is where a consumer should
    look for it.

    This is the only implementation of the band rule in the package, enforced
    by an ``ast`` walk in ``tests/test_difficulty_tiers.py``. A module that
    compared a score against :data:`EASY_MAX_SCORE` itself would be a second
    classifier that a retune could silently leave behind.

    Total on the whole real line, not just on 0..100: a score below
    :data:`SCORE_MIN` reads as Easy and one above :data:`SCORE_MAX` as Hard.
    :func:`score_difficulty` cannot produce either, and a classifier that
    raised on them would only turn a scale bug into a crash at the point
    furthest from its cause.

    The cutoffs belong to the *lower* band (``33.0`` is Easy, ``90.0`` is
    Medium), which is ADR-0005's inclusive-upper-bound reading — and which is
    what makes a full-share bottom rung land on 33.0 as Easy rather than a
    third of a point outside it.

    The bands are ``Easy = [0, 33]``, ``Medium = (33, 90]``,
    ``Hard = (90, 100]`` since CARD-137. Only the first edge is also a rung
    boundary; ``90.0`` cuts the ``probe_contradiction`` rung at 70.6% of the
    grid, so a score of 70 and a score of 95 are now different tiers although
    both puzzles needed a probe. That is the recalibration, and the module
    docstring says why a boundary inside a rung is the point of it.
    """
    if score <= EASY_MAX_SCORE:
        return Tier.EASY
    if score <= MEDIUM_MAX_SCORE:
        return Tier.MEDIUM
    return Tier.HARD


#: The value ADR-0025's retired fourth tier was stored as. Kept as a *reading*
#: rule only (CARD-098, ADR-0031): no build writes it, `parse_tier` refuses it
#: like any other unknown word, and nothing migrates the rows that carry it.
_RETIRED_GUESS_TIER = "guess"


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
        is not a tier at all. ``"guess"`` is the one word that is no longer a
        tier but is still read: see :data:`_RETIRED_GUESS_TIER`.

    Re-grading the rows so that only one spelling exists is CARD-077's job and
    a different kind of act — this function only makes the reader honest about
    what is already on disk, and it keeps working afterwards.
    """
    if not isinstance(value, str):
        return None
    if value.strip().casefold() == _RETIRED_GUESS_TIER:
        # A row written while ADR-0025's fourth tier existed. It reads as Hard
        # rather than as nothing: `None` means "not a tier at all", which would
        # drop the row out of every count and filter silently — a counting bug
        # wearing a rendering bug's clothes, which is the failure this whole
        # function was written to prevent. A puzzle that needed a branch is at
        # least as hard as the hardest band, so Hard is the nearest true
        # statement about it, and a re-grade (CARD-077) will reassign it on its
        # own terms. Nothing here rewrites what is stored.
        return Tier.HARD
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
