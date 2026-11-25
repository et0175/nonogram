# CARD-547: EC-022's property test is renamed to the rule it now checks

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/547-rename-ec022-property-test
**Worktree:** ../PythonProject4-card-547
**Source:** roadmap wave 21, cut 2026-11-25 on the owner's "pick the next no-decision wave from the backlog". Backlog IDEA-179; the rename has been owed since CARD-224 (trace.yml FR-032 notes, 2026-10-17).
**Idea:** IDEA-179
**Wave:** 100
**Created wave:** 100
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/property/test_book_pdf_geometry.py, tests/property/test_book_layout.py (module docstring only), tests/wave_close_marker.py, tests/test_wave_close_marker.py, meta/architecture/requirements.yml (EC-022 `test:` and the comments that name the test), meta/architecture/trace.yml (the FR-032 row and its notes)
**UI surface:** —
**Review score:** —
**Started:** 2026-11-25T11:41Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent` is EC-022's property check. Its name still says "fixed top edge", a rule CARD-224 retired on 2026-10-17. EC-022 now says the drawing sits 42% of the way down its puzzle area's spare height, is placed as low as it fits when the spare is too small, and never crosses the header or footer rule. CARD-224 was asked to rename the test and closed without doing it. `trace.yml`'s FR-032 notes record that "only its name lies". The test itself is sound. A name a reader acts on should say what it checks.

## What to implement

1. **Read the two test functions first:** `test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_pdf_pages` and `..._two_up_pages`. Choose a new `PropertyTest_BookPdf_...` name that states what they assert today, as EC-022 words it: portrait page, unrotated grid, drawing at the 42% float, and clear of both rules for every extent. Do not invent a claim the bodies do not make. Record the chosen name and a one-line reason in `## Worktree notes`.
2. **Rename everywhere it is named, in one change:** the two function names, the module docstrings of `tests/property/test_book_pdf_geometry.py` and `tests/property/test_book_layout.py`, the `wave_close_only` registry in `tests/wave_close_marker.py` (node ids and the keyed entry), the expectations keyed by name in `tests/test_wave_close_marker.py`, EC-022's `test:` field and the comments in `meta/architecture/requirements.yml` that name it, and the FR-032 row in `meta/architecture/trace.yml`.
3. **Update the FR-032 notes in `trace.yml`:** the "still encodes the retired rule ... rename is still owed" passage becomes a dated line saying the rename landed on this card. Keep the history above it.
4. **Change only names and docs.** Do not change any test body, case count or assertion. The `wave_close_only` marker must still apply to both renamed tests.
5. After the change, the old name must appear nowhere in `src/`, `tests/` or `meta/architecture/`. Historical text under `meta/kanban/` (cards, roadmap, backlog) stays as written, because it records what was true then.

## Acceptance criteria

- AC-1: `grep -rn PortraitWithFixedTopEdge src tests meta/architecture` prints nothing (recorded). The new name resolves, by `ast`, to exactly the two test functions; collecting each by node id finds 1 test, recorded with collected/passed counts and exit code.
- AC-2: the wave-close marker still covers both renamed tests. `tests/test_wave_close_marker.py` passes, and `make test-marked`-style collection (`-m wave_close_only --collect-only`) lists both new node ids (recorded).
- AC-3: the trace and requirements censuses stay green. Name the tests that check `trace.yml` / `requirements.yml` `test:` refs, run them, and record the result. Run the forge validator (the forge_1 copy) and report its error count before and after.
- AC-4: owner's test budget: no test added or removed; net test count 0; report it.

## Worktree notes
