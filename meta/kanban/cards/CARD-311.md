# CARD-311: The owner uploads a divider page, and the interior prints it in place of the drawn one — four slots, the folio decided, and the type floor's hole named

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Owner request 2026-10-29, after asking whether the panel already had it. Measured answer: it does not — the dividers are drawn, and the only control is CARD-305's all-or-none toggle. The cover is the sole uploadable page in the whole panel.
**Idea:** —
**Wave:** —
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** CARD-298
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_page_spec.py, src/nonogram/admin/templates/book_setup_print.html, src/nonogram/admin/templates/book_finalize.html, tests/test_book_pdf.py, tests/test_book_workflow_steps.py, migrations/versions/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What exists today, measured

**Four divider pages, all drawn, none uploadable.** `"Easy"` / `"Medium"` /
`"Hard"` before each non-empty level (AC-254, CARD-128) and `"SOLUTIONS"` before
the answer key (AC-292). `book_pdf_generator.py:4790`'s `create_divider_page`
builds `Image.new("RGB", frame, "white")`, centres one word on the trim, and draws
the folio after it. Its own docstring: *"Its `text` is **the only thing on it** —
no band, no page number, no drawing, nothing fitted."*

**The only divider control is a checkbox** — `book_setup_print.html`, *"Print the
four divider pages"*, one toggle for all four (CARD-305,
`books.interior_divider_pages`, migration 017).

**The only uploadable page in the panel is the cover**
(`book_finalize.html` → `request.files["cover"]`). The other file input,
`/batch/from-images`, takes source pictures for puzzle generation, not book pages.

## Why this is not "copy the cover path"

Four measured collisions. Each needs a decision in this card, and none of them is
visible from the feature description.

**1. The cover's storage is a temp directory and a session key, and that is not
good enough for a book's dividers.** `_cover_dir()` is
`app.config["BOOK_COVER_DIR"]` or **`tempfile.gettempdir()/nonogram_book_covers`**;
the path lives in `session[f"book_{book_id}_cover_path"]`, and
`_cover_upload_lost` / `_forget_stale_cover` exist precisely because the file can
be **purged out from under the book**. Meanwhile the divider *toggle* persists in a
**database column**. So a book would remember whether to print dividers and forget
which images they are. **Decide where an uploaded divider lives** — and if the
answer is a DB-backed store, say what happens to the bytes (a column, a file path
plus a real directory, or a blob) and write the migration. This is the decision
that could justify splitting the card.

**2. An uploaded divider is raster by nature, and the medium is currently a
function of the PAGE KIND, not of the book.** CARD-298 shipped
`page_medium(kind)` reading `_RASTER_DECLARATIONS`, where `PageKind.DIVIDER` is
declared raster with `expires_with=("CARD-231", …)` — and ADR-0042/R2's reason for
that is explicitly that **CARD-231 will redesign the divider so the new design is
"born vector rather than the old one converted"**. An uploadable divider means the
medium depends on *this book's* data, which the model has no way to express.
**Raise it rather than work around it**: either the declaration gains a per-book
dimension, or an uploaded divider is a declared raster exception of its own with
its own reason, or the two features are mutually exclusive per book and that is
stated. `_write_pdf` refuses a representation that contradicts its kind's
declaration, so getting this wrong **refuses the page** rather than shipping it
quietly — which is the good outcome, but it will fail loudly in CARD-298's guard.

**3. CON-020's 10 pt interior type floor is bypassed by an image.** The floor is
verified by spying on text draws (`TestInteriorType_EveryFaceHoldsTheFloor`,
CARD-184; CARD-299 re-expresses it against the content stream). **An uploaded
divider has no text draws and no `Tf` sizes, so a divider carrying 6 pt lettering
would satisfy the guard while violating the constraint.** This card must say what
holds the floor for an uploaded page — a minimum input resolution, a stated
declared bound, or an explicit exemption with the reason recorded. **Silence here
ships a hole in a constraint, which is the defect class this board has spent the
week on.**

**4. The folio.** `create_divider_page` draws the page number at the frame's
bottom-outer corner **after** the word, and the interior's parity (FR-043) and
navigation assume every interior page carries one. **Does an uploaded divider still
get a folio drawn over the owner's artwork?** Decide and state it; "it looked
better without" is a decision, not an accident, and an uploaded page with no folio
is the first interior page without one.

## What to implement

1. **Four slots, not one file.** Easy, Medium, Hard, SOLUTIONS, each independently
   uploadable, each falling back to the drawn page when empty — so a book may mix
   uploaded and drawn dividers. Levels that are empty have no divider at all today;
   an upload for an absent level must not create a page (that would change the page
   count, see G-1).
2. **Fit to the interior trim, derived.** The page is
   `page_frame(self.page_spec(page_number))`, and that is **not** the cover's trim.
   Derive the target from the page spec, never a constant. Decide and state the
   behaviour for a wrong aspect ratio (letterbox, crop, or refuse) and for an image
   whose resolution is below the book's DPI — and make the refusal path a **refusal**,
   not a silent upscale.
3. **Honour CARD-305's toggle, and check both paths honour it the same way.**
   Measured asymmetry: the SOLUTIONS divider is gated at yield time
   (`if self.divider_pages:` at `book_pdf_generator.py:7225`), while the level
   dividers arrive as `DividerPagePlan` entries and are gated when the **plan** is
   built (`:7180`). An upload must not make those two disagree.
4. **Reuse the cover path's hardening rather than re-deriving it**, and keep every
   guard it earned: decode and `exif_transpose` (a phone photo is stored sideways
   with a rotate tag PNG does not carry), re-encode server-side, name the file from
   **the book id and never the client's filename**, and honour only files inside the
   store's own directory so a stored value cannot make an export read anything
   else. **The defect not to repeat is on the record:** until CARD-135 the cover
   upload kept the *filename* and dropped the image, so no export could ever print
   it.

## Acceptance criteria

- **AC-1** (an uploaded divider reaches the reader): *Given* a book with an image
  uploaded for a level, *when* the interior is exported, *then* that level's
  divider page is the uploaded image and no other page changes.
- **AC-2** (mixing works, derived over all four slots): *Given* a book with some
  slots filled and some empty, *then* each filled slot prints its image and each
  empty one prints the drawn word — enumerated over the slots from the page plan,
  not from a written list.
- **AC-3** (geometry is untouched): *Given* any combination of uploads, *then* the
  interior's page **count**, every page **number**, FR-043 parity and the TOC rows
  are byte-for-byte what the same book produces with no uploads. (**gate**: an
  upload changes ink, never geometry — this is the cheap property that separates
  this card from CARD-305.)
- **AC-4** (the refusals are refusals): *Given* an image of the wrong aspect ratio,
  below the book's DPI, or not an image at all, *then* the upload is **refused with
  a message naming which**, and the stored state is unchanged. (**Two mutants per
  ADR-0039/R1**, one inside the claim and one at its edge.)
- **AC-5** (persistence survives a purge): *Given* an uploaded divider and a
  restart or a purged temp directory, *then* either the image is still there or the
  book plainly says it is gone — never a book that silently prints the drawn word
  where the owner put a picture. (**This is the cover's known weakness; this AC is
  the card's answer to decision 1 and must be measured, not asserted.**)
- **AC-6** (the medium stays declared): *Given* a book with an uploaded divider,
  *then* `page_medium`'s declaration for that page and the written representation
  **agree**, so `_write_pdf` does not refuse it — and the declaration says why an
  uploaded page is raster. (See collision 2; the agreement is CARD-298's guard and
  this card must not weaken it.)
- **AC-7** (an owner render exists): *Given* an uploaded divider, *then* a rendered
  interior is produced under `~/Documents/nonogram-reviews/CARD-311/`.
  **Standing rule: image-pipeline changes need a rendered eyeball, not just green
  tests** — and this card's whole subject is how a page looks.

## Engineering constraints

- **EC:** across a seeded corpus of books spanning trims, page counts, tier mixes
  and upload combinations, the interior's page count and every page number are
  identical to the same book with no uploads — minimum case count asserted inside
  the test.

## Guardrails

- **G-1: an upload must not change the page count.** The page already exists; this
  card changes what is printed on it. A slot for an absent level creates nothing.
  CARD-305 owns the count-changing decision and its consequences (TOC rows, spine
  width, KDP page count); this card must not reopen them.
- **G-2: do not touch `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`
  or the A4 golden.** Neither is a book interior. If either reds, that is a
  **finding to raise**, not a baseline to refresh.
- **G-3: the 21 book baselines must not move.** No fixture book uploads a divider,
  so an upload path that moves a baseline has changed the drawn page too — a
  finding, not a re-record. `tests/fixtures/**` is not regenerated.
- **G-4: do not weaken CON-020's floor or its verifying test to accommodate an
  image.** Either the floor holds for uploaded pages by some stated mechanism, or
  the exemption is declared with its reason. Making the guard blind is the one
  outcome this card must not produce.
- **G-5: no test deleted, renamed, skipped or merged** — `parametrize` ids
  included. (**gate**: node-id set difference with `-o addopts=''`.)
- **G-6: never trust the client's filename, and never read a stored path outside
  the store's own directory.** Both guards exist in the cover path for a reason;
  re-use them rather than re-deriving them.
- **G-7: do not convert any page to vector.** That is CARD-309's, and an uploaded
  divider is raster by nature — see collision 2.
- **G-8: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT`).

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R2 — a raster page is declared with a reason; an expired declaration is a defect (check: CARD-298's derived guard; **this card adds a reason, or a per-book dimension, and must not bypass it**)
- ADR-0042/R1 — interior pages are operators (check: review-lens — an uploaded divider is a permanent counter-example and the ADR should say so)
- ADR-0036/R1-R2 — the sheet and the page geometry come from the PageSpec (check: the A4 golden / review-lens)
- CON-019 — book geometry never changes the CLI's or web UI's exports, byte-for-byte (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
- CON-020 — the 10 pt interior type floor (check: CARD-184's test, re-expressed by CARD-299 — **bypassed by an image; see collision 3**)
- INV-013 — the interior holds no cover page; parity counts from interior page 1
- FR-043 — the interior's page order and parity
- ADR-0039/R1-R2 — a claim needs a control that CAN fail; a guard's set is derived and an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0006/R1 — the dependency baseline is exactly stdlib + Pillow + NumPy (check: **DEAD REF** — verify the substance; see CARD-307)

## Architecture context

- **FR:** FR-030, FR-032, FR-040, FR-041, FR-043
- **NFR:** NFR-008
- **ADR:** ADR-0042/R1-R2, ADR-0036/R1-R2, ADR-0039/R1-R2
- **Components:** COMP-009
- **Trace:** a new AC set belongs to the FR that orders the interior's sections; **do not** write a Trace line promising an ADR-0042 rule row — `trace.yml` holds none (measured 2026-10-29, prose only at `:1813` and `:1853`), the mistake CARD-298 inherited.

## Worktree notes

- **Serializes on two declared hotspots**, `src/nonogram/admin/app.py` and
  `src/nonogram/admin/book_pdf_generator.py`, so it cannot run beside any card
  touching either. It also overlaps **CARD-231** (which redesigns the *drawn*
  divider) on the same page and **CARD-309** (which converts interior pages) on the
  medium — order it against both deliberately rather than by arithmetic.
- **CARD-231 is the sibling feature, not a dependency.** That card makes the
  *generated* opener richer — large type, dots, range, a line of what to expect. It
  is `ready`, 1d, unscheduled, and carries `Revision pending: true`. If both land,
  the drawn page CARD-231 designs is the fallback this card prints when a slot is
  empty, so the two are complementary — but whichever lands second inherits the
  question of whether an uploaded image should be able to replace a designed page
  at all. Worth the owner's view before the second one starts.
- **The cheap half and the expensive half are separable** if this needs splitting:
  printing an uploaded image in place of a drawn one is small; making it survive a
  purge (AC-5) is where the storage decision and a migration live.
