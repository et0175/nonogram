"""EC-025 (INV-007) — the readiness gate, as an iff over a seeded corpus.

    PropertyTest_BookReady_GateIffEveryCellWithinTolerance

The property: for **any** plan and **any** selection, marking the book ready
succeeds if and only if every one of the 12 longest-side x tier cells is within
+/-3 percentage points of its planned share — and no route out of draft, to any
status and in either storage mode, bypasses that check.

No ``hypothesis`` — it is not in the dependency baseline (ADR-0006). The corpus
is built by hand with stdlib :class:`random.Random` from fixed seeds, and each
test asserts how many cases it saw, in each verdict, so the corpus cannot
silently shrink to nothing while still passing.

The expectation is an **independent second implementation**: exact
:class:`~fractions.Fraction` shares compared against the literal ``3/100``, over
the cell counts each case was *built* from. Nothing here asks
``selection_cells``, ``planned_cells``, ``off_plan_cells`` or the gate itself
what the answer should be.

Half of every corpus is drawn inside the tolerance and half around it, so both
directions of the iff are measured, and both boundaries — a cell exactly on the
bound, which is in, and one unit past it, which is out — are drawn every time.
"""

from __future__ import annotations

import random
from fractions import Fraction

import pytest

from nonogram.admin.book_manager import (
    READY_TOLERANCE_POINTS,
    BookStatus,
    DistributionPlan,
    Split,
    ready_refusal,
)
from nonogram.admin.book_plan import BUCKETS, TIERS
from nonogram.limits import MAX_SIZE
from tests.helpers.db import sqlite_session_scope
from tests.test_book_ready_gate import Shelf

#: The tolerance as the requirement states it, in percentage points of the
#: planned total. A literal fraction rather than a value taken from the code,
#: so the oracle and the gate are free to disagree.
TOLERANCE = Fraction(3, 100)

#: How many cases the pure-domain corpus holds, how many of them a run must
#: see, and how many must land on each side of the verdict.
CORPUS = 600
MIN_CASES = 500
MIN_PER_VERDICT = 100

#: The smaller corpus driven through real books in real storage, per case set.
STORAGE_CASES = 24

CELLS = tuple((bucket, tier) for bucket in BUCKETS for tier in TIERS)

NON_DRAFT = [s.value for s in BookStatus if s is not BookStatus.DRAFT]


def _split(rng) -> Split:
    easy = rng.randint(0, 100)
    medium = rng.randint(0, 100 - easy)
    return Split(easy, medium, 100 - easy - medium)


def _matrix(counts) -> tuple:
    """A 4 x 3 matrix in BUCKETS x TIERS order from a ``{cell: count}`` map."""
    return tuple(tuple(counts[(bucket, tier)] for tier in TIERS) for bucket in BUCKETS)


def _case(rng, *, max_count=200, tight=None):
    """One ``(plan, planned cells, selection)``, near the tolerance either way.

    ``band`` is the largest per-cell difference that is still within 3 points
    of a book of ``count``. A ``tight`` case draws every difference inside it
    (so it must be accepted, and often sits exactly on the bound); a loose one
    draws from two units wider (so a cell one past the bound is common).
    """
    count = rng.randint(1, max_count)
    ceiling = max(1, count // 6)
    planned = {cell: rng.randint(0, ceiling) for cell in CELLS}

    band = 3 * count // 100
    window = band if (rng.random() < 0.5 if tight is None else tight) else band + 2
    selection = {
        cell: max(0, planned[cell] + rng.randint(-window, window)) for cell in CELLS
    }

    plan = DistributionPlan(count=count, split=_split(rng), cells=_matrix(planned))
    return plan, planned, selection


def _records(rng, selection):
    """The stored records of a selection, plus rows that belong to no cell.

    The noise rows are the two verdicts ``selection_cells`` makes on a record
    it cannot place — no recognisable tier, and a side outside the supported
    range — so the property also says those rows never move a cell.
    """
    records = [
        {"width": bucket.high, "height": bucket.low, "difficulty_tier": tier.value}
        for (bucket, tier), count in selection.items()
        for _ in range(count)
    ]
    for _ in range(rng.randint(0, 3)):
        records.append({"width": 12, "height": 12, "difficulty_tier": None})
        records.append({"width": MAX_SIZE + 5, "height": 12, "difficulty_tier": "easy"})
    rng.shuffle(records)
    return records


def _offenders(planned, selection, total):
    """The cells outside the tolerance, by exact fractions — the oracle."""
    return {
        cell
        for cell in CELLS
        if abs(Fraction(selection[cell], total) - Fraction(planned[cell], total))
        > TOLERANCE
    }


def test_the_tolerance_the_gate_uses_is_the_one_the_requirement_states() -> None:
    assert Fraction(READY_TOLERANCE_POINTS, 100) == TOLERANCE


def test_PropertyTest_BookReady_GateIffEveryCellWithinTolerance() -> None:
    """EC-025 — the gate's verdict is exactly the tolerance predicate."""
    rng = random.Random(20260923)
    accepted = refused = 0

    for case in range(CORPUS):
        plan, planned, selection = _case(rng)
        expected = _offenders(planned, selection, plan.count)

        refusal = ready_refusal(plan, _records(rng, selection))

        assert (refusal is None) == (not expected), (
            f"case {case}: the gate said {refusal!r} for {len(expected)} offending cell(s)"
        )
        if refusal is None:
            accepted += 1
        else:
            refused += 1

    assert accepted + refused >= MIN_CASES
    assert accepted >= MIN_PER_VERDICT, f"only {accepted} accepted case(s)"
    assert refused >= MIN_PER_VERDICT, f"only {refused} refused case(s)"


def test_a_refusal_names_every_offending_cell_and_no_other() -> None:
    rng = random.Random(4171)
    seen = 0

    for case in range(CORPUS):
        plan, planned, selection = _case(rng)
        expected = _offenders(planned, selection, plan.count)
        if not expected:
            continue

        refusal = ready_refusal(plan, _records(rng, selection))

        seen += 1
        assert refusal.count(" against ") == len(expected), f"case {case}: {refusal}"
        for bucket, tier in expected:
            assert f"{bucket.label} x {tier.value}:" in refusal, f"case {case}: {refusal}"

    assert seen >= MIN_PER_VERDICT, f"only {seen} refused case(s)"


def test_a_book_with_no_plan_is_always_refused() -> None:
    """The plan-less case: no selection can make up for a missing plan."""
    rng = random.Random(90210)

    for _ in range(CORPUS // 10):
        _plan, _planned, selection = _case(rng)

        refusal = ready_refusal(None, _records(rng, selection))

        assert refusal is not None
        assert "Print setup" in refusal


@pytest.mark.parametrize("mode", ("memory", "db"))
@pytest.mark.parametrize("target", NON_DRAFT)
def test_no_exit_from_draft_bypasses_it_in_either_storage_mode(
    mode, target, tmp_path
) -> None:
    """The same iff, through real books in real storage, for every target status.

    A smaller corpus — each case is a book and its puzzle records — but the
    same oracle, and it is what makes EC-025's "no route to the ready status
    bypasses the check" a measured claim rather than a reading of
    ``set_book_status``.
    """
    rng = random.Random(f"{mode}-{target}")
    shelf = Shelf(mode, None if mode == "memory" else sqlite_session_scope(tmp_path))
    accepted = refused = 0

    for case in range(STORAGE_CASES):
        plan, planned, selection = _case(rng, max_count=40, tight=case % 2 == 0)
        expected = _offenders(planned, selection, plan.count)
        book_id = shelf.book(selection, plan=plan, title=f"Book {case}")

        if expected:
            shelf.refusal(book_id, target)
            assert shelf.status(book_id) == BookStatus.DRAFT.value
            refused += 1
        else:
            assert shelf.books.set_book_status(book_id, target) is True
            assert shelf.status(book_id) == target
            accepted += 1

    assert accepted + refused == STORAGE_CASES
    assert accepted and refused, f"a one-sided corpus: {accepted} in, {refused} out"
