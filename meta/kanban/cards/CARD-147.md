# CARD-147: The book PDF is written black-and-white or in colour, and says which

**Status:** blocked
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** owner, 2026-09-25 ("2 modes to pdf generator: black/white and colors … I was a bit too creative making colored pages for book 1 — then it gets more expensive. But we may add colors for book2")
**Idea:** —
**Wave:** 27
**Depends on:** CARD-146
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_page_spec.py, src/nonogram/db/models.py, migrations/, src/nonogram/admin/templates/book_setup_print.html, tests/test_book_pdf_ink_mode.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** waiting on CARD-146 — it is the last wave-26/27 card in book_pdf_generator.py

## What to implement

A book chooses how its **interior** is printed: **black-and-white** (the
default, and what Book 1 ships) or **colour** (available for Book 2 and later).
The choice is stored on the book beside the trim and margins, shown in Print
setup, and reported on the Finalise summary, because it changes what the book
costs to print.

**What is true today — verified 2026-09-25, do not re-derive from the card's
wording:**

- **The interior's content is already pure black and white.** `export/png.py`
  draws with `INK = (0, 0, 0)` on `BACKGROUND = (255, 255, 255)` and nothing
  else; a grep for any other RGB triple across the export and book pipeline
  returns nothing. No divider, guide, band, frame or answer page introduces a
  colour.
- **But the file declares colour.** Every page is composed as a Pillow `"RGB"`
  image (`book_pdf_generator.py:1060/1106/1159/1511`, and `_write_pdf` converts
  anything else at :2145), JPEG-encoded in RGB, and written with
  `ColorSpace=PdfName("DeviceRGB")` at :2158.
- **The cover is already a separate file** (CARD-135) and is **not** in scope:
  a colour cover on a black-and-white interior is the ordinary case, and the
  cover takes an uploaded image which may be anything.

So this card is not "remove the colours from Book 1" — there are none to
remove. It is: let the book say what it is, and make the interior file match
that claim rather than always declaring `DeviceRGB`.

Three things follow from writing a black-and-white interior as grayscale:

1. **Cost.** Print-on-demand interiors are priced on whether they are
   black-and-white or colour. A `DeviceRGB` interior invites the expensive
   classification for a book that has no colour in it. *(Confirm the exact KDP
   rule before relying on the number — this card's job is to make the file
   honest, not to promise a price.)*
2. **Size.** A grayscale JPEG carries one channel where RGB carries three.
3. **Memory.** CARD-145 fixed an OOM by writing one page at a time; a grayscale
   page bitmap is a third of an RGB one, so the envelope gets wider for free.

## Acceptance criteria

- **AC-1:** A book set to black-and-white exports an interior whose pages are
  grayscale and whose PDF declares `DeviceGray`, and every page's ink is
  pixel-for-pixel the same marks as the RGB rendering — nothing moves, nothing
  is lost. *test: TestBookInk_BlackAndWhiteInteriorIsGrayscale*
- **AC-2:** A book set to colour exports exactly what ships today: RGB pages,
  `DeviceRGB`, byte-identical to the pre-card export for the same book.
  *test: TestBookInk_ColourInteriorIsUnchanged*
- **AC-3:** The mode is stored on the book, survives a reopen, and defaults to
  black-and-white for a book that has none stored (every existing book).
  *test: TestBookInk_ModeIsStoredAndDefaultsToBlackAndWhite*
- **AC-4:** Print setup offers the choice and Finalise names it, so the owner
  can see which one the file they are about to upload will be.
  *test: TestBookInk_PrintSetupAndFinaliseShowTheMode*
- **AC-5:** The cover file is unaffected by the mode — an uploaded colour cover
  stays colour on a black-and-white book.
  *test: TestBookInk_CoverIgnoresTheInteriorMode*

## Engineering constraints

- **EC-1:** The mode changes the colour space only. For any book and any mode,
  the set of inked pixel positions is identical — cell size, origin, gutter,
  rules, frame and page count do not depend on it. Verify as a property over a
  seeded corpus, not on one book.

## Guardrails

- G-1: CON-019 — CLI and web A4 output stay byte-identical and
  `tests/fixtures/a4_golden/**` is NOT regenerated or edited. This card is
  book-interior only; `export/png.py`'s `INK`/`BACKGROUND`/`_MODE` are the
  pipeline's, not the book's, and are out of bounds.
- G-2: ADR-0037/R2 — no stroke weight changes. Grayscale must not soften a
  rule: pure black stays 0 and pure white stays 255, with no anti-aliasing
  introduced by the conversion.
- G-3: Do not regress CARD-145's streaming property — peak memory stays
  O(one page). The conversion happens per page, never by collecting pages.
- G-4: The cover path is out of scope (CARD-135 owns it).

## Architecture context

- **FR:** — (untraced: owner intake, `meta/architecture/inputs/raw-requirements.md`, 2026-09-25)
- **ADR:** ADR-0036/R1 (PageSpec carries the book's print geometry), ADR-0036/R2 (the panel decides no geometry)
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

**This card has no FR on purpose.** Like CARD-144's frame, it is owner intake
that the architect station has not yet formalised. Do not cite an existing FR
to make it look traced — CARD-144's review found exactly that defect (the frame
cited FR-041, the level-divider requirement, at ~15 sites) and it cost a
finding. If a citation is wanted, name the intake line.

## Worktree notes

[Baselines — read before you start] `tests/fixtures/book_baseline_card144.json`
records sha256 digests of the exported pages' **decoded bitmaps**. Changing the
interior's colour space changes those bitmaps, so a black-and-white default
will move every digest. That is the one case CARD-145's fixture `warning`
allows a successor for: record a NEW baseline under this card's number, with
`why_a_new_baseline` and a `recorded_from_commit` that can actually reproduce
the digests, and add a `superseded_by` line to CARD-144's WITHOUT rewriting any
digest in it. CARD-128's and CARD-144's reviews both checked this mechanically
(`git diff --numstat` must show insertions only on the superseded file); yours
will too.

[Sequencing] Blocked on CARD-146 because that card is the last of the current
run to edit `book_pdf_generator.py`, and wave 26 has already produced one
unpredicted conflict on the shared book fixtures between two cards that both
touched them.

[Open for the owner] Whether the mode belongs per-book (proposed here, since
Book 1 is black-and-white and Book 2 may not be) or as a global default with a
per-book override. Proposed: per-book, defaulting to black-and-white, because
every book that exists today is black-and-white in content.
