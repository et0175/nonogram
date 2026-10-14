# CARD-210: Each puzzle's QR code becomes a real, scannable link to that puzzle's online solver

**Status:** blocked
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/210-real-puzzle-qr
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 ("I think about delivering some extra benefits with the book: 1. Qr code with each puzzle in the book to the puzzle online solver for this specific puzzle (this solver doesn't exist so far, so we need to think about its development)"); the slot it fills is CARD-204's placeholder glyph
**Idea:** —
**Wave:** —
**Depends on:** CARD-204
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/export/layout.py, pyproject.toml, tests/test_book_pdf.py, tests/test_book_qr.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** owner decision 2026-10-13 — "keep the placeholder until infra exists". Real QR pixels wait on the next phase's infrastructure: a public solver that is actually hosted, and a per-puzzle URL namespace stable enough to print in a book that cannot be reprinted. Unblock when both exist (`/forge:kanban unblock CARD-210`).

## What to implement

**Why this card exists and is blocked.** CARD-204 reserves a 2×2 cm QR slot on
every book puzzle page and fills it with a deliberately-fake, non-scanning glyph
— the owner's own "draft the QR icon's layout slot now with a placeholder/TODO
link" decision of 2026-10-08. This card is the swap-in that CARD-204's
"What to implement" step 2 names as a follow-up. Two things it needs do not
exist yet, and neither can be decided in a worktree:

1. **A public solver to point at.** Today interactive play exists **only** as the
   admin panel's player behind the CON-015/CON-016 door (CON-021, ADR-0038/R6).
   The owner's own plan is explicit: "we'll need to set up an infrastructure for
   prod. But I propose to move it to the next phase — make for now solver under
   the admin panel". A QR printed into a book is permanent; pointing it at a
   URL that does not resolve, or at an admin URL nobody but the owner can
   reach, is worse than printing no QR.
2. **A URL namespace per puzzle** that survives the database being re-seeded —
   a printed code cannot be re-pointed. This is a design decision (opaque
   stable puzzle slug vs. row id vs. a content hash of the grid), not an
   implementation detail.

**What it will do once unblocked.**

1. Encode a real QR (the public per-puzzle URL) and draw it into CARD-204's
   existing slot — same position, same 2×2 cm extent, no new geometry
   (ADR-0036/R2: positions come from `export/layout.py`, which CARD-204 already
   taught to reserve the slot).
2. **The encoder is an ADR-0006 decision.** The runtime dependency set is
   exactly stdlib + Pillow + NumPy; a QR encoder is either a new dependency
   (revising ADR-0006/R1) or ~400 lines of in-repo Reed–Solomon, mask selection
   and version fitting — correctness-critical code whose failure mode is a
   printed code that looks right and does not scan. The card must carry the
   owner's choice, recorded as an ADR delta **before** implementation.
3. Quiet zone and module size are print constraints, not cosmetics: a 2×2 cm
   code must hold the URL at a module size a phone camera resolves. The card
   must state the chosen QR version and the longest URL it can carry, and the
   AC below must verify a **decoded** round trip, not merely that pixels were
   drawn.

## Acceptance criteria

(Written now so the card is ready to run the moment it is unblocked; all of them
presume the two blockers are resolved and the chosen URL scheme is recorded.)

- **AC-1** (happy): *Given* a puzzle printed as puzzle 37, *when* its book page
  is rendered, *then* the QR slot holds a code that decodes to exactly that
  puzzle's public solver URL. (test: `TestBookQr_DecodesToThePuzzlesOwnUrl`)
- **AC-2** (happy, every page): *Given* any book, *when* its interior is
  exported, *then* every puzzle page's QR decodes to the URL of the puzzle (or,
  on a two-up page, of each slot's own puzzle) printed on it. (test:
  `PropertyTest_BookQr_EveryPageCodesItsOwnPuzzle`)
- **AC-3** (happy, geometry): *Given* any book trim in CON-018's profile set,
  *when* a page is drawn, *then* the code occupies CARD-204's 2×2 cm slot
  exactly, with its full quiet zone inside that slot and no overlap with the
  grid, the band, the rule or the folio. (test: `TestBookQr_FitsTheReservedSlot`)
- **AC-4** (edge, print resolution): *Given* the book's export DPI, *when* a
  code is drawn, *then* every QR module is a whole number of device pixels (no
  resampling blur), and the module size is at or above the minimum the card
  records. (test: `TestBookQr_ModulesAreWholePixels`)
- **AC-5** (guard, dependency): *Given* the installed environment, *when* the
  dependency baseline test runs, *then* it reflects the ADR-0006 decision this
  card recorded — and fails if a dependency was added without it. (test:
  `TestDependencyBaseline_IsExactlyPillowAndNumpy`, updated only alongside the
  ADR delta)
- **AC-6** (guard, no solution leak): *Given* a printed QR, *when* it is
  decoded, *then* it carries a URL and nothing else — no grid, no solution, no
  admin path (ADR-0038/R6, CON-021). (test: `TestBookQr_CarriesOnlyAPublicUrl`)

## Guardrails

- G-1: The QR must never point at an admin-panel URL — CON-021/ADR-0038/R6 keep
  interactive play behind the admin door, and a printed admin link would publish
  it (test: `TestBookQr_CarriesOnlyAPublicUrl`).
- G-2: No new runtime dependency without an ADR-0006 revision recorded first
  (ADR-0006/R1; test: `TestDependencyBaseline_IsExactlyPillowAndNumpy`).
- G-3: The slot's geometry is CARD-204's — this card fills it, it does not move
  or resize it, and it computes no page geometry of its own (ADR-0036/R2).
- G-4: CLI and web-UI exports stay byte-identical (CON-019) — no QR on a
  single-puzzle export unless a separate card asks for one.
- G-5: Out of scope — the second QR from the same doc item ("generate your own
  puzzle from the picture") and the public solver itself; both are backlog
  entries pending the owner's "V1: only solver for book 1" decision.

## System contract

- ADR-0006/R1 — runtime dependencies are exactly stdlib + Pillow + NumPy; no
  third-party package joins without revising the ADR (check:
  `TestDependencyBaseline_IsExactlyPillowAndNumpy`)
- CON-021 — interactive play exists only as the admin panel's player, behind the
  admin door; no public or hosted page offers it (check: review-lens)
- ADR-0038/R6 — only the admin player may ship a solution to a browser; any
  public phase reopens the ADR (check: review-lens)
- CON-019 — book geometry never changes CLI/web exports (check:
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)
- ADR-0036/R2 — only COMP-007's layout functions place things (check:
  review-lens)

## Architecture context

- **FR:** FR-032 (puzzle-page placement, as amended by CARD-204), FR-044 (the
  player — the thing the QR would link to, today admin-only).
- **ADR:** ADR-0006 (dependency baseline — **this card needs a delta**),
  ADR-0036/R2, ADR-0038/R6.
- **CON:** CON-015, CON-016, CON-019, CON-021.
- **Components:** COMP-009 (`book_pdf_generator.py`), COMP-007
  (`export/layout.py`, only if the slot needs anything CARD-204 did not add).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

—
