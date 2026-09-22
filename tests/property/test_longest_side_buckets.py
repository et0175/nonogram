"""Property test for the longest-side buckets (CARD-119, FR-036).

    EC-024  PropertyTest_LongestSideBuckets_PartitionEveryExtent

The sweep is exhaustive over the supported range (``nonogram.limits``), not
sampled. The expected bucket is decided independently of ``bucket_of``: by
membership in each bucket's declared ``low..high`` range, counted, so a gap
shows as zero matches and an overlap as two.
"""

from __future__ import annotations

from nonogram.admin.book_plan import BUCKETS, bucket_of
from nonogram.limits import MAX_SIZE, MIN_SIZE


def test_PropertyTest_LongestSideBuckets_PartitionEveryExtent() -> None:
    """EC-024 — PropertyTest_LongestSideBuckets_PartitionEveryExtent.

    Every extent in MIN_SIZE..MAX_SIZE x MIN_SIZE..MAX_SIZE lands in exactly
    one of the four buckets, chosen by max(width, height) alone.
    """
    sides = range(MIN_SIZE, MAX_SIZE + 1)
    # The declared ranges tile the supported range end to end: no gap, no overlap.
    assert len(BUCKETS) == 4
    assert BUCKETS[0].low == MIN_SIZE and BUCKETS[-1].high == MAX_SIZE
    for lower, upper in zip(BUCKETS, BUCKETS[1:]):
        assert upper.low == lower.high + 1

    checked = 0
    seen = set()
    for width in sides:
        for height in sides:
            longest = max(width, height)
            matches = [b for b in BUCKETS if b.low <= longest <= b.high]
            assert len(matches) == 1, (width, height, matches)
            got = bucket_of(width, height)
            assert got is matches[0], (width, height)
            # max() alone: the transposed extent and the square of the longest side agree.
            assert bucket_of(height, width) is got
            assert bucket_of(longest, longest) is got
            assert bucket_of(longest, MIN_SIZE) is got
            seen.add(got)
            checked += 1
    assert checked == len(sides) ** 2 >= 441
    assert seen == set(BUCKETS), "every tab must be reachable"


def test_the_tab_boundaries_are_the_termed_ones() -> None:
    """TERM-027: <=15, 16-20, 21-25, 26-30 — pinned, since the sweep derives from them."""
    assert [(b.low, b.high) for b in BUCKETS] == [(MIN_SIZE, 15), (16, 20), (21, 25), (26, MAX_SIZE)]
