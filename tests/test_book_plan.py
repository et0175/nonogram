"""CARD-119 — the distribution plan as pure domain (FR-034, FR-035, FR-036).

Unit tests for ``nonogram.admin.book_plan``. The route halves of AC-197 and the
rendered-tab halves of AC-208..AC-210 are CARD-120/CARD-122's; these tests pin
the domain half each criterion rests on.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from nonogram.admin import book_plan
from nonogram.admin.book_plan import (
    BUCKETS,
    DEFAULT_PLAN,
    TIERS,
    DistributionPlan,
    InvalidPlan,
    LongestSideBucket,
    Split,
    bucket_of,
    planned_cells,
    prefill,
    selection_cells,
    tier_counts,
    with_edited_cell,
    with_split,
)
from nonogram.difficulty import Tier
from nonogram.errors import SizeOutOfRange
from nonogram.limits import MAX_SIZE, MIN_SIZE

B15, B20, B25, B30 = BUCKETS
E, M, H = TIERS


def _columns(plan: DistributionPlan) -> tuple[int, int, int]:
    return tuple(sum(row[t] for row in plan.cells) for t in range(3))  # type: ignore[return-value]


class TestBookPlan_RejectsSplitNotSummingTo100:
    """AC-197 (INV-005), domain half: construction refuses a split that is not 100%."""

    def test_forty_forty_thirty_is_refused(self) -> None:
        with pytest.raises(InvalidPlan, match="100"):
            Split(40, 40, 30)

    @pytest.mark.parametrize("shares", [(40, 40, 19), (0, 0, 0), (50, 50, 1), (101, -1, 0)])
    def test_other_bad_splits_are_refused(self, shares: tuple[int, int, int]) -> None:
        with pytest.raises(InvalidPlan):
            Split(*shares)

    @pytest.mark.parametrize("shares", [(40.0, 40, 20), (True, 79, 20), ("40", 40, 20)])
    def test_non_whole_percent_is_refused(self, shares: tuple) -> None:
        with pytest.raises(InvalidPlan):
            Split(*shares)

    def test_the_stored_plan_is_untouched_by_a_refused_split(self) -> None:
        stored = prefill(150, Split(40, 40, 20))
        with pytest.raises(InvalidPlan):
            with_split(stored, Split(40, 40, 30))
        assert stored == DEFAULT_PLAN
        assert (stored.count, stored.split) == (150, Split(40, 40, 20))

    def test_a_split_summing_to_100_is_accepted(self) -> None:
        assert Split(100, 0, 0).percent(Tier.EASY) == 100


class TestBookPlan_InvariantsAtConstruction:
    @pytest.mark.parametrize("count", [0, -5, 1.5, True, "150"])
    def test_count_must_be_a_positive_whole_number(self, count: object) -> None:
        with pytest.raises(InvalidPlan):
            DistributionPlan(count=count, split=Split(40, 40, 20), cells=DEFAULT_PLAN.cells)  # type: ignore[arg-type]

    def test_negative_cell_is_refused(self) -> None:
        cells = [list(r) for r in DEFAULT_PLAN.cells]
        cells[0][0] = -1
        with pytest.raises(InvalidPlan):
            DistributionPlan(count=150, split=Split(40, 40, 20), cells=cells)  # type: ignore[arg-type]

    def test_wrong_shape_is_refused(self) -> None:
        with pytest.raises(InvalidPlan):
            DistributionPlan(count=150, split=Split(40, 40, 20), cells=DEFAULT_PLAN.cells[:3])

    def test_split_must_be_a_split(self) -> None:
        with pytest.raises(InvalidPlan):
            DistributionPlan(count=150, split=(40, 40, 20), cells=DEFAULT_PLAN.cells)  # type: ignore[arg-type]

    def test_plan_is_frozen(self) -> None:
        with pytest.raises(AttributeError):
            DEFAULT_PLAN.count = 1  # type: ignore[misc]


class TestBookPlan_PrefillMatchesBook1MatrixAt150x40_40_20:
    """AC-198 — pins the earlier-bucket tie-break (medium 60 -> 7/27/20/6)."""

    def test_matrix(self) -> None:
        plan = prefill(150, Split(40, 40, 20))
        assert plan.cells == (
            (20, 7, 0),
            (30, 27, 6),
            (10, 20, 12),
            (0, 6, 12),
        )
        assert plan.edited == frozenset()
        assert not plan.disagrees_with_split

    def test_default_plan_is_that_prefill(self) -> None:
        """ADR-0034: the default is 150 at 40/40/20 (60/60/30) with this matrix."""
        assert DEFAULT_PLAN == prefill(150, Split(40, 40, 20))
        assert DEFAULT_PLAN.tier_counts == (60, 60, 30)

    def test_default_plan_is_a_constant_not_a_function_of_audience(self) -> None:
        """G-1: a value, not a callable, and no plan function takes an audience."""
        import inspect

        assert isinstance(book_plan.DEFAULT_PLAN, DistributionPlan)
        for fn in (prefill, with_split, tier_counts):
            assert not any("audience" in p for p in inspect.signature(fn).parameters)


class TestBookPlan_TierCounts:
    def test_whole_counts(self) -> None:
        assert tier_counts(150, Split(40, 40, 20)) == (60, 60, 30)
        assert tier_counts(120, Split(30, 45, 25)) == (36, 54, 30)

    def test_137_at_40_40_20_rounds_by_largest_remainder(self) -> None:
        # 54.8 / 54.8 / 27.4 -> floors 54/54/27 (135), remainders .8/.8/.4 -> 55/55/27
        assert tier_counts(137, Split(40, 40, 20)) == (55, 55, 27)

    def test_equal_remainders_go_to_the_earlier_tier(self) -> None:
        # 150 at 30/45/25 = 45 / 67.5 / 37.5: one spare unit, tie -> medium
        assert tier_counts(150, Split(30, 45, 25)) == (45, 68, 37)
        # 1 at 34/33/33: 0.34/0.33/0.33 -> easy
        assert tier_counts(1, Split(34, 33, 33)) == (1, 0, 0)
        # 1 at 0/50/50: tie between medium and hard -> medium
        assert tier_counts(1, Split(0, 50, 50)) == (0, 1, 0)


class TestBookPlan_PrefillColumnTotalsMatchGeneralPlan:
    """AC-199 — 120 at 30/45/25 (36/54/30)."""

    def test_totals(self) -> None:
        plan = prefill(120, Split(30, 45, 25))
        assert sum(map(sum, plan.cells)) == 120
        assert _columns(plan) == (36, 54, 30)
        assert not plan.disagrees_with_split


class TestBookPlan_ZeroShareCellsStayZero:
    """AC-200 — <=15 x hard and 26-30 x easy are 0."""

    def test_zero_share_cells(self) -> None:
        plan = prefill(120, Split(30, 45, 25))
        assert plan.cell(B15, H) == 0
        assert plan.cell(B30, E) == 0

    def test_even_when_a_tier_is_the_whole_book(self) -> None:
        assert prefill(7, Split(100, 0, 0)).cell(B30, E) == 0
        assert prefill(7, Split(0, 0, 100)).cell(B15, H) == 0


class TestBookPlan_UneditedMatrixRederivedOnSplitChange:
    """AC-201 (POL-007)."""

    def test_rederived(self) -> None:
        stored = prefill(150, Split(40, 40, 20))
        changed = with_split(stored, Split(30, 45, 25))
        assert changed == prefill(150, Split(30, 45, 25))
        assert changed.split == Split(30, 45, 25)
        assert _columns(changed) == (45, 68, 37)
        assert not changed.disagrees_with_split


class TestBookPlan_HandEditedCellSurvivesSplitChange:
    """AC-202 (POL-007)."""

    def test_edited_cell_keeps_its_value(self) -> None:
        stored = with_edited_cell(prefill(150, Split(40, 40, 20)), B25, H, 15)
        assert stored.cell(B25, H) == 15
        assert stored.edited == {(B25, H)}
        changed = with_split(stored, Split(30, 45, 25))
        assert changed.cell(B25, H) == 15
        assert changed.edited == {(B25, H)}
        # Every unedited cell is its prefill value at the new split.
        fresh = prefill(150, Split(30, 45, 25))
        for bucket in BUCKETS:
            for tier in TIERS:
                if (bucket, tier) != (B25, H):
                    assert changed.cell(bucket, tier) == fresh.cell(bucket, tier)

    def test_disagreement_is_reported_when_the_edit_breaks_the_column(self) -> None:
        stored = with_edited_cell(DEFAULT_PLAN, B25, H, 20)
        assert stored.disagrees_with_split
        changed = with_split(stored, Split(30, 45, 25))
        assert changed.cell(B25, H) == 20
        assert changed.disagrees_with_split

    def test_editing_a_zero_share_cell_is_allowed(self) -> None:
        edited = with_edited_cell(DEFAULT_PLAN, B15, H, 3)
        assert edited.cell(B15, H) == 3
        assert edited.disagrees_with_split

    def test_edit_refuses_a_negative_value(self) -> None:
        with pytest.raises(InvalidPlan):
            with_edited_cell(DEFAULT_PLAN, B15, E, -1)


class TestBookSelect_PuzzleListedUnderLongestSideTab:
    """AC-208, bucket-function half: 15 wide x 30 tall is 26-30."""

    def test_fifteen_by_thirty(self) -> None:
        assert bucket_of(15, 30) is LongestSideBucket.FROM_26_TO_30
        assert bucket_of(30, 15) is LongestSideBucket.FROM_26_TO_30


class TestBookSelect_LongestSideSixteenGoesToSecondTab:
    """AC-209, bucket-function half."""

    def test_fifteen_by_sixteen(self) -> None:
        assert bucket_of(15, 16) is LongestSideBucket.FROM_16_TO_20
        assert bucket_of(15, 16) is not LongestSideBucket.UP_TO_15


class TestBookSelect_LongestSideFifteenGoesToFirstTab:
    """AC-210, bucket-function half."""

    def test_fifteen_by_fifteen(self) -> None:
        assert bucket_of(15, 15) is LongestSideBucket.UP_TO_15


class TestBucketOf_RefusesOutOfRange:
    @pytest.mark.parametrize("extent", [(MIN_SIZE - 1, 15), (15, MAX_SIZE + 1), (40, 40)])
    def test_refused(self, extent: tuple[int, int]) -> None:
        with pytest.raises(SizeOutOfRange):
            bucket_of(*extent)

    def test_labels_are_the_tab_labels(self) -> None:
        assert [b.label for b in BUCKETS] == ["<=15", "16-20", "21-25", "26-30"]


class TestPlannedAndSelectionCells:
    def test_planned_cells_has_every_key(self) -> None:
        cells = planned_cells(DEFAULT_PLAN)
        assert len(cells) == 12
        assert cells[(B20, M)] == 27
        assert sum(cells.values()) == 150

    def test_selection_reads_stored_tier_under_either_spelling(self) -> None:
        puzzles = [
            {"width": 15, "height": 30, "difficulty_tier": "hard"},
            {"width": 10, "height": 10, "difficulty_tier": "Easy"},
            {"width": 16, "height": 15, "difficulty_tier": "MEDIUM"},
            {"width": 25, "height": 12, "difficulty_tier": "guess"},  # retired -> Hard
        ]
        cells = selection_cells(puzzles)
        assert set(cells) == set(planned_cells(DEFAULT_PLAN))
        assert cells[(B30, H)] == 1
        assert cells[(B15, E)] == 1
        assert cells[(B20, M)] == 1
        assert cells[(B25, H)] == 1
        assert sum(cells.values()) == 4

    def test_selection_skips_ungraded_and_out_of_range_records(self) -> None:
        puzzles = [
            {"width": 15, "height": 15, "difficulty_tier": None},
            {"width": 15, "height": 15, "difficulty_tier": "extreme"},
            {"width": 40, "height": 40, "difficulty_tier": "hard"},
            {"width": 15, "height": 15},
        ]
        assert sum(selection_cells(puzzles).values()) == 0

    def test_selection_never_regrades(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """G-3: only the stored tier is read; the grader is never called."""
        import nonogram.difficulty as difficulty

        def boom(*_a: object, **_k: object) -> None:
            raise AssertionError("re-graded")

        for name in ("score_difficulty", "classify"):
            if hasattr(difficulty, name):
                monkeypatch.setattr(difficulty, name, boom)
        assert selection_cells([{"width": 12, "height": 12, "difficulty_tier": "easy"}])[(B15, E)] == 1


class TestBookPlan_PureDomainImports:
    """G-2: book_plan imports no database, Flask or templates."""

    def test_imports(self) -> None:
        tree = ast.parse(Path(book_plan.__file__).read_text())
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        forbidden = {m for m in modules if m.startswith(("nonogram.db", "flask", "jinja2", "sqlalchemy"))}
        assert forbidden == set()
        assert not any("template" in m for m in modules)
