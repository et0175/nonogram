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

### Implementation round 1 (2026-11-25)

**Verdict:** done, with two premise corrections and one AC-1 residual held for the orchestrator (below).

**Chosen name:** `PropertyTest_BookPdf_PortraitUnrotatedFloatingAtFortyTwoPercentForEveryExtent`.
Reason: every one of the three bodies asserts portrait, unrotated (columns x rows as drawn), and the 42% float of the puzzle area's spare (`varying_tops > 1` / `len(tops) > 1` as the retired fixed edge's survivor); "clear of both rules" is left out because only the `_pdf_pages` body asserts a rule (the footer side, CARD-485 AC-2) and none asserts the header side directly, so the name would claim more than the bodies check. "FortyTwoPercent" follows `TestBookPuzzleFrame_GridSitsAtFortyTwoPercentOfTheSpare`.

**Premise corrections (measured, not inferred):**
- The name has **three** defs, not two: the layout half `tests/property/test_book_layout.py::test_<name>` plus the two PDF halves `_pdf_pages` and `_two_up_pages`. `trace.yml` already recorded "3 cases collected at the AC gate". All three were renamed; otherwise AC-1's grep could not be empty. The layout function's docstring paragraph "Function name kept for trace stability" was rewritten to record the rename (docstring only).
- The `wave_close_only` marker applied before this card to **one** of them, not both: `_pdf_pages` is in `LIST_1[0].marked`; `_two_up_pages` is that entry's `smoke` node (the gate keeps it, so it is unmarked by design); the layout half is unregistered. The registry's shape is unchanged; only the node ids/keys were renamed.

**Change (names and docs only; no test body, case count or assertion changed):**
- `tests/property/test_book_pdf_geometry.py`, `tests/property/test_book_layout.py`: three function names, both module docstrings, the layout function's docstring paragraph.
- `tests/wave_close_marker.py` (marked node id, smoke node id, floors key) and `tests/test_wave_close_marker.py` (`PINNED_FLOORS` keys).
- `meta/architecture/requirements.yml` (EC-022 `test:` and the comment naming it), `meta/architecture/trace.yml` (FR-032 row; the "still encodes the retired rule ... rename is still owed" passage replaced with a dated "Renamed 2026-11-25 (CARD-547)" line, history kept), `meta/architecture/handoff.md` (test list).
- `tests/test_check_ref_resolution.py`: three census baselines re-derived, each with a dated provenance comment: `CENSUS` (598, digest only), `TRACE_TESTS` (509, digest only), `DEFINED` (484, digest only); each move is OUT 1 (old name) / IN 1 (new name). Each was red after the rename and green on the base (stash control: the two failing tests 2 passed on base). The new ref resolves by an independent `ast` index to 3 def lines; the old name to 0.

**AC evidence:**
- AC-1: `grep -rn PortraitWithFixedTopEdge src tests meta/architecture` prints ONE line: `tests/hang_guard.py` (a comment recording CARD-336's projection for "the CARD-322 geometry node `PortraitWithFixedTopEdge_pdf_pages`"). Not edited: the brief forbids editing any guard file. Held for the orchestrator to decide (edit the comment, or accept it as historical). `ast` index: new name -> exactly 3 defs (listed above), old name -> 0. By node id, each run once: layout half 1 collected / 1 passed / 0 skipped, exit 0, 0.93 s call; `_two_up_pages` 1/1/0, exit 0, 2.35 s call; `_pdf_pages` 1/1/0, exit 0, 22.55 s call (quiet host).
- AC-2: `tests/test_wave_close_marker.py` passes (19 collected, inside the run below). `-m wave_close_only --collect-only` over the two property files: 3/15 collected (12 deselected), exit 0, listing `..._DrawingFitsUsableAreaUnderStandardCell_pdf_pages`, `test_PropertyTest_BookPdf_PortraitUnrotatedFloatingAtFortyTwoPercentForEveryExtent_pdf_pages`, `..._MirroredMarginsCentreDrawingForEveryParity_pdf_pages`. `_two_up_pages` is not listed, as before the card (it is the entry's smoke node).
- AC-3: tests that read `trace.yml` / `requirements.yml` refs: `tests/test_check_ref_resolution.py` (26), `tests/test_grid_bound_agreement.py` (4), `tests/test_book_page_packing_doc.py` (3), `tests/test_approval_guess_gate.py::test_the_registrys_check_refs_for_this_card_all_resolve` (1), `tests/test_impact_set.py` (217, holds the trace census in its regret table), plus `tests/test_wave_close_marker.py` (19): 270 collected, 270 passed, 0 skipped, exit 0 (2 UserWarnings, identical on the base). Forge validator (forge_1, `~/MyProjects/forge_1/forge/skills/architect-validate/scripts/validate.py --root meta/architecture`): before 0 errors / 104 warnings, after 0 errors / 104 warnings; output identical modulo the name.
- AC-4: no test added or removed. Collection over the four edited test files: 60 before, 60 after. Net test count 0.
