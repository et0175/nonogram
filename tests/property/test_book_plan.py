"""Property tests for the book distribution plan (CARD-119).

    EC-023 (INV-005)  PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan
    POL-007           PropertyTest_BookPlan_HandEditedCellsSurviveAnySplitChange

No ``hypothesis`` (not in ADR-0006's baseline): the corpora are built by hand
with a seeded :class:`random.Random` plus exhaustive sweeps, and their size is
asserted inside the tests so they cannot silently shrink.

How this avoids asserting the implementation against itself: the expected
apportionment is computed by an *independent* method — :func:`_oracle_apportion`
hands out units one at a time to the share whose current count lags its exact
quota the most (a Hamilton/largest-remainder method phrased as sequential
allocation over :class:`fractions.Fraction`), ties to the earlier share. It
shares no code with ``book_plan._largest_remainder`` (floors + sorted
remainders), so a bug in either shows as a disagreement.
"""

from __future__ import annotations

import random
from fractions import Fraction

from nonogram.admin.book_plan import (
    BOOK1_MATRIX,
    BUCKETS,
    TIERS,
    Split,
    prefill,
    tier_counts,
    with_edited_cell,
    with_split,
)

_SEED = 20260922


def _oracle_apportion(total: int, weights: tuple[int, ...]) -> tuple[int, ...]:
    """Independent largest-remainder: floors, then one unit at a time to the biggest lag."""
    quotas = [Fraction(total * w, sum(weights)) for w in weights]
    counts = [q.numerator // q.denominator for q in quotas]
    while sum(counts) < total:
        best = None
        for i, q in enumerate(quotas):
            lag = q - counts[i]
            if best is None or lag > quotas[best] - counts[best]:  # strict: ties keep the earlier
                best = i
        assert best is not None
        counts[best] += 1
        quotas[best] = Fraction(counts[best])  # consumed: this share takes no second unit
    return tuple(counts)


def _all_splits(step: int) -> list[Split]:
    return [Split(e, m, 100 - e - m) for e in range(0, 101, step) for m in range(0, 101 - e, step)]


def _cases() -> list[tuple[int, Split]]:
    rng = random.Random(_SEED)
    cases: list[tuple[int, Split]] = []
    # Exhaustive over a coarse split grid for small and typical counts.
    for count in list(range(1, 61)) + [99, 100, 101, 120, 137, 150, 151, 199, 250, 400]:
        for split in _all_splits(5):
            cases.append((count, split))
    # Random whole-percent splits and counts, including large ones.
    for _ in range(5000):
        e = rng.randint(0, 100)
        m = rng.randint(0, 100 - e)
        cases.append((rng.randint(1, 1000), Split(e, m, 100 - e - m)))
    return cases


def test_PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan() -> None:
    """EC-023 — PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan.

    For any count >= 1 and any split summing to 100: 12 non-negative int cells,
    sum == count, column totals == the general plan's tier counts, zero-share
    cells (<=15 x hard, 26-30 x easy) are 0 — and every value agrees with an
    independent apportionment.
    """
    cases = _cases()
    assert len(cases) >= 15000, "the corpus shrank"
    ties_seen = 0
    for count, split in cases:
        counts = tier_counts(count, split)
        expected_counts = _oracle_apportion(count, (split.easy, split.medium, split.hard))
        assert counts == expected_counts, (count, split)
        assert sum(counts) == count

        plan = prefill(count, split)
        flat = [v for row in plan.cells for v in row]
        assert len(flat) == 12
        assert all(isinstance(v, int) and v >= 0 for v in flat)
        assert sum(flat) == count
        for t in range(3):
            column = tuple(row[t] for row in plan.cells)
            assert sum(column) == counts[t], (count, split, t)
            assert column == _oracle_apportion(counts[t], tuple(r[t] for r in BOOK1_MATRIX))
        assert plan.cells[0][2] == 0  # <=15 x hard
        assert plan.cells[3][0] == 0  # 26-30 x easy
        assert not plan.disagrees_with_split
        assert plan.edited == frozenset()
        if (count * split.medium) % 100 and (count * split.medium) % 100 == (count * split.hard) % 100:
            ties_seen += 1
    # Tie-breaking must actually be exercised, or the oracle's tie rule is untested.
    assert ties_seen >= 100


def test_PropertyTest_BookPlan_HandEditedCellsSurviveAnySplitChange() -> None:
    """POL-007 — PropertyTest_BookPlan_HandEditedCellsSurviveAnySplitChange.

    For any plan, any set of hand edits and any new split: edited cells keep
    their value and their edited mark, every unedited cell equals its prefill at
    the new split, and ``disagrees_with_split`` is True iff a column total is off
    the new tier counts. With no edits the result is exactly the prefill.
    """
    rng = random.Random(_SEED + 1)
    cells = [(b, t) for b in BUCKETS for t in TIERS]
    checked = disagreed = 0
    for _ in range(3000):
        count = rng.randint(1, 400)
        e = rng.randint(0, 100)
        m = rng.randint(0, 100 - e)
        plan = prefill(count, Split(e, m, 100 - e - m))
        edits = {c: rng.randint(0, 80) for c in rng.sample(cells, rng.randint(0, 5))}
        for (bucket, tier), value in edits.items():
            plan = with_edited_cell(plan, bucket, tier, value)
        e2 = rng.randint(0, 100)
        m2 = rng.randint(0, 100 - e2)
        new_split = Split(e2, m2, 100 - e2 - m2)

        changed = with_split(plan, new_split)
        fresh = prefill(count, new_split)
        assert changed.split == new_split and changed.count == count
        assert changed.edited == frozenset(edits)
        for bucket, tier in cells:
            want = edits[(bucket, tier)] if (bucket, tier) in edits else fresh.cell(bucket, tier)
            assert changed.cell(bucket, tier) == want
        columns = tuple(sum(row[t] for row in changed.cells) for t in range(3))
        assert changed.disagrees_with_split == (columns != tier_counts(count, new_split))
        if not edits:
            assert changed == fresh
        checked += 1
        disagreed += changed.disagrees_with_split
    assert checked >= 3000
    assert 100 <= disagreed < checked, "both outcomes of the warning must be exercised"
