# CARD-241: One round mark on the page, proved by rendering it rather than by reading the source

**Status:** ready
**Priority:** P1
**Category:** enabler
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-228's escalation, 2026-10-16 — owner decision at the architect station, option (b) of three. Every figure in this card was measured during CARD-228's three review cycles; nothing here needs re-deriving.
**Idea:** —
**Wave:** —
**Depends on:** CARD-228 (it owns the glyph and the four-route static guard this card supersedes as the universal check)
**Touches:** tests/test_book_difficulty_dots.py, tests/helpers/ (a new roundness helper), meta/architecture/decisions/ (ADR-0036 delta, if the owner takes the declaration here)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

CARD-228 cut one function that draws a tier as three dots, and four later cards
(CARD-207/229/231/233) are supposed to reuse it rather than each inventing their own. The
guarantee that they *must* reuse it was attempted as a static `ast` walk over `src/nonogram/**`.
**Three review cycles proved that instrument cannot hold it.** This card replaces the instrument.

### Why the static walk failed, stated once so it is not re-attempted

The walk discriminates by **syntactic form**, and **no authority enumerates the forms.**
`dir(ImageDraw.ImageDraw)` is a genuine authority for *which methods* can draw — that half is sound
and must be kept — but Python's grammar offers nothing importable that lists every way to write a
vertex list or name a receiver. So each cycle closed the named routes and the next cycle found a new
family one level down:

| cycle | glyphs landed | the family |
|---|---|---|
| 1 | 3 | `draw.text` with bullets, a 32-gon `polygon`, a `point` disc |
| 2 | 2 | a **starred** vertex literal, an **annotated** draw receiver |
| 3 | 3 | **`draw.line`** polylines, ink **accumulated across calls**, a **stored bound method** |

Cycle 2's default-deny inversion was the right move and is kept — it closed receivers and binding
forms for good — but it moves the frontier rather than closing it.

### The instrument this card uses instead

**Render a page, find the ink, test it for roundness.** Blind to spelling altogether, and it is what
CARD-207's printed proof does anyway.

1. A helper that takes a rendered page and returns its connected ink regions with, per region, the
   measurements that distinguish a disc from everything else. CARD-228's cycle-3 review established
   the metric works and is cheap — a few lines of NumPy, on the dependency baseline already
   (stdlib + Pillow + NumPy, ADR-0006/R1, **no new dependency**).
2. The measurements to use, all taken during CARD-228's cycles: `draw.ellipse` at a given radius
   inks **1313 px**; the `draw.line` 240-ray fan that evaded the static guard inks **1329 px** at
   **41×41 px, aspect 1.000**; the `draw.point` loop disc inks **1257 px**. A metric that cannot
   separate those three from each other is the *right* answer — they are all discs, and all three
   must be **caught**, which is the point. What the metric must separate is a disc from the
   package's legitimate marks: rules, frames, glyph text, the proof sheet's arrow head.
3. The guard: render the pages the book actually produces, and assert that every round region on
   them is accounted for by the one drawing site. A round mark nobody declared is a failure.

### What must NOT be thrown away

CARD-228's static guard **stays**. It is fast, it runs on every commit, and it catches the four
routes it does see before a render is even attempted. This card adds the universal check; it does
not delete the cheap one. Keep its "true by mechanism" / "named limits" split, and strike from its
limits list exactly those routes this card's render check now closes — **the equality must go red
if a limit is struck without being closed, and that is the card's own self-test.**

## Acceptance criteria

- **AC-1** (happy, the three known evasions die): *Given* CARD-228's three cycle-3 survivors —
  `draw.line` as a ray fan, a loop of in-bound `draw.point` calls, a stored bound method — *then*
  each is caught by the render check, demonstrated by planting and reverting each one.
  (test: `TestRoundMarkOnThePage_CatchesWhatTheWalkCannotSee`)
- **AC-2** (guard, legitimate marks are not caught): *Given* the pages the book really produces,
  *then* the check passes on every one of them unmutated — rules, frames, the proof sheet's arrow
  head and all glyph text included. Paired with AC-1, so the check is shown to discriminate rather
  than merely to fire. (test: `TestRoundMarkOnThePage_PassesOnTheRealBook`)
- **AC-3** (guard, blind to spelling): *Given* one dot glyph written four different ways —
  `ellipse`, a `line` fan, a `point` loop, a `polygon` — *then* the check's verdict is the same for
  all four, because it reads ink and not syntax.
  (test: `TestRoundMarkOnThePage_SameVerdictForEverySpelling`)
- **AC-4** (edge, the metric's own boundary): *Given* a mark that is **nearly** round (a hexagon, a
  rounded rectangle at a small corner radius) *then* the check's verdict is **stated and tested**
  at that boundary rather than left to chance, and the threshold is justified by a measurement, not
  chosen. (test: `TestRoundMarkOnThePage_TheBoundaryIsMeasured`)
- **AC-5** (guard, the static guard's limits list shrinks honestly): *Given* CARD-228's named-limits
  list, *then* exactly those routes this card closes are struck from it, and the list's equality
  goes **red** if a route is struck without being closed or closed without being struck.
  (test: CARD-228's own limits equality, extended)
- **AC-6** (edge, cost): *Given* the render check, *then* its wall-clock cost is **measured and
  recorded**, and if it is too slow for every commit it is marked so that it runs where the project
  already pays for rendering — stated explicitly, not discovered at a merge gate.
  (test: a recorded measurement, in the card and in `meta/profiling/`)

## Guardrails

- G-1: **do not delete CARD-228's static guard.** It is the cheap first line. This card supersedes
  it only as the *universal* check.
- G-2: no new runtime dependency (ADR-0006/R1). NumPy and Pillow are already in the baseline; the
  helper belongs under `tests/helpers/`, which is where this project puts independent second
  implementations.
- G-3: **no `hypothesis`.** Seeded stdlib corpora with an asserted minimum case count, per CLAUDE.md.
- G-4: do not change the glyph. `difficulty_dots`, `_draw_difficulty_dots` and their geometry are
  CARD-228's and are done; this card only measures what they draw.
- G-5: do not re-measure or regenerate `meta/profiling`'s frozen artefacts. If this card's new test
  file would enter `test_suite_profile.py`'s render-heavy set, **say so and handle it deliberately**
  — CARD-228's fix cycle hit exactly that and backed out rather than commit under `meta/`; the
  third option it missed was splitting the matched literal, and it is recorded here so this card
  does not rediscover it.
- G-6: every claim this card makes about what the check catches carries a control that can fail —
  the standing rule from CARD-238, and the one CARD-228's three cycles kept testing.

## System contract

- ADR-0006/R1 — runtime dependencies are exactly stdlib + Pillow + NumPy (check:
  `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`)
- ADR-0036/R2 — page geometry comes from COMP-007 (check: review-lens)
- CON-020 — reader-facing interior text at or above 10 pt; the dots are not text (check:
  `TestInteriorType_EveryFaceHoldsTheFloor`)

## Architecture context

- **FR:** FR-033, FR-043.
- **CON:** CON-020.
- **ADR:** ADR-0036/R2, ADR-0006/R1. ⚑ **An ADR delta may be owed here:** CARD-228 introduced a
  package-wide constraint — no string literal anywhere in `src/nonogram/` may hold a codepoint in
  U+25A0–U+25FF, U+2022 or U+2219, docstrings included — which is currently declared *only* inside
  a test file. It binds every module and its single exemption cannot absorb a drawing module. The
  owner may want it in ADR-0036 instead; decide that here, since this card owns the same subject.
- **Components:** COMP-007, COMP-009.
- **Trace:** to be updated if the ADR delta is taken.

## Worktree notes

- [Why architectural, and why TDD] It replaces a verification instrument that four cards depend on,
  and every AC is of the form "a check that fires on X and not on Y" — which cannot be evidenced
  without driving each one red against the current code first. Same reason CARD-238 and CARD-239
  carry `TDD: true`.
- [Read CARD-228's three review reports before starting] `meta/review/*CARD-228-cycle{1,2,3}.yml`.
  They contain the measured ink counts, the exact evasions, and the reasoning for why enumeration
  cannot converge — all of it measured, none of it needing to be re-derived. Re-deriving it is how
  this card costs 2d instead of 1d.
- [The trap this card must not fall into] Writing a render check whose *stated* reach exceeds what
  it measures. That is the same family as the static guard's, one abstraction over. State what the
  metric separates, measure the boundary (AC-4), and name what it does not catch.
