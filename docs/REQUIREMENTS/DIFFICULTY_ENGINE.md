# Strategy-Based Difficulty Engine

**Purpose:** Estimate puzzle difficulty based on solving strategies required  
**Status:** MVP Implementation Complete  
**Version:** 1.0 (POC)

---

## Overview

The difficulty engine analyzes nonogram puzzles by tracking the **solving strategies** required to reach a solution. This is more intuitive than heuristic scoring because it measures what a human solver actually needs to do.

**Key insight:** A puzzle requiring 5 different strategies is fundamentally harder than one solvable by 1 strategy, regardless of size.

---

## Strategy Taxonomy

Six core solving strategies are tracked:

### 1. **Line Logic** (Most Basic)
- **Description:** Cells that must be filled or empty based on clue constraints
- **Examples:** 
  - A row of 5 with clue "5" → all cells filled
  - A row of 10 with clue "3" → cells outside the 3-block are empty
  - Pointing pairs: Two possible positions for a block, one in each of two clues
- **Difficulty:** Low (foundational)
- **Frequency:** Every puzzle requires at least this

### 2. **Constraint Propagation** (Basic)
- **Description:** Eliminating possibilities by combining row and column constraints
- **Examples:**
  - If row has only one valid placement for a block, column eliminates other possibilities
  - Cascading: Filling cells in one direction constrains perpendicular clues
- **Difficulty:** Low-Medium
- **Frequency:** Most puzzles need 1-2 rounds

### 3. **Block Elimination** (Intermediate)
- **Description:** Determining which block placements are impossible
- **Examples:**
  - A clue "2,3" needs 2 blocks of sizes 2 and 3, checking spacing
  - Blocks that overlap contradictory cells can be eliminated
- **Difficulty:** Medium
- **Frequency:** Random 20×20+ puzzles

### 4. **Pointing Pairs** (Intermediate)
- **Description:** A block in one clue can only go in positions that also satisfy another clue
- **Examples:**
  - Row clue "4" can only be at positions 1-4 or 6-9
  - Column clue "3" intersects only with positions 1-4
  - Conclusion: Row's "4" block must be at 1-4
- **Difficulty:** Medium
- **Frequency:** Moderately complex puzzles

### 5. **Backtracking** (Advanced)
- **Description:** Guessing at ambiguous positions and exploring solution branches
- **Examples:**
  - Multiple valid placements exist after logic-based solving
  - Must try position A: if contradiction, try position B
  - Deep backtracking: Nested guesses (guess 1, then guess 2 within guess 1's path)
- **Difficulty:** High
- **Frequency:** Random 25×25+ or specially designed puzzles
- **Metric:** `backtracking_depth` tracks maximum nesting (0 = no guessing, 5+ = very deep)

### 6. **Ambiguity** (Complex)
- **Description:** Multiple branches explored during search (high branch count)
- **Examples:**
  - Unclear ordering of blocks requires exploring many possibilities
  - Puzzles with poor constraint propagation (many ambiguous cells)
- **Difficulty:** Very High
- **Frequency:** Rare; usually indicates poor puzzle design
- **Metric:** `branch_count` tracks how many distinct paths were explored

---

## Difficulty Scoring

### Score Calculation (0-100)

Difficulty score combines three components:

**1. Strategy Complexity (0-40 points)**
- Each unique strategy type adds weight (line logic < constraint propagation < block elimination < pointing pairs)
- Multiple applications of the same strategy also add weight
- Formula: `min(40, (unique_count * 40) / 6 + total_applications / 5)`

**2. Backtracking Requirement (0-35 points)**
- No backtracking: 0 points
- Shallow (depth 1-3): 10-20 points
- Deep (depth 4+): 25-35 points
- Formula: 
  - depth 0: 0
  - depth 1-3: `depth * 7` (capped at 20)
  - depth 4+: `20 + (depth - 3) * 5` (capped at 35)

**3. Ambiguity / Branching (0-25 points)**
- More branches explored = more ambiguous = harder
- Formula: `min(25, branch_count * 25 / 10)`

**Total:** `strategy_score + backtracking_score + ambiguity_score` (capped at 100)

### Difficulty Tiers

| Tier | Score | Characteristics | Example |
|------|-------|-----------------|---------|
| **Easy** | 0-29 | Pure line logic, no backtracking | 10×10 random, dense clues |
| **Medium** | 30-69 | Mixed strategies, shallow backtracking (1-3 levels) | 20×20 random, moderate clues |
| **Hard** | 70-100 | Multiple strategies, deep backtracking (4+), high branching | 25×25+, sparse clues |

---

## Example Scorings

### Example 1: Easy 10×10 Random Puzzle
```
Strategy Counter:
  - Line Logic: 4 applications
  - Constraint Propagation: 2 applications
  - Backtracking: 0 levels
  - Branches: 0

Calculation:
  - Unique strategies: 2 → (2 * 40) / 6 = 13 points
  - Total applications: 6 → 6 / 5 = 1 point  
  - Strategy score: 13 + 1 = 14 points
  - Backtracking: 0 points
  - Ambiguity: 0 points
  - Total: 14/100 → EASY ✓
```

### Example 2: Medium 20×20 Random Puzzle
```
Strategy Counter:
  - Line Logic: 8 applications
  - Constraint Propagation: 6 applications
  - Block Elimination: 3 applications
  - Pointing Pairs: 2 applications
  - Backtracking: 2 levels
  - Branches: 2

Calculation:
  - Unique strategies: 4 → (4 * 40) / 6 = 27 points
  - Total applications: 19 → 19 / 5 = 4 points
  - Strategy score: 31 points
  - Backtracking depth 2: 2 * 7 = 14 points
  - Ambiguity: 2 * 25 / 10 = 5 points
  - Total: 31 + 14 + 5 = 50/100 → MEDIUM ✓
```

### Example 3: Hard 30×30 Random Puzzle
```
Strategy Counter:
  - Line Logic: 15 applications
  - Constraint Propagation: 12 applications
  - Block Elimination: 8 applications
  - Pointing Pairs: 6 applications
  - Ambiguity: 4 applications
  - Backtracking: 5 levels
  - Branches: 8

Calculation:
  - Unique strategies: 5 → (5 * 40) / 6 = 33 points
  - Total applications: 45 → 45 / 5 = 9 points
  - Strategy score: 42 points
  - Backtracking depth 5: 20 + (5-3)*5 = 30 points
  - Ambiguity: 8 * 25 / 10 = 20 points
  - Total: 42 + 30 + 20 = 92/100 → HARD ✓
```

---

## Implementation

### Core Module: `src/nonogram/analysis/strategy_counter.py`

```python
from src.nonogram.analysis import (
    StrategyCounter, 
    Strategy,
    calculate_difficulty_from_strategies
)

# During solving, track strategies
counter = StrategyCounter()
counter.add_strategy(Strategy.LINE_LOGIC, count=5)
counter.add_strategy(Strategy.CONSTRAINT_PROPAGATION, count=3)
counter.set_backtracking_depth(2)

# Calculate difficulty
score, tier = calculate_difficulty_from_strategies(counter)
print(f"Difficulty: {score}/100 ({tier})")
```

### Integration Points

**Where used:**
1. **Puzzle Generator** → After solver runs, calculate difficulty
2. **Admin Panel** → Display difficulty metrics for review
3. **Database** → Store difficulty_score, difficulty_tier, strategies_used
4. **User Display** → Show "Easy/Medium/Hard" badge on generated puzzles

**Database Fields (Nonogram table):**
```sql
difficulty_score INT          -- 1-100
difficulty_tier VARCHAR       -- 'Easy', 'Medium', 'Hard'
strategies_used TEXT[]        -- ['line_logic', 'constraint_propagation', ...]
backtracking_depth INT        -- 0-10
```

---

## Validation & Tuning

### Empirical Data Gathering (Future)

To validate thresholds, generate 100+ test puzzles:

```
Size   Mode    Strategies  Depth  Score  Tier     Actual Difficulty
10×10  random  2           0      15     Easy     ✓ Easy (5 min)
15×15  random  3           1      28     Easy     ~ Medium (10 min)
20×20  random  4           2      50     Medium   ✓ Medium (20 min)
25×25  random  5           4      85     Hard     ✓ Hard (45 min)
30×30  random  6           5      95     Hard     ✓ Hard (60+ min)
```

Correlation: Does strategy count match human perception?

### Performance Impact

Overhead of strategy tracking should be < 20% of solve time:
- v1 solve time (heuristic): 50ms (baseline)
- v2 solve time (with tracking): 55-60ms (acceptable: < 60ms)

If overhead > 20%, optimize:
- Cache strategy checks
- Reduce propagation analysis depth
- Sample large puzzles instead of full analysis

---

## Known Limitations (v1)

1. **No machine learning:** Uses empirical thresholds, not trained model
2. **Static thresholds:** May need tuning for different user populations
3. **No puzzle style differentiation:** Random vs. image puzzles might need different scoring
4. **No advanced strategies:** Missing symmetry detection, coloring, etc.

**Future work (v2+):**
- Gather empirical difficulty ratings from users
- Train ML model on strategy features
- Add puzzle style weighting
- Implement advanced strategies

---

## References

- **Solving Techniques:** docs/guides/solving_techniques.md
- **Strategy Counter Tests:** tests/test_strategy_counter.py
- **Solver Integration:** (To be implemented in next phase)

---

**Last Updated:** 2026-09-06  
**Status:** ✅ MVP Complete  
**Next:** Integrate into solver pipeline
