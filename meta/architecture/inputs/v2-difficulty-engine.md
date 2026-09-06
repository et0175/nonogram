# v2: Difficulty Engine Analysis (Strategy-Based)
**Status:** PRE-ARCHITECTURE RESEARCH  
**Purpose:** Gather empirical data to inform difficulty analyzer architecture  
**Reference:** docs/guides/monogram_analyzer.md (preliminary analysis)  
**Timeline:** Document ready by 2026-09-13, architecture by 2026-09-20

---

## Goal

Replace or enhance v1's **heuristic difficulty scoring** with **strategy-based analysis**:
- **v1:** Scoring based on solver signals (coverage, backtracking, time)
- **v2:** Scoring based on **count and complexity of solving strategies** (what the puzzle actually requires)

**Why:** Strategy count is more predictive of perceived difficulty than heuristics.

---

## Research Questions

### 1. **Strategy Taxonomy: What Strategies Count?**

From monogram_analyzer.md, identify the core strategies:

**To Research:**
- [ ] Line logic (naked singles, pointing pairs, etc.)
- [ ] Block elimination
- [ ] Constraint propagation depth
- [ ] Backtracking requirement
- [ ] Ambiguity (multiple solution branches explored)

**For each strategy:**
- How is it detected in solver code?
- How often does it appear in typical puzzles?
- Does it correlate with user-perceived difficulty?

### 2. **Empirical Correlation: Strategy Count → Difficulty**

**Data gathering:**
- Generate 100+ puzzles across sizes (10×10, 15×15, 20×20, 25×25, 30×30)
- Run solver on each, count strategies used
- Measure: total strategy count, unique strategies, backtracking depth
- Correlate with v1 heuristic score (Easy/Medium/Hard)

**Output:** Spreadsheet with columns:
| Grid Size | Random/Image | Strategy Count | Strategy Types | Backtrack Depth | v1 Difficulty | v1 Score |
|-----------|--------------|----------------|-----------------|-----------------|--------------|---------|
| 20×20 | random | 8 | line_logic, pointing_pairs | 2 | Easy | 45 |
| 20×20 | random | 15 | line_logic, block_elim, constraint_prop | 5 | Medium | 62 |
| etc. | | | | | | |

### 3. **Thresholds: When is a Puzzle "Easy" vs "Hard"?**

Based on empirical data:
- Easy threshold: strategy count < X, backtrack depth < Y
- Medium threshold: X ≤ strategy count < Z
- Hard threshold: strategy count ≥ Z, backtrack depth > Y

**Hypothesis (to test):**
- Easy: 1-5 strategies, no backtracking
- Medium: 6-12 strategies, shallow backtracking (1-3 levels)
- Hard: 13+ strategies, deep backtracking (4+ levels)

### 4. **Performance: Can We Afford Strategy Analysis?**

**Question:** How long does strategy counting add to generation?
- v1 solve time: X ms (baseline)
- v2 solve + strategy count: Y ms
- Acceptable overhead: < 20% (don't slow down generation)

### 5. **Special Cases: Image Mode**

**Question:** Do strategies vary for image-sourced vs. random puzzles?
- Image puzzles often have simpler structure (dense clues)
- Do they require fewer strategies?
- Does difficulty score need adjustment for image mode?

---

## Acceptance Criteria

Documentation is ready when you can answer:

- [ ] What 5-10 core strategies define difficulty?
- [ ] How does strategy count correlate with user-perceived difficulty?
- [ ] What are the thresholds (Easy: count < X, Medium: X-Y, Hard: > Y)?
- [ ] Is strategy analysis overhead acceptable (< 20%)?
- [ ] How do image-mode puzzles differ from random?

---

## Deliverable (by 2026-09-13)

**File:** `meta/architecture/inputs/difficulty-analysis.md` (this file, updated)

**Sections:**
1. Strategy Taxonomy (defined)
2. Empirical Data (spreadsheet summary)
3. Thresholds (Easy/Medium/Hard definitions)
4. Performance Impact (overhead measured)
5. Image Mode Specifics (if applicable)
6. Open Questions (anything unclear?)

---

## Implementation Notes (Not for v1)

Once analysis is complete, v2 will need:

**New Module:** `src/nonogram/analysis/strategy_counter.py`
- Instrument solver to count strategies
- Return strategy breakdown (type, count, depth)

**New FR:** FR-029 - "Analyze puzzle strategies to determine difficulty"
- Input: Puzzle (grid + clues)
- Output: strategy_count, strategy_types, difficulty (Easy/Medium/Hard)

**New Capability:** CAP-006 - Puzzle Analysis
- Separate from CAP-004 (Difficulty Calibration)
- Question: Replace heuristic or run both?

---

**Next Action:** Start gathering empirical data this week. Document findings by 2026-09-13.
