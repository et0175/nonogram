"""Analysis module for puzzle metrics: difficulty, quality, and strategy tracking."""

from .strategy_counter import (
    Strategy,
    StrategyCounter,
    calculate_difficulty_from_strategies,
)
from .quality_metric import (
    Recognizability,
    QualityMetrics,
    measure_quality,
    calculate_visual_similarity,
    calculate_silhouette_match,
    calculate_density_match,
)

__all__ = [
    # Strategy-based difficulty
    "Strategy",
    "StrategyCounter",
    "calculate_difficulty_from_strategies",
    # Quality metrics
    "Recognizability",
    "QualityMetrics",
    "measure_quality",
    "calculate_visual_similarity",
    "calculate_silhouette_match",
    "calculate_density_match",
]
