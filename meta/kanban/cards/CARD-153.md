# CARD-153: Finalise doesn't hide a broken page plan behind "About N"

**Status:** ready
**Priority:** P1
**Category:** bug
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** CARD-129 review findings F-001, F-002, F-004, F-005 (2026-09-30); code re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 29
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_finalize.html, tests/test_book_finalise_gutter.py, tests/test_book_export_interior_cover.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`_interior_counts` (`src/nonogram/admin/app.py:866`) asks the export's page plan
for the interior's page counts. It wraps that call in a bare `except Exception`
(:887). Three problems share that one root cause:

1. **A correctness failure looks like an estimate.** `interior_stream` raises
   `RuntimeError` from two deliberate plan tripwires ("the page plan prints …",
   "the answer key holds …", documented in `book_pdf_generator.py` around
   :2234). Those mean the exporter is wrong. The bare `except` catches them the
   same way it catches an unreadable print spec, and the screen shows "About N"
   with no log line and no message.
2. **The reason is recorded and then dropped.** `InteriorCounts.unreadable` is
   written at :901 and nothing ever reads it. The owner never learns why the
   count is approximate.
3. **A book can leave draft when its pages can't be counted.** When
   `_interior_counts` returns `None`, `_kdp_gutter_refusal` returns `None` (:926),
   which the `save_and_finish` branch (:4096) treats as "no objection". The book
   moves to `READY_FOR_PDF` while the same screen says its pages cannot be counted.

Also from the same review:

4. **Wording mismatch (F-005):** the refusal says the book "runs to N pages" where
   the screen says "About N" for the same inexact count.
5. **A vacuous assertion (F-004):** `tests/test_book_export_interior_cover.py:374`,
   `"~" not in body.split('data-interior-page-count')[1][:40]`, can never fail,
   because the first split segment after the attribute name never contains the
   display text.

## What to do

1. Only catch what means "this book's print spec can't be laid out". Let the
   plan tripwires (and any other unexpected exception) propagate as the
   errors they are, logged with a traceback. Find out the exact exception type(s)
   the "unlayable spec" case raises, and catch only those.
2. Show `unreadable` on the Finalise screen next to the approximate count, with
   the remedy (Print setup).
3. A book whose interior can't be counted at all must not leave draft. Refuse in
   `save_and_finish` with a message saying why.
4. Make the refusal text and the screen agree on whether the count is exact.
5. Replace the vacuous assertion with one that can fail.

## Acceptance criteria

- **AC-1:** When `interior_stream` raises one of its plan tripwires, Finalise
  does not show an "About N" count, and the error is logged with its traceback.
  *test: TestFinaliseCounts_PlanTripwireIsNotAnEstimate*
- **AC-2:** When the stored print spec can't be laid out, Finalise shows the
  approximate count together with the reason and points to Print setup.
  *test: TestFinaliseCounts_ShowsWhyTheCountIsApproximate*
- **AC-3:** A book whose interior cannot be counted stays in draft on
  "Save and finish", and the screen says why.
  *test: TestFinalise_UncountableBookStaysInDraft*
- **AC-4:** The refusal for an inexact count uses the same "about" wording as
  the screen.
  *test: TestFinaliseGutter_InexactRefusalSaysAbout*
- **AC-5:** The exactness assertion in `test_book_export_interior_cover.py` fails
  when the screen shows "~N" (checked by temporarily breaking it).
  *test: the existing test, rewritten*

## Guardrails

- G-1: The stored gutter is never raised or rewritten, and the book is never laid
  out a second time at another gutter (CARD-129's G-1/G-2 stand).
- G-2: No change to the PDF bytes of any export. The CON-019 golden A4 tripwire
  stays green.
- G-3: ADR-0035/R1's plan gate is unchanged; this card adds a refusal and
  doesn't relax one.

## Architecture context

- **FR:** FR-030, FR-040, FR-042 (page counts on Finalise); EC-034 (the count
  checked is the count printed)
- **ADR:** ADR-0035/R1, ADR-0036 (gutter clarification)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] CARD-129's review: F-001/F-002/F-005 share one root cause and were
  left open when CARD-129 merged. Cut from the backlog sweep on 2026-10-02.
- [Why P1] This is the one place a real exporter bug would surface before the
  owner uploads to KDP, and right now it surfaces as a plausible number.
