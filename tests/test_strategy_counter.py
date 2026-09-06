"""Tests for strategy-based difficulty analysis."""

import pytest
from src.nonogram.analysis.strategy_counter import (
    StrategyCounter,
    Strategy,
    calculate_difficulty_from_strategies,
)


class TestStrategyCounter:
    """Test StrategyCounter data tracking."""

    def test_add_strategy_single(self):
        """Test adding a single strategy."""
        counter = StrategyCounter()
        counter.add_strategy(Strategy.LINE_LOGIC)

        assert Strategy.LINE_LOGIC in counter.strategies_used
        assert counter.strategy_count == 1
        assert counter.get_unique_strategy_count() == 1

    def test_add_strategy_multiple_same(self):
        """Test adding same strategy multiple times."""
        counter = StrategyCounter()
        counter.add_strategy(Strategy.LINE_LOGIC, 5)

        assert counter.strategy_count == 5
        assert counter.get_unique_strategy_count() == 1

    def test_add_multiple_strategies(self):
        """Test adding different strategies."""
        counter = StrategyCounter()
        counter.add_strategy(Strategy.LINE_LOGIC, 3)
        counter.add_strategy(Strategy.CONSTRAINT_PROPAGATION, 2)
        counter.add_strategy(Strategy.BACKTRACKING, 1)

        assert counter.strategy_count == 6
        assert counter.get_unique_strategy_count() == 3
        assert Strategy.LINE_LOGIC in counter.strategies_used
        assert Strategy.CONSTRAINT_PROPAGATION in counter.strategies_used
        assert Strategy.BACKTRACKING in counter.strategies_used

    def test_get_strategy_names_sorted(self):
        """Test that strategy names are returned sorted."""
        counter = StrategyCounter()
        counter.add_strategy(Strategy.BACKTRACKING)
        counter.add_strategy(Strategy.LINE_LOGIC)
        counter.add_strategy(Strategy.CONSTRAINT_PROPAGATION)

        names = counter.get_strategy_names()
        assert names == sorted(names)
        assert len(names) == 3

    def test_backtracking_depth_tracking(self):
        """Test backtracking depth is tracked correctly."""
        counter = StrategyCounter()
        counter.set_backtracking_depth(2)
        counter.set_backtracking_depth(1)  # Should keep max
        counter.set_backtracking_depth(5)

        assert counter.backtracking_depth == 5

    def test_branch_counting(self):
        """Test branch exploration counting."""
        counter = StrategyCounter()
        for _ in range(3):
            counter.increment_branches()

        assert counter.branch_count == 3

    def test_to_dict_serialization(self):
        """Test conversion to dictionary."""
        counter = StrategyCounter()
        counter.add_strategy(Strategy.LINE_LOGIC, 5)
        counter.add_strategy(Strategy.CONSTRAINT_PROPAGATION, 2)
        counter.set_backtracking_depth(3)
        counter.increment_branches()
        counter.increment_propagation_round()

        d = counter.to_dict()
        assert d["total_strategy_applications"] == 7
        assert d["unique_strategy_count"] == 2
        assert d["backtracking_depth"] == 3
        assert d["branch_count"] == 1
        assert d["propagation_rounds"] == 1


class TestDifficultyCalculation:
    """Test difficulty score calculation from strategies."""

    def test_easy_puzzle_no_backtracking(self):
        """Easy puzzle: few strategies, no backtracking."""
        counter = StrategyCounter()
        counter.add_strategy(Strategy.LINE_LOGIC, 2)

        score, tier = calculate_difficulty_from_strategies(counter)

        assert tier == "Easy"
        assert score < 30

    def test_medium_puzzle_shallow_backtracking(self):
        """Medium puzzle: moderate strategies, shallow backtracking."""
        counter = StrategyCounter()
        counter.add_strategy(Strategy.LINE_LOGIC, 3)
        counter.add_strategy(Strategy.CONSTRAINT_PROPAGATION, 3)
        counter.add_strategy(Strategy.POINTING_PAIRS, 2)
        counter.set_backtracking_depth(2)

        score, tier = calculate_difficulty_from_strategies(counter)

        assert tier == "Medium"
        assert 30 <= score < 70

    def test_hard_puzzle_deep_backtracking(self):
        """Hard puzzle: many strategies, deep backtracking."""
        counter = StrategyCounter()
        counter.add_strategy(Strategy.LINE_LOGIC, 5)
        counter.add_strategy(Strategy.CONSTRAINT_PROPAGATION, 5)
        counter.add_strategy(Strategy.BLOCK_ELIMINATION, 3)
        counter.add_strategy(Strategy.POINTING_PAIRS, 4)
        counter.add_strategy(Strategy.AMBIGUITY, 3)
        counter.set_backtracking_depth(5)
        for _ in range(5):
            counter.increment_branches()

        score, tier = calculate_difficulty_from_strategies(counter)

        assert tier == "Hard"
        assert score >= 70

    def test_score_is_normalized_0_to_100(self):
        """Difficulty score is always between 0 and 100."""
        counter = StrategyCounter()
        # Extreme case: max out everything
        counter.add_strategy(Strategy.LINE_LOGIC, 100)
        counter.add_strategy(Strategy.CONSTRAINT_PROPAGATION, 100)
        counter.add_strategy(Strategy.BACKTRACKING, 100)
        counter.set_backtracking_depth(100)
        for _ in range(100):
            counter.increment_branches()

        score, tier = calculate_difficulty_from_strategies(counter)

        assert 0 <= score <= 100

    def test_empty_puzzle_is_easy(self):
        """A puzzle with no strategies is Easy."""
        counter = StrategyCounter()
        score, tier = calculate_difficulty_from_strategies(counter)

        assert tier == "Easy"
        assert score == 0

    def test_backtracking_matters(self):
        """Backtracking depth significantly affects difficulty."""
        counter1 = StrategyCounter()
        counter1.add_strategy(Strategy.LINE_LOGIC, 3)

        counter2 = StrategyCounter()
        counter2.add_strategy(Strategy.LINE_LOGIC, 3)
        counter2.set_backtracking_depth(4)

        score1, _ = calculate_difficulty_from_strategies(counter1)
        score2, _ = calculate_difficulty_from_strategies(counter2)

        assert score2 > score1

    def test_ambiguity_increases_difficulty(self):
        """More branches explored = higher difficulty."""
        counter1 = StrategyCounter()
        counter1.add_strategy(Strategy.LINE_LOGIC, 3)

        counter2 = StrategyCounter()
        counter2.add_strategy(Strategy.LINE_LOGIC, 3)
        for _ in range(5):
            counter2.increment_branches()

        score1, _ = calculate_difficulty_from_strategies(counter1)
        score2, _ = calculate_difficulty_from_strategies(counter2)

        assert score2 > score1
