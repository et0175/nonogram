"""A book's distribution plan as pure domain (FR-034, FR-035, FR-036; CARD-119).

The arithmetic behind Print setup's plan, with no database, Flask or template
anywhere near it (COMP-009, AGG-002's plan value). Everything later that talks
about *planned vs actual* — the Print setup form, the longest-side tabs, the
readiness gate and the books-list statistics — reads these functions and never
re-derives them.

* :class:`LongestSideBucket` and :func:`bucket_of` — the **one** bucketing
  function (TERM-027, EC-024). A puzzle's bucket is decided by
  ``max(width, height)`` alone.
* :class:`Split` — an easy/medium/hard split in whole percent summing to exactly
  100 (INV-005). Construction refuses anything else.
* :class:`DistributionPlan` — count, split, the 4 x 3 per-bucket matrix and the
  set of hand-edited cells (TERM-026, TERM-029).
* :func:`prefill` — the Book 1 size x difficulty matrix rescaled column by column
  to a count and split (EC-023).
* :func:`with_split` — POL-007: a split change re-derives unedited cells and keeps
  hand-edited ones.
* :data:`DEFAULT_PLAN` — 150 at 40/40/20, a constant of book creation (ADR-0034).
* :func:`planned_cells` / :func:`selection_cells` — the two sides of every
  planned-vs-actual comparison, keyed identically by ``(bucket, tier)``.
* :func:`book_level_order` and the functions beside it — the book's
  **level order** (TERM-032, INV-009, FR-041; CARD-126). The plan decides *what
  goes in*; this decides *what order it prints in*, and both speak the same
  tier vocabulary, which is why they live in one module.

Rounding
--------
All apportionment is exact integer largest-remainder arithmetic: each share's
quota is ``total * weight / weight_sum``, its floor is the integer quotient and
its remainder the integer ``total * weight % weight_sum``, so two remainders
that are mathematically equal compare equal (no float can split a tie). Units
left over after the floors go to the largest remainders. Ties go to the
**harder tier** for the general plan's tier counts (hard, then medium, then
easy — the owner's choice, 2026-09-22: 150 at 30/45/25 is 45/67/38), and to the
**earlier bucket** (<=15 first) inside a tier column, which is the rule AC-198's
worked table implies (medium 60 -> 7/27/20/6).

A share with zero weight has zero remainder and can never receive a leftover
unit (every leftover unit needs a *positive* remainder to claim it, and there
are always more positive remainders than leftover units), so the Book 1 matrix's
zero-share cells stay 0 structurally, not by a special case.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum

from nonogram.difficulty import Tier, tier_of_record
from nonogram.errors import SizeOutOfRange
from nonogram.limits import MAX_SIZE, MIN_SIZE

__all__ = [
    "BOOK1_MATRIX",
    "BUCKETS",
    "CROSS_LEVEL_REFUSAL",
    "DEFAULT_PLAN",
    "TIERS",
    "UNGRADED_RANK",
    "UNGROUPED_ORDER_REFUSAL",
    "DistributionPlan",
    "InvalidPlan",
    "LevelBoundary",
    "LongestSideBucket",
    "Split",
    "book_level_order",
    "book_levels",
    "bucket_of",
    "is_level_order",
    "level_rank",
    "moved_within_level",
    "place_in_level",
    "planned_cells",
    "prefill",
    "selection_cells",
    "tier_counts",
    "with_edited_cell",
    "with_split",
]


class InvalidPlan(ValueError):
    """A distribution plan, split or cell value that INV-005 does not allow."""


class LongestSideBucket(Enum):
    """TERM-027: the four longest-side buckets, in tab order.

    Each member's value is its display label; :attr:`low` and :attr:`high` are
    its inclusive longest-side range. The outer ends are the supported size
    range itself (:mod:`nonogram.limits`), so the four buckets partition it.
    """

    UP_TO_15 = "<=15"
    FROM_16_TO_20 = "16-20"
    FROM_21_TO_25 = "21-25"
    FROM_26_TO_30 = "26-30"

    @property
    def label(self) -> str:
        return self.value

    @property
    def low(self) -> int:
        return _BOUNDS[self][0]

    @property
    def high(self) -> int:
        return _BOUNDS[self][1]


_BOUNDS: dict[LongestSideBucket, tuple[int, int]] = {
    LongestSideBucket.UP_TO_15: (MIN_SIZE, 15),
    LongestSideBucket.FROM_16_TO_20: (16, 20),
    LongestSideBucket.FROM_21_TO_25: (21, 25),
    LongestSideBucket.FROM_26_TO_30: (26, MAX_SIZE),
}

#: The buckets in tab order (rows of the matrix).
BUCKETS: tuple[LongestSideBucket, ...] = tuple(LongestSideBucket)
#: The tiers in book order (columns of the matrix).
TIERS: tuple[Tier, ...] = (Tier.EASY, Tier.MEDIUM, Tier.HARD)


def bucket_of(width: int, height: int) -> LongestSideBucket:
    """The longest-side bucket of a ``width`` x ``height`` puzzle (EC-024).

    Decided by ``max(width, height)`` alone. Both sides must lie in the
    supported range; a side outside it belongs to no tab.

    The contract a database pushdown must mirror
    --------------------------------------------
    This function is the *whole* verdict, and a store that narrows to a bucket
    in SQL (``PuzzleFilter.longest_side_range``, CARD-122) has to reproduce
    both halves of it, not only the interesting one:

    1. ``low <= max(width, height) <= high`` for the bucket's own
       :attr:`~LongestSideBucket.low` / :attr:`~LongestSideBucket.high`, which
       come from here and from nowhere else (G-1); **and**
    2. *both* sides inside ``MIN_SIZE..MAX_SIZE`` — a row stored under an
       older size limit belongs to no bucket at all rather than to the nearest
       one, which is the same verdict :func:`selection_cells` makes on it.

    Half 2 is the one a pushdown forgets, and forgetting it makes the store's
    count and the rendered tab disagree about the same row. Changing either
    half here is a change to that predicate too (review cycle 2, F-006).

    Raises:
        SizeOutOfRange: either side is outside ``MIN_SIZE..MAX_SIZE``.
    """
    for name, side in (("width", width), ("height", height)):
        if isinstance(side, bool) or not isinstance(side, int) or not MIN_SIZE <= side <= MAX_SIZE:
            raise SizeOutOfRange(
                f"{name} {side!r} is outside the supported {MIN_SIZE}..{MAX_SIZE} range"
            )
    longest = max(width, height)
    for bucket in BUCKETS:
        if longest <= bucket.high:
            return bucket
    raise AssertionError("unreachable: the buckets cover MIN_SIZE..MAX_SIZE")  # pragma: no cover


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True)
class Split:
    """An easy/medium/hard split in whole percent that sums to exactly 100 (INV-005)."""

    easy: int
    medium: int
    hard: int

    def __post_init__(self) -> None:
        values = (self.easy, self.medium, self.hard)
        if not all(_is_int(v) and 0 <= v <= 100 for v in values):
            raise InvalidPlan(f"each split share must be a whole percent 0..100, got {values}")
        if sum(values) != 100:
            raise InvalidPlan(
                f"the split must sum to exactly 100%, got {'/'.join(map(str, values))}"
                f" = {sum(values)}%"
            )

    def percent(self, tier: Tier) -> int:
        return {Tier.EASY: self.easy, Tier.MEDIUM: self.medium, Tier.HARD: self.hard}[tier]


#: Book 1's size x difficulty matrix (docs/research/book-format-research.md §8),
#: in percent of the book, rows in :data:`BUCKETS` order, columns in
#: :data:`TIERS` order. "–" is 0.
BOOK1_MATRIX: tuple[tuple[int, int, int], ...] = (
    (10, 5, 0),   # <=15
    (15, 20, 5),  # 16-20
    (5, 15, 10),  # 21-25
    (0, 5, 10),   # 26-30
)

Cell = tuple[LongestSideBucket, Tier]


@dataclass(frozen=True)
class DistributionPlan:
    """TERM-026/029: a book's general plan plus its per-longest-side matrix.

    ``cells`` is 4 x 3 — one row per bucket in :data:`BUCKETS` order, one column
    per tier in :data:`TIERS` order — of non-negative ints. ``edited`` names the
    cells the owner typed a value into. Hand edits may leave the matrix out of
    step with the general plan; that is allowed and reported by
    :attr:`disagrees_with_split`, never refused.
    """

    count: int
    split: Split
    cells: tuple[tuple[int, ...], ...]
    edited: frozenset[Cell] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not _is_int(self.count) or self.count < 1:
            raise InvalidPlan(f"the puzzle count must be a whole number of at least 1, got {self.count!r}")
        if not isinstance(self.split, Split):
            raise InvalidPlan(f"split must be a Split, got {type(self.split).__name__}")
        cells = tuple(tuple(row) for row in self.cells)
        if len(cells) != len(BUCKETS) or any(len(row) != len(TIERS) for row in cells):
            raise InvalidPlan("the per-bucket plan must be 4 buckets x 3 tiers")
        if not all(_is_int(v) and v >= 0 for row in cells for v in row):
            raise InvalidPlan(f"every per-bucket count must be a non-negative whole number, got {cells}")
        edited = frozenset(self.edited)
        if not all(
            isinstance(c, tuple) and len(c) == 2 and c[0] in BUCKETS and c[1] in TIERS for c in edited
        ):
            raise InvalidPlan(f"edited cells must be (LongestSideBucket, Tier) pairs, got {set(edited)}")
        object.__setattr__(self, "cells", cells)
        object.__setattr__(self, "edited", edited)

    def cell(self, bucket: LongestSideBucket, tier: Tier) -> int:
        return self.cells[BUCKETS.index(bucket)][TIERS.index(tier)]

    @property
    def tier_counts(self) -> tuple[int, int, int]:
        """The general plan's easy/medium/hard counts (see :func:`tier_counts`)."""
        return tier_counts(self.count, self.split)

    @property
    def disagrees_with_split(self) -> bool:
        """True when the matrix's column totals differ from the general plan's tier counts.

        Column totals equal to the tier counts imply the matrix sums to the count,
        so this one comparison covers both. A prefilled plan never disagrees;
        only hand edits can make it (FR-034's warning).
        """
        columns = tuple(sum(row[t] for row in self.cells) for t in range(len(TIERS)))
        return columns != self.tier_counts


def _largest_remainder(
    total: int, weights: tuple[int, ...], *, ties_to_later: bool = False
) -> tuple[int, ...]:
    """Apportion ``total`` over ``weights`` by largest remainder.

    Equal remainders go to the earlier index, or to the later one when
    ``ties_to_later``. Exact integers throughout. ``weights`` must have a
    positive sum.
    """
    weight_sum = sum(weights)
    floors = [total * w // weight_sum for w in weights]
    remainders = [total * w % weight_sum for w in weights]
    leftover = total - sum(floors)
    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], -i if ties_to_later else i))
    for i in order[:leftover]:
        floors[i] += 1
    return tuple(floors)


def tier_counts(count: int, split: Split) -> tuple[int, int, int]:
    """The general plan's easy/medium/hard counts: ``count x split``, summing to ``count``.

    When ``count x split`` is not whole (137 x 40% = 54.8) the three counts are
    rounded by largest remainder, ties to the harder tier (EC-023; owner's
    choice 2026-09-22).
    """
    easy, medium, hard = _largest_remainder(
        count, (split.easy, split.medium, split.hard), ties_to_later=True
    )
    return easy, medium, hard


def prefill(count: int, split: Split) -> DistributionPlan:
    """The per-bucket plan prefilled from :data:`BOOK1_MATRIX` (FR-034, EC-023).

    Column by column: each tier's count is apportioned over the four buckets in
    proportion to that tier's Book 1 column, so every column total equals its
    tier count exactly and the matrix sums to ``count``. Row totals are not
    preserved (FR-034 note). No cell is marked hand-edited.
    """
    counts = tier_counts(count, split)
    columns = [
        _largest_remainder(counts[t], tuple(row[t] for row in BOOK1_MATRIX))
        for t in range(len(TIERS))
    ]
    cells = tuple(tuple(columns[t][b] for t in range(len(TIERS))) for b in range(len(BUCKETS)))
    return DistributionPlan(count=count, split=split, cells=cells)


def with_split(plan: DistributionPlan, new_split: Split) -> DistributionPlan:
    """POL-007 (CMD-020 -> EVT-021): change the general split.

    Unedited cells are re-derived — they take their :func:`prefill` value at the
    plan's count and the new split — so a plan with no hand-edited cells becomes
    exactly ``prefill(plan.count, new_split)``. Hand-edited cells keep their
    values and stay marked edited; if that leaves the column totals off the new
    tier counts, the result's :attr:`~DistributionPlan.disagrees_with_split` is
    True so Print setup can warn.
    """
    fresh = prefill(plan.count, new_split)
    cells = tuple(
        tuple(
            plan.cells[b][t] if (bucket, tier) in plan.edited else fresh.cells[b][t]
            for t, tier in enumerate(TIERS)
        )
        for b, bucket in enumerate(BUCKETS)
    )
    return DistributionPlan(count=plan.count, split=new_split, cells=cells, edited=plan.edited)


def with_edited_cell(
    plan: DistributionPlan, bucket: LongestSideBucket, tier: Tier, value: int
) -> DistributionPlan:
    """The owner types ``value`` into one cell: set it and mark it hand-edited."""
    b, t = BUCKETS.index(bucket), TIERS.index(tier)
    cells = tuple(
        tuple(value if (i, j) == (b, t) else v for j, v in enumerate(row))
        for i, row in enumerate(plan.cells)
    )
    return DistributionPlan(
        count=plan.count, split=plan.split, cells=cells, edited=plan.edited | {(bucket, tier)}
    )


#: ADR-0034: every new book starts at 150 puzzles, 40/40/20 (60/60/30), with the
#: prefilled matrix. A constant — not a function of the book's audience.
DEFAULT_PLAN: DistributionPlan = prefill(150, Split(40, 40, 20))


def planned_cells(plan: DistributionPlan) -> dict[Cell, int]:
    """The plan's count for every ``(bucket, tier)`` cell — all 12 keys present."""
    return {(bucket, tier): plan.cell(bucket, tier) for bucket in BUCKETS for tier in TIERS}


def selection_cells(puzzles: Iterable[Mapping[str, object]]) -> dict[Cell, int]:
    """How many of ``puzzles`` fall in each ``(bucket, tier)`` cell — all 12 keys present.

    Each puzzle is a record as the admin panel holds it (``width``, ``height``,
    ``difficulty_tier``). The tier is read through
    :func:`nonogram.difficulty.tier_of_record` from what is stored — never
    re-graded (ADR-0033/R1). A record with no recognisable tier, or with a side
    outside the supported range (a row stored under an older size limit), has
    no cell and is not counted: it belongs to no tab and no plan cell.
    """
    counts = {(bucket, tier): 0 for bucket in BUCKETS for tier in TIERS}
    for puzzle in puzzles:
        tier = tier_of_record(puzzle.get("difficulty_tier"))
        if tier not in TIERS:
            continue
        try:
            bucket = bucket_of(puzzle.get("width"), puzzle.get("height"))
        except SizeOutOfRange:
            continue
        counts[(bucket, tier)] += 1
    return counts


# ---------------------------------------------------------------------------
# The book's level order (FR-041, INV-009, TERM-032; CARD-126)
# ---------------------------------------------------------------------------
#
# A book runs easy, then medium, then hard. Inside a level the sequence is the
# owner's own arrangement, and it changes only when they explicitly move a
# puzzle *within* that level. :func:`book_level_order` is **the one grouping**
# every consumer uses — the moves, the adds, the arrange page and (CARD-128)
# the printed book — so the order on screen is the order on the page, with no
# second sorting rule anywhere to drift away from this one.
#
# Everything here is pure: ids in, ids out. The caller supplies ``tier_of``, a
# function from a puzzle id to its **stored** tier (``difficulty.tier_of_record``
# on what the row holds) or ``None``. Nothing here reads a database, and
# nothing re-grades a puzzle — ADR-0033/R1 and ADR-0031: the tier is read, and
# a book never derives one from a grid's size.

#: Where a puzzle whose stored tier is not one of the three goes: after all of
#: them. A row with a missing, blank or unrecognised ``difficulty_tier`` has no
#: level, and the honest place for it is the end — never silently inside easy,
#: where it would sit among puzzles it has not been shown to belong with, and
#: never dropped, because dropping it would make the order stop being a
#: permutation of the membership (INV-009 is about *order*, not membership).
UNGRADED_RANK: int = len(TIERS)

#: Why a move was refused. One sentence, shown to the owner by the arrange
#: route: it names the rule rather than the two levels, because the rule is the
#: same wherever the boundary is and this way there is one string to keep true.
CROSS_LEVEL_REFUSAL = (
    "A book runs easy, then medium, then hard, and a move stays inside its own "
    "level. This move would carry the puzzle across a level boundary, so the "
    "order is unchanged."
)

#: Why a whole submitted order was refused (:func:`is_level_order`).
UNGROUPED_ORDER_REFUSAL = (
    "This order is not grouped by level. A book runs easy, then medium, then "
    "hard, so the order was not stored."
)


class LevelBoundary(ValueError):
    """An order change INV-009 refuses: it would break the easy/medium/hard grouping.

    A :class:`ValueError`, so every caller that already handles the book
    store's refusals handles this one too; a distinct class, so the arrange
    route can tell "the owner asked for something the order does not allow"
    from "something went wrong" and word the flash accordingly.
    """


def level_rank(tier: Tier | None) -> int:
    """Where ``tier``'s level sits in the book: 0 easy, 1 medium, 2 hard.

    Anything that is not one of :data:`TIERS` — ``None`` above all — ranks
    :data:`UNGRADED_RANK`, after every graded level.
    """
    return TIERS.index(tier) if tier in TIERS else UNGRADED_RANK


def book_level_order(puzzle_ids, tier_of):
    """``puzzle_ids`` grouped easy, then medium, then hard (INV-009).

    The relative order of two ids of the *same* level is exactly the one they
    came in with — the sort is stable and its key is the level alone — so this
    never reorders inside a level and never invents an arrangement the owner
    did not make. It is idempotent: the grouped order of a grouped order is
    itself, which is what lets a legacy mixed arrangement be *read* grouped
    without anything being rewritten (the card's AC-260 note; only a move
    writes the grouped order back, :func:`moved_within_level`).

    Args:
        puzzle_ids: the book's stored order.
        tier_of: a total function from a puzzle id to its stored
            :class:`~nonogram.difficulty.Tier`, or ``None`` when the row has no
            recognisable tier or cannot be read at all.

    Returns:
        A new list — the same ids, grouped. A permutation of the input,
        always.
    """
    return sorted(puzzle_ids, key=lambda puzzle_id: level_rank(tier_of(puzzle_id)))


def is_level_order(puzzle_ids, tier_of) -> bool:
    """True when ``puzzle_ids`` is already grouped by level — INV-009's predicate."""
    ids = list(puzzle_ids)
    return book_level_order(ids, tier_of) == ids


def book_levels(puzzle_ids, tier_of) -> list[tuple[Tier | None, list]]:
    """The grouped order cut into its levels, in book order.

    ``[(tier, [ids...]), ...]`` over :func:`book_level_order`, one entry per
    **non-empty** level — an empty level has no entry, which is the same shape
    CARD-128's "one divider per non-empty level" needs. The ungraded tail, if
    there is one, is the last entry with ``None`` for its tier.
    """
    groups: list[tuple[Tier | None, list]] = []
    for puzzle_id in book_level_order(puzzle_ids, tier_of):
        tier = tier_of(puzzle_id)
        level = tier if tier in TIERS else None
        if not groups or groups[-1][0] is not level:
            groups.append((level, []))
        groups[-1][1].append(puzzle_id)
    return groups


def place_in_level(order, new_ids, tier_of) -> list:
    """``new_ids`` inserted at the end of their own levels, in submission order.

    The owner's answer for an add (FR-041): a new puzzle joins the back of its
    level's queue, not the back of the book — so an easy picture added to a
    book that already has medium ones prints before them (AC-259).

    Insertion, not a re-sort: each id goes after the last id already in the
    list whose level is not *later* than its own. On an order that is already
    grouped this is exactly "the end of that level". On a **legacy mixed**
    order it is still the end of that level as :func:`book_level_order` reads
    it, and the rest of the stored list is left alone — an add is not the place
    a legacy arrangement gets normalised (that is the move, and only the move).

    Two new ids of one level keep the order they were submitted in, because
    each is placed after the one before it.
    """
    placed = list(order)
    for puzzle_id in new_ids:
        rank = level_rank(tier_of(puzzle_id))
        index = len(placed)
        while index and level_rank(tier_of(placed[index - 1])) > rank:
            index -= 1
        placed.insert(index, puzzle_id)
    return placed


def moved_within_level(puzzle_ids, puzzle_id, offset, tier_of) -> list | None:
    """The order after moving ``puzzle_id`` by ``offset`` places inside its level.

    The move is made on the **grouped** view (:func:`book_level_order`), and
    the grouped order is what comes back, so a move on a legacy mixed book
    normalises it — the one point in the system where that happens, and the
    owner sees the result immediately on the page they clicked.

    Args:
        puzzle_ids: the book's stored order.
        puzzle_id: the id being moved. Must be in ``puzzle_ids``.
        offset: ``-1`` for up, ``+1`` for down. Any integer works.
        tier_of: as :func:`book_level_order`.

    Returns:
        The new order, or ``None`` when there is no neighbour at all — the
        puzzle is at the very top or the very bottom of the book, which has
        always meant "nothing happened" rather than "refused".

    Raises:
        LevelBoundary: the neighbour the move would swap with belongs to
            another level (AC-258). Nothing is returned and nothing is changed;
            the caller writes nothing.
    """
    order = book_level_order(puzzle_ids, tier_of)
    index = order.index(puzzle_id)
    target = index + offset
    if not 0 <= target < len(order):
        return None
    if level_rank(tier_of(order[target])) != level_rank(tier_of(puzzle_id)):
        raise LevelBoundary(CROSS_LEVEL_REFUSAL)
    order[index], order[target] = order[target], order[index]
    return order
