"""Analysis module for puzzle metrics: difficulty, quality, and strategy tracking."""

from .strategy_counter import (
    Strategy,
    StrategyCounter,
    calculate_difficulty_from_strategies,
)

__all__ = [
    "Strategy",
    "StrategyCounter",
    "calculate_difficulty_from_strategies",
]
