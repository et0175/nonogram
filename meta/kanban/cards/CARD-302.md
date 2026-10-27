# CARD-302: The memo's USE is unguarded — the cheapening can silently return

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/302-guard-the-memo-at-its-call-site
**Worktree:** —
**Source:** CARD-292 review cycle 2, F-203 — the declared bound of its F-008 had no owner, so nothing owed the control. Created 2026-10-27 before CARD-292's last fix round, so the bound names a card that exists.
**Idea:** —
**Wave:** unscheduled
**Created wave:** 62
**Deferred waves:** 0
**Depends on:** CARD-292 (merged)
**Touches:** tests/test_book_export_interior_cover.py, meta/profiling/card-292-per-test-ceiling.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this exists, in one measured sentence

CARD-292 made `tests/test_book_export_interior_cover.py` run **4.9× faster**
(511.43 s → 104.12 s) by routing `segment()` through a module-level
`_source_segment` over a memoised line split. **The memo's existence is guarded;
its use at the one hot call site is not** — so the file can return to ~113 s with
**no cell firing**, and the board would learn about it from a suite that got slow
again rather than from a test.

Measured by CARD-292's own kill matrix and re-derived by its cycle 2:

- **M1 dies** when the memo is deleted — `assert 9816 == 1`, "the line split ran
  9816 times". So the *mechanism* is guarded.
- **M10 survives** when the cheapening is reverted — the memo-guard class stays
  green (5 passed) and the split-count cell passes, **because that cell calls
  `_source_segment` directly and never goes through the hot site.** The file then
  costs 105.65 / 87.27 s against 29.38 / 10.94 s, and nothing reds.

## What CARD-292 declined, and why the decline was right

Cycle 1 offered an AST control asserting that `segment()` resolves to
`_source_segment`. CARD-292's fix round **declined** it with two reasons cycle 2
verified as mechanically true:

1. A fix round whose subject was *figures* should not add a claim that changes
   what the tree asserts.
2. The control would turn **M10 from §8.1's *control* into a kill**, so the
   matrix row cycle 1 had independently reproduced would stop describing the tree.

Cycle 2's verdict: *"a declared bound, not a hole wearing a declaration"* — the
hole is stated in the sharpest terms available and the two cold sites a control
must discriminate are named. **Only the owner was missing. That is this card.**

## What to implement

1. **Guard the memo at its use, not only at its existence.** A control that reds
   when `segment()` stops going through `_source_segment` — whether by reverting
   the call, by rebinding the name, or by reaching the stdlib function directly
   at the hot site.
2. **Discriminate the two legitimate cold sites.** `ast.get_source_segment` is
   called directly at **lines 1438 and 2913** at CARD-292's revision
   (`db0e1a3e`); cycle 2 verified these are the only remaining ones outside the
   equivalence class. They are *correct* and must stay allowed, so a blanket "no
   `ast.get_source_segment` anywhere" rule is **not** the shape — resolve the
   line numbers freshly rather than trusting these, since the file moves.
3. **Decide M10's fate explicitly, and say which you chose.** Either keep
   §8.1's matrix describing the tree (M10 stays a control, and your new guard is
   written so it does not subsume it), or let M10 become a kill and **update the
   matrix and its prose in the same commit**. A matrix row that no longer
   describes the tree is the defect CARD-292 spent two cycles removing.

## Acceptance criteria

- **AC-1** (the use is guarded): *Given* the cheapening reverted at the hot call
  site only — the memo still present and still exported — *then* a named test
  reds. (test: a new cell; **gate**: the revert planted line-count-preserving and
  the firing cell named.)
- **AC-2** (the cold sites stay legal): *Given* the two direct
  `ast.get_source_segment` sites, *then* the guard passes, and *given* a third
  one planted at the hot site, *then* it reds. (test: both arms; **gate**: the
  plant's location named, and the site list **derived**, not retyped.)
- **AC-3** (M10's status is stated and true): *Given* `meta/profiling/card-292-per-test-ceiling.md`
  §8.1, *then* every row describes the tree as it is after this card. (**gate**:
  M10 re-fired and its row's outcome re-recorded, whichever way it goes.)
- **AC-4** (no figure re-measured without its door): *Given* any timing figure
  this card touches, *then* it names the instrument it came from. CARD-292's own
  headline defect was an instrument's domain leaking into a figure — the
  unprofiled ratio is **8.0×**, the both-arms-profiled ratio **4.05×**, and the
  original 9.9× was a profiled numerator over an unprofiled denominator.

## Guardrails

- **G-1: do not re-cheapen or re-measure the file.** CARD-292 owns the
  performance work and its figures are settled. This card adds a control.
- **G-2: do not edit `src/**`.** Test-tree only; a production change is a finding
  to raise.
- **G-3: no test deleted, renamed, skipped or merged** — `parametrize` ids count.
- **G-4: probes stay OUT of `tests/`**, and note CARD-292's own experience:
  `tests/test_suite_profile.py`'s guard enumerates **`tests` AND
  `meta/profiling`** through `git ls-files`, so an untracked scratch file is
  invisible to it while a tracked one is judged by it.
- **G-5: no new runtime dependency** (ADR-0006/R1), and **no `pytest-timeout`**.

## Worktree notes

- **The ceiling it lives under.** `tests/hang_guard.py` arms a **120 s per-test**
  wall-clock alarm with `exit=True`; `addopts = "-q"` hides the header line that
  announces it. If this file returns to ~113 s, its dearest test sits **7 s**
  under that ceiling — which is the condition CARD-292 existed to remove. That is
  the real cost of the unguarded use, and it is why this is tech-debt rather than
  housekeeping.
- **Read CARD-292's document before starting**, especially §5 (the decline), §8.1
  (the matrix) and §8.2 (the pre-gate rows). The two cold sites, the memo's
  export and M10's exact cells are all recorded there.
