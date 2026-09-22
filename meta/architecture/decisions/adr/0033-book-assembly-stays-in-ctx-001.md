# ADR-0033: Book assembly stays in CTX-001 as its second aggregate

**Status:** Accepted
**Date:** 2026-09-22
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

The 2026-09-22 book-generator delta (FR-030..FR-039, NFR-008, CON-018, CON-019) modelled the Book for the first time: AGG-002 Book with its own invariants (INV-005..INV-008), a lifecycle of its own (draft → ready_for_pdf → pdf_generated → ready_for_kdp → published), capability CAP-006 "Book assembly" and a print-production vocabulary (TERM-018..TERM-029). Until now CTX-001 held one aggregate, and ADR-0019 had rejected a separate context for the web UI on grounds — same aggregate, no network (BCON-0001), no persistence (CON-003) — that do not carry over to a DB-backed, deployed admin panel (ADR-0030, ADR-0032, CON-017).

Two forces pull in opposite directions. For a separate context: Book references puzzles by id and never modifies them, CON-019 already imposes a one-way no-feedback rule towards CAP-005, and the print vocabulary (trim, gutter margin, standard cell) is foreign to puzzle generation. Against: the tool has one owner and one actor, `src/nonogram/admin/` imports clues, difficulty, export and the orchestrator in-process and is registered in the import guard (`tests/test_cli.py`) as a rank-0 adapter beside `cli` and `web`, the C4 views label the Admin Panel container CTX-001, and both aggregates share one Postgres database in which each puzzle row mirrors its book membership in `puzzles.book_id` (foreign key since migration 009).

## Decision

We will keep Book assembly in CTX-001: AGG-002 Book is CTX-001's second aggregate, CAP-006 is a CTX-001 capability, the admin panel stays an inbound adapter of CTX-001, the context map stays empty, and TERM-018..TERM-029 belong to CTX-001. This satisfies CON-017 and CON-019 with no structural change, because the separation that matters — CAP-006 may read puzzles but never feed back into puzzle generation or CAP-005's exports — is already a stated constraint and does not need a context boundary to hold. A split buys naming clarity rather than any NFR, for a single-owner tool, and it stays cheap later: only CAP-006 touches AGG-002, so CAP-006, AGG-002 and TERM-018..TERM-029 would move out together and the map would gain one CTX-002 → CTX-001 entry.

Whether one puzzle may appear in more than one book is left open (see Neutral). Today's rule — at most one book per puzzle, enforced by the single-valued `puzzles.book_id`, with assigned puzzles hidden from other books' selection — stays in force until the owner decides it.

## Alternatives considered

### CTX-002 Book Production with a shared database
Name the boundary in the model and C4 while both sides keep reading and writing the same Postgres and `puzzles.book_id` stays. Rejected: the diagrams would say "separate" while the data says "shared" — CTX-001's puzzle table would carry CTX-002's membership column, so a schema change on either side could break the other, and the admin adapter's in-process imports of CTX-001 capabilities would become a cross-context dependency the import guard does not model. It is the riskiest of the three shapes for the least gain.

### CTX-002 Book Production owning membership
Book becomes the sole owner of membership (its own `book_puzzles` table), `puzzles.book_id` is retired by migration, and CTX-001 is consumed read-only by puzzle id. This is the cleanest boundary and would also allow a puzzle to sit in several books. Rejected for now: it needs a migration and a rewrite of every query that filters puzzles by `book_id` (selection's exclusion of assigned puzzles, the books-list counts), the largest change of the three, and its main product benefit — reuse across books — is not yet wanted. If the owner decides puzzles may be reused, the membership table can be introduced then without revisiting the context boundary.

## Consequences

### Positive
- Zero structural change: the code, the import guard, the C4 views and this model agree, and the book cards start from the code as built.
- INV-005..INV-008 live in one aggregate inside one context, next to the puzzle data they reference, with no integration contract to keep in step.
- The split remains a mechanical move (CAP-006 + AGG-002 + TERM-018..TERM-029 → CTX-002) if a second owner, a separate deployment or cross-book reuse ever justifies it.

### Negative
- CTX-001's ubiquitous language now mixes puzzle generation with print production; "gutter" already needs two qualified terms (TERM-020 Gutter margin, TERM-021 Clue gutter) to stay unambiguous.
- The shared-database coupling stays implicit: `puzzles.book_id` is book membership stored on the puzzle, so a Puzzle "knows" about books even though Book is modelled as referencing puzzles by id only.
- One-book-per-puzzle is a consequence of that column rather than a stated product rule; reusing puzzles in a later big book or pocket edition would need a migration.

### Neutral
- TERM-018..TERM-029 move from `context: unknown` to CTX-001 in glossary.yml; contexts.yml's provisional notes become final.
- Open product question, recorded here rather than decided: may one puzzle appear in more than one book (e.g. Book 1 and a later big book or 6×9 pocket edition)? Until answered, the one-book rule holds.
- DEC-035 (where the book's page geometry lives) can now proceed; it no longer depends on a context split.

## References

- DEC-037 (resolved by this ADR)
- CTX-001 (affected context); CAP-006, AGG-002 (INV-005..INV-008), TERM-018..TERM-029
- CON-017, CON-019
- ADR-0019 (web UI kept inside CTX-001), ADR-0030, ADR-0032 (deployed, DB-backed admin panel)
- migrations/versions/009 (`fk_puzzles_book_id_books`); tests/test_cli.py (import guard, `admin` as rank-0 adapter)

## History

- 2026-09-22: Created — Book assembly kept in CTX-001 as its second aggregate; the one-book-per-puzzle rule left open as a product question.

## Rules

```yaml
- id: ADR-0033/R1
  statement: >-
    Book assembly references puzzles by id and never changes a puzzle's grid,
    clues, difficulty tier or strategies; the only puzzle field it may write
    is the book-membership mirror (puzzles.book_id).
  scope: {contexts: [CTX-001], code: ["src/nonogram/admin/book_*.py"]}
  check: {kind: review-lens}
  severity: mandatory
```
