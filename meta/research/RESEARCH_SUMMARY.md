# Market Research Summary — Nonogram Business Channels
**Date**: 2026-09-04  
**Scope**: Three business models (Amazon KDP books, online generator, online solver)

## Executive Summary

**Unique Opportunity**: Uniqueness verification (solver check) + batch PDF aggregation are differentiated features that no competitor offers. First-mover window for KDP positioning is open.

**Market Sizing**:
- KDP nonogram books: $2–5M annual (531 titles, $13–15 price band)
- Online solver games: $500M+ (Katana dominates at 4.8★, 10+ year history)
- Generator tools: $50–200M (nascent, zero monetization models)

## Leaders Researched

### LDR-001: Amazon KDP Market Segment
- **Size**: 531 searchable titles
- **Pricing**: $9–12 Kindle (25%), $13–15 paperback (50%), $15–20 (20%), $20+ (5%)
- **Pain**: No uniqueness verification → reputation risk from duplicate/unsolvable puzzles
- **Pain**: No batch PDF aggregation → manual copy-paste workflow
- **Active authors**: 50–100; top book ~3K estimated sales
- **TAM estimate**: $2–5M annual KDP revenue

### LDR-002: PuzzleGenio
- **Type**: Freemium multi-puzzle SaaS (Wyattly LLC)
- **Pricing**: Free (ads), Premium $69/year
- **Positioning**: Education-focused
- **Strengths**: PDF export with answer keys (teacher workflow moat)
- **Weaknesses**: Grid cap (30×30), no uniqueness verification, no batch export
- **Monetization**: Unclear freemium conversion rate

### LDR-001: Nonogram Builder
- **Type**: Free indie web tool (Max Jakeins, RenderSnail)
- **Positioning**: Simplicity-first, no login, no ads
- **Strengths**: Unlimited grid sizes (50×50+), clean UX
- **Weaknesses**: No monetization (donations only), no PDF, no batch, no verification
- **Sustainability**: Unknown (solo dev)

### LDR-003: Nonograms Katana
- **Type**: Market-leading puzzle game (UCDEVS, Serbian studio)
- **Platforms**: iOS, Android, web, Windows, Amazon, Huawei
- **Scale**: 5–7.6M downloads; 223K iOS users estimated; 4.8★ rating
- **Monetization**: VIP €3.09/mo (~$2.49 USD); hints IAP ($0.99–$2.99)
- **Revenue estimate**: $5–50K/month (conservative 10% monetization)
- **Moats**: Brand, 10+ year longevity, multi-platform cloud sync, UX polish
- **Weakness**: Library (1000 puzzles) vs competitors (10K–20K+); no image-to-puzzle; no education angle

## Feature Matrix (Normalized)

| Feature | INT-KDP | INT-GEN | INT-SOL | PuzzleGenio | Nonogram Builder | Katana |
|---------|---------|---------|---------|-------------|------------------|---------|
| **Image-to-puzzle** | HIGH | HIGH | MED | partial | partial | none |
| **Uniqueness verification** | **HIGH** | HIGH | none | **❌** | **❌** | **❌** |
| **Batch PDF aggregation** | **HIGH** | none | none | **❌** | **❌** | N/A |
| **Answer keys** | HIGH | HIGH | none | ✓ | ? | none |
| **Grid size 10×50+** | HIGH | HIGH | MED | partial (30×30 cap) | ✓ | ✓ |
| **Commercial licensing clarity** | **HIGH** | HIGH | none | unclear | ✓ | N/A |
| **Difficulty curve auto** | MED | MED | HIGH | none | none | none |
| **UX simplicity** | MED | HIGH | HIGH | ✓ | ✓ | ✓ |

## Gap Analysis

### Nobody Does It
1. **Uniqueness verification** — No competitor verifies exactly-one-solution property. KDP authors resort to manual testing or skip (high reputation risk).
2. **Batch PDF aggregation** — No tool bundles 50–200 puzzles into one book with centralized answer keys.
3. **Difficulty curve validation** — No tool auto-assigns Easy/Med/Hard based on solver metrics.
4. **Commercial licensing clarity** — PuzzleGenio and Nonogram Builder silent on commercial use rights.

### Everybody Does It Badly
1. **KDP quality control** — Reviews cluster: duplicate puzzles, spoiler leaks, difficulty mismatch, missing answers.
2. **Generator tools: grid size** — PuzzleGenio's 30×30 cap frustrates users wanting larger puzzles.
3. **Solver games: library size** — Katana's 1000 vs competitors 10K–20K+ is weak moat.

### Our Context Enables It
1. **Solver tech moat** — Production-grade uniqueness solver (no competitor exports this as a feature).
2. **First-mover window** — Katana silent on verification; competitive window is open but time-sensitive.
3. **Multi-channel reuse** — Same solver tech serves KDP (verify→PDF), generator (verify exports), and solver game (difficulty→progression).

## v1 Feature Selection

### Table Stakes (7 features)
- MF-004: Image-to-puzzle (adoption blocker across all channels)
- MF-005: Answer keys/solution export (adoption blocker for INT-KDP)
- MF-006: Grid size range 10–50+ (adoption blocker)
- MF-007: Commercial licensing clarity (adoption blocker for INT-KDP)
- MF-010: UI simplicity (retention moat)
- Plus two more baseline features

### Differentiators (3 features)
1. **MF-002: Uniqueness verification** ⭐ — Locked moat; KDP pain point; no competitor has it
2. **MF-003: Batch PDF aggregation** ⭐ — End-to-end KDP workflow; eliminates manual copy-paste
3. **MF-008: Difficulty curve via solver metrics** — Auto-assign Easy/Med/Hard; validates progression

### Later Bucket (6 features)
- Multi-platform + cloud sync (phase 2, 6+ months)
- Daily challenges & leaderboards (v1.5, engagement)
- Puzzle library 1000+ (organic growth, not v1)
- User-generated content (v2+, moderation liability)
- Color nonograms (v1.5+, niche feature)
- Narrative wrapping (v1.5+, engagement experiment)

### Explicitly Rejected
- Massive library (10K+) → Opportunity cost vs verification moat
- Multi-platform launch v1 → Web first, validate before scaling
- Leaderboards v1 → Add post-launch when core polished
- Color v1 → Scope discipline; B&W sufficient

## Market Assumptions (Unvalidated)

| ASM | Claim | Validation Gate | Timeline |
|-----|-------|-----------------|----------|
| ASM-001 | KDP market is $2–5M annual | 5–10 author interviews; threshold ≥3 confirm $500+/mo target | Q3 2026 |
| ASM-002 | Uniqueness verification unblocks KDP authors | Author interviews; ≥7/10 say "yes" | Q3 2026 |
| ASM-003 | Batch PDF eliminates bottleneck | Author interview: median >2 hours/week assembling | Q3 2026 |
| ASM-004 | Auto-difficulty accuracy | v1 beta: ≥70% agree auto-tier matches perception | Post-launch |
| ASM-005 | First-mover window is open | Monitor competitors Q3–Q4 2026; alert if Katana adds verification | Ongoing |
| ASM-006 | Commercial licensing clarity unblocks adoption | Author interviews; ≥8/10 confirm it matters | Q3 2026 |
| ASM-007 | Solver game market is mature/saturated | Monitor Katana velocity; if declines >20% YoY, confirm saturation | Ongoing |

## Non-Negotiable Risks

⚠ **Solver latency on 50×50 mid-density grids**: May timeout (>60s). Cooperative retry loop + user manual modifications required.

⚠ **Difficulty heuristic accuracy**: v1 uses heuristics (propagation depth, backtrack count); needs player feedback loop for calibration.

⚠ **Commercial licensing legal review**: ToS must explicitly permit commercial use (KDP, print-on-demand) before launch.

⚠ **First-mover window**: If Katana or PuzzleGenio add verification by EOY 2026, our moat shrinks. Time-to-market critical for KDP positioning.

## Next Steps

1. ✅ **Research complete** — All four leaders analyzed; features normalized; gaps identified; v1 synthesis finalized
2. **Pending**: Fix forge validator hook (YAML parsing bug on .md files) and commit artifacts
3. **Next phase**: `/forge:brainstorm` for story synthesis from differentiators
4. **Then**: `/forge:roadmap` for feature prioritization and sequencing
5. **Gate**: Schedule 5–10 KDP author interviews (Q3 2026) for ASM validation
