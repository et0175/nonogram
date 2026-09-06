"""Strategy-based difficulty analysis for nonogram puzzles.

Tracks solving techniques used during puzzle solution to determine difficulty.
Strategies identified:
- Line Logic: Naked singles (cells that must be filled/empty)
- Constraint Propagation: Eliminating possibilities based on clue constraints
- Backtracking: Need to guess and explore branches
- Block Elimination: Removing impossible block placements
- Ambiguity: Multiple solution paths explored
"""

from dataclasses import dataclass, field
from typing import Set, List, Tuple
from enum import Enum


class Strategy(Enum):
    """Core solving strategies used in nonogram solver."""

    LINE_LOGIC = "line_logic"  # Naked singles detection
    CONSTRAINT_PROPAGATION = "constraint_propagation"  # Clue-based elimination
    BLOCK_ELIMINATION = "block_elimination"  # Block placement logic
    POINTING_PAIRS = "pointing_pairs"  # Same block across multiple lines
    BACKTRACKING = "backtracking"  # Guess and explore
    AMBIGUITY = "ambiguity"  # Multiple branches explored


@dataclass
class StrategyCounter:
    """Tracks strategy usage during puzzle solving.

    Attributes:
        strategies_used: Set of strategies applied
        strategy_count: Total count of individual strategy applications
        backtracking_depth: Maximum depth of backtracking required
        branch_count: Number of branches explored (related to ambiguity)
        propagation_rounds: How many rounds of constraint propagation needed
    """

    strategies_used: Set[Strategy] = field(default_factory=set)
    strategy_count: int = 0
    backtracking_depth: int = 0
    branch_count: int = 0
    propagation_rounds: int = 0

    def add_strategy(self, strategy: Strategy, count: int = 1) -> None:
        """Record use of a solving strategy.

        Args:
            strategy: The strategy used
            count: How many times this strategy was applied (default: 1)
        """
        self.strategies_used.add(strategy)
        self.strategy_count += count

    def set_backtracking_depth(self, depth: int) -> None:
        """Record maximum backtracking depth required.

        Args:
            depth: Maximum depth of nested guesses
        """
        self.backtracking_depth = max(self.backtracking_depth, depth)

    def increment_branches(self) -> None:
        """Record exploration of a new solution branch."""
        self.branch_count += 1

    def increment_propagation_round(self) -> None:
        """Record one round of constraint propagation."""
        self.propagation_rounds += 1

    def get_unique_strategy_count(self) -> int:
        """How many different strategies were used."""
        return len(self.strategies_used)

    def get_strategy_names(self) -> List[str]:
        """Get list of strategy names used."""
        return sorted([s.value for s in self.strategies_used])

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "strategies_used": self.get_strategy_names(),
            "unique_strategy_count": self.get_unique_strategy_count(),
            "total_strategy_applications": self.strategy_count,
            "backtracking_depth": self.backtracking_depth,
            "branch_count": self.branch_count,
            "propagation_rounds": self.propagation_rounds,
        }


def calculate_difficulty_from_strategies(counter: StrategyCounter) -> Tuple[int, str]:
    """Convert strategy metrics into difficulty score and tier.

    Uses empirical thresholds based on strategy complexity.

    Args:
        counter: StrategyCounter with metrics from solving

    Returns:
        Tuple of (difficulty_score: 1-100, difficulty_tier: "Easy"|"Medium"|"Hard")
    """

    # Scoring components (each out of ~100)
    strategy_score = 0
    backtracking_score = 0
    ambiguity_score = 0

    # 1. Strategy complexity (0-40 points)
    unique_count = counter.get_unique_strategy_count()
    total_count = counter.strategy_count

    # More strategies = harder
    # Max 6 strategies, normalize to 0-40
    strategy_score = min(40, (unique_count * 40) // 6)
    # Multiple applications of same strategy also indicates complexity
    strategy_score = min(40, strategy_score + (total_count // 5))

    # 2. Backtracking (0-35 points)
    # No backtracking: 0 points
    # Shallow backtracking (1-3 levels): 10-20 points
    # Deep backtracking (4+ levels): 25-35 points
    if counter.backtracking_depth == 0:
        backtracking_score = 0
    elif counter.backtracking_depth <= 3:
        backtracking_score = min(20, counter.backtracking_depth * 7)
    else:
        backtracking_score = min(35, 20 + (counter.backtracking_depth - 3) * 5)

    # 3. Ambiguity / Branch exploration (0-25 points)
    # More branches = more ambiguity = harder
    ambiguity_score = min(25, (counter.branch_count * 25) // 10)

    # Total score (0-100)
    difficulty_score = min(100, strategy_score + backtracking_score + ambiguity_score)

    # Determine tier based on score
    if difficulty_score < 30:
        tier = "Easy"
    elif difficulty_score < 70:
        tier = "Medium"
    else:
        tier = "Hard"

    return difficulty_score, tier


if __name__ == "__main__":
    # Example usage
    counter = StrategyCounter()
    counter.add_strategy(Strategy.LINE_LOGIC, 5)
    counter.add_strategy(Strategy.CONSTRAINT_PROPAGATION, 3)
    counter.set_backtracking_depth(2)
    counter.increment_branches()

    score, tier = calculate_difficulty_from_strategies(counter)
    print(f"Difficulty Score: {score}/100")
    print(f"Difficulty Tier: {tier}")
    print(f"Strategies: {counter.to_dict()}")
