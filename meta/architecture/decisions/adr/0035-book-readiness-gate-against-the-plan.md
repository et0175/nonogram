# ADR-0035: A book leaves draft only when it matches its planned book

**Status:** Accepted
**Date:** 2026-09-22
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** on-touch
**Pattern:** —
**API-Posture:** —

## Context

FR-037 (BK-4, book rule 6) says a book can be marked ready only when every longest-side × tier cell of its selection is within ±3 percentage points of that cell's share of the stored plan (FR-034, INV-007). FR-039 adds a hint to the books list that shows, per book, where the selection is short of or over its plan. The source leaves four points unstated, and each changes what the code does:

- (a) Which transition is "marked ready". `BookManager.set_book_status` accepts any jump today: draft can go straight to ready_for_kdp or published. So a gate on a single target status could be bypassed.
- (b) The denominator of a share when the actual puzzle count differs from the plan. Is a cell's share measured against the planned total or the actual total?
- (c) What a book created before plans existed (no stored plan) does at the gate.
- (d) Whether FR-039's hint uses the same ±3 pp tolerance or exact counts.

The status chain is draft → ready_for_pdf → pdf_generated → ready_for_kdp → published. The only rule today is "at least one puzzle before leaving draft". ADR-0034 gives every new book a default plan of 150 puzzles at 40/40/20.

## Decision

We will gate every transition out of draft, to ready_for_pdf or any later status, on the plan check. A cell's actual share is its puzzle count divided by the **planned** total, so "ready" means "this is the book that was planned", not only "the mix is right". A book with no stored plan is refused with a message to store a plan on Print setup first; ADR-0034's default makes that one step. The books-list hint (FR-039) shows exact counts against the plan per cell (e.g. "short 3", "over 1"), because it is a to-do list, not a gate.

These are the owner's answers to (a)–(d), taken point by point on 2026-09-22. Gating every exit from draft closes the status-jump bypass without adding a status-order rule the requirements never asked for.

## Alternatives considered

### Gate only draft → ready_for_pdf, enforce the status order, measure proportions against the actual total, let plan-less books pass, ±3 pp hint
This reads "±3 percentage points" as proportion only: a smaller book in the right mix passes, and the hint always agrees with the gate. Rejected: it would let a 10-puzzle book pass a 150-puzzle plan. Grandfathering would let every older book skip BK-4 entirely. And a mandatory status order is a new rule the requirements do not contain.

## Consequences

### Positive
- The gate cannot be bypassed by jumping statuses. Any exit from draft is checked.
- "Ready" means the planned book: an under-filled book fails even if its proportions are right, which also catches an unfinished selection before the PDF is generated.
- Legacy books get a clear remedy instead of a silent pass.
- The list hint tells the owner exactly how many puzzles to add or remove in each cell.

### Negative
- Because shares use the planned denominator, the gate also enforces the total count within the tolerance. A deliberately smaller book needs its plan edited first.
- The hint and the gate can disagree near the tolerance: the list may say "over by 1" while the gate passes.
- Existing books in the database have no plan, so none of them can leave draft until a plan is stored. That is the on-touch migration: fix when a book is next edited.

### Neutral
- The gate runs at the transition only. Editing a non-draft book's membership returns it to draft (see Clarifications).
- FR-037's open question (a)–(c) and FR-039's tolerance question are closed; the criteria that assumed actual count = planned count stand, and the card adds criteria for the under-filled and plan-less cases.

## Clarifications (2026-09-22)

### Membership change after draft
Adding or removing puzzles in a book that has left draft (after FR-038's confirmation for a published book) returns the book to **draft**. It must pass the plan check again before a new PDF is generated. The owner chose this over keeping the status with a warning, because a KDP upload must never be built from a book that no longer matches its plan.

## References

- DEC-038 (resolved by this ADR)
- CTX-001; AGG-002 Book (INV-007), TERM-029
- FR-034, FR-037, FR-038, FR-039
- ADR-0033 (Book assembly stays in CTX-001), ADR-0034 (default plan)
- src/nonogram/admin/book_manager.py (`set_book_status`)

## History

- 2026-09-22: Created — every exit from draft is gated on the planned book (planned-total denominator, ±3 pp per cell); plan-less books are refused; the list hint uses exact counts.
- 2026-09-22: Clarified (owner) — changing the puzzles of a book that has left draft returns it to draft. Decision unchanged.

## Rules

```yaml
- id: ADR-0035/R1
  statement: >-
    No book leaves draft (to any other status) unless it has a stored plan
    and every longest-side x tier cell's count, divided by the planned
    total, is within +/-3 percentage points of that cell's planned share.
  scope: {contexts: [CTX-001], code: ["src/nonogram/admin/book_manager.py"]}
  check: {kind: test, ref: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan}
  severity: mandatory
```
