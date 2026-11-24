# CARD-537: The CARD-145 export minors, verified first and fixed only where still live

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** roadmap wave 17, cut 2026-11-24 on the owner's "pick the next no-decision wave from the backlog". IDEA-025.
**Idea:** IDEA-025
**Wave:** 96
**Created wave:** 96
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_pdf_memory.py
**UI surface:** —
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-145's review left two minors: a same-length byte change would still pass the interior byte-length assertion, and the uploaded cover's RGBA path is not measured for memory. Re-checked on main at the cut: `TestBookPdfMemory`'s determinism group in `tests/test_book_pdf_memory.py` now has `test_the_same_book_is_the_same_length_every_time` beside `test_the_same_book_writes_the_same_operators_every_time` (sha256 per content stream) and `test_the_same_book_renders_to_the_same_pixels_every_time` (per-page digests). The first minor may now be moot, because a same-length change would have to leave both the operators and the pixels unchanged to escape. The module docstring describes a cover half of the memory bound; whether it covers an RGBA upload is not known.

## What to implement

1. Verify first. Minor 1: name the class of same-length byte change that would escape all three determinism tests (if any) and show it with a mutant, or record moot with the mutants that were caught. Minor 2: find whether any memory test feeds the cover an RGBA image (an uploaded PNG with alpha); if none does, measure one run with an RGBA cover against the bound the cover half uses.
2. Fix only the live ones. For minor 2, a live result means the RGBA path exceeds or is not covered by the bound: add the RGBA case as a parameter of the existing cover test, not a new test.
3. No change to `src/`. If the RGBA path breaks the bound, stop and report it: that is a product change and needs its own card.

## Acceptance criteria

- AC-1: each item has a recorded verdict, live or moot, backed by a run (a mutant, a probe or a test), never by reading code alone. Record the command and its result in `## Worktree notes`.
- AC-2: every live item is fixed, and its fix has one control that fails when the fix is reverted.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes
