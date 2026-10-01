# CARD-147: The book PDF is written black-and-white or in colour, and says which

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/147-interior-ink-mode
**Worktree:** —
**Source:** owner, 2026-09-25 ("2 modes to pdf generator: black/white and colors … I was a bit too creative making colored pages for book 1 — then it gets more expensive. But we may add colors for book2")
**Idea:** —
**Wave:** 27
**Depends on:** CARD-146
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_page_spec.py, src/nonogram/db/models.py, migrations/, src/nonogram/admin/templates/book_setup_print.html, tests/test_book_pdf_ink_mode.py
**Review score:** 9.5 (1 cycle + fix)
**Started:** 2026-10-01T07:10:00Z
**Closed:** 2026-10-01T09:30:00Z
**Actual:** 0.5d
**Merge commit:** 0fa9302
**Blocked by:** — (cleared 2026-10-01: CARD-146 merged b9a17d3)

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
- [Env] forge 2026.8.17
- [Blocker cleared] CARD-146 merged at b9a17d3.
- [The card's baseline note is two recordings stale — read this instead] It names
  `book_baseline_card144.json`. The live fixture is **`book_baseline_card146.json`**
  (`tests/helpers/book_corpus.py:100`), and the chain is now card145 → card128 → card144 →
  card149 → card146. The *instruction* in the note is right and still applies; only the
  filename is out of date. Supersede the **card146** file, not card144's.
- [This is the largest baseline change yet, and the card understates it] Every previous card in
  the chain moved one or two pages — CARD-149 page 1, CARD-146 page 3. Making black-and-white
  the default changes the colour space of the **whole interior**, so **all eleven digests move**
  and `interior_bytes` changes substantially. `changed_pages` should name all of them, and the
  page-by-page verification the precedent demands is still owed: it is the evidence that every
  page moved *for the stated reason* rather than that something else moved too.
- [Schema change, and the one that actually ships] This is the first card since CARD-148 to
  touch `src/nonogram/db/models.py` and `migrations/`. Nothing else is in flight there. Note the
  live panel runs on Postgres (`nonogram_poc`), not the sqlite file, so the migration has to be
  good on Postgres — and CARD-148's work means `alembic upgrade head` now resolves its driver
  explicitly, so the deploy path is sound.
- [CON-020 does not bite here] The constraint added on 2026-09-30 governs interior **type size**
  — no text below 10 pt, sizes physical rather than bare pixels. A colour-space change touches
  no type size. It is listed so nobody has to wonder.
- [The card's "no FR on purpose" paragraph is load-bearing] CARD-144's review found that card
  citing FR-041 — the level-divider requirement — at roughly fifteen sites to look traced, and
  it cost a finding. Do not invent a citation here. Naming the intake line is the honest form.

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

[DECIDED by the owner, 2026-09-25] **Per-book**, not a global default with an
override. The mode is stored on the book beside its trim and margins, and
defaults to black-and-white for any book that has none stored — which is every
book that exists today, all of them black-and-white in content. Book 1 is
black-and-white; colour is available per book from Book 2 onward.

### Cycle 1 review (2026-10-01)

- [Review 1/3] **9.5** · risk LOW · lane FAST ·
  `meta/review/20261001T035109Z-CARD-147-cycle1.yml` · 0 critical, 0 important, 7 minor.
  **Ready to merge**, no blocking conditions. Suite reproduced exactly: 5500 / 5491 / 2 / 7.
- **The digest question is settled, and the answer matters.** The reviewer tested both halves
  by experiment rather than argument. **(b) is load-bearing**: `convert("L")` is the exact
  identity on all 256 grey levels, and through JPEG at four quality settings a grey RGB image
  and its `L` counterpart decode to identical luma, max diff 0 — with the arithmetic to match
  (libjpeg's `19595+38470+7471 = 65536`, so `(65536v+32768)>>16 = v`; a constant chroma plane
  level-shifts to all-zero DCT and survives quantisation). **(a) cannot be the whole story**:
  `convert("RGB")` on an `L` image is a lossless `v → (v,v,v)`, so it blinds the digest to the
  colour-space *declaration* and to nothing else. Proved by counterfactual: **softening one
  pixel by one level moves the digest.**
- So the baseline **is** still evidence — of the ink, not of the colour space. The card's
  sentence welds two claims the digests cannot both carry; only the second follows. The colour
  space is established separately and correctly, by `interior_bytes` and by `pdf_image_objects`,
  a deliberate non-normalising second reader. The fixture's own `interior_colorspace_note` says
  this two keys later, so the document disambiguates itself — Minor (F-006), not a defect.
- **And AC-1 never rested on the baseline anyway**: its evidence is two tests reading the two
  written files directly, which the reviewer re-derived itself off the rendered PDFs — all 11
  pages, max luma diff 0, ink masks equal, pure-black and pure-white counts equal page for page.
- **Migration 013 verified live on Postgres**, which is the database that matters: Alembic's
  `PostgresqlImpl` does not override `requires_recreate_in_batch`, so batch mode emits a plain
  `ALTER TABLE … ADD COLUMN` with no recreate and no FK hazard; `pg_dump --schema-only` before
  and after a downgrade/upgrade round trip is **identical**; probe rows cleaned up and
  `nonogram_test` left exactly as found. sqlite's recreate path was exercised separately with
  two inbound FKs and three indexes — all survived.
- Mutation: **11 mutants, 9 killed.** Both survivors argued rather than waved away: the
  migration's explicit `UPDATE` backfill is **confirmed-redundant** (a separate mutant proves
  the `server_default` layer is covered, and the UPDATE is a provable no-op on both supported
  backends), and `_write_pdf`'s new `ValueError` guard is unreachable because the dict lookup
  raises `KeyError` first.
- **F-001 (minor) is the finding worth remembering**, because it is a convention this project
  states explicitly: `test_no_mark_moves_on_any_page_bitmap` computes `page.convert("L")`
  *itself* and compares it to `rgb[:,:,0]` — so it tests Pillow, not the writer, while its
  docstring claims "the conversion is the writer's own". CLAUDE.md names exactly this
  ("prefer an independent second implementation over re-deriving a value with the same function
  you're testing"). G-2 is still genuinely enforced, by the file-level comparisons, and the
  softening mutant was killed by two other tests.
- F-004 (minor) `test_book_floor.py` upgrades to `"head"` where it means `"013"` — two
  characters, and it will silently test the wrong thing as soon as migration 014 exists.
- F-007 (minor, **an owner decision older than this card**) the `superseded_by` back-pointer:
  each fixture's `warning` ends "…and **says so here**", and its prohibition is scoped to
  *regenerating digests*, which an additive key is not — so the card body's reading is the
  better one and the chain should carry back-pointers. But only card145 and card128 do; card144,
  card149 and card146 never got one. It bites hardest on card146, which is **still live
  evidence** (hardcoded as `PRE_CARD_BASELINE` for AC-2). Debt three cards old, flagged not
  filed against this diff.
- **No invented FR citation** — confirmed by the reviewer: the three FR ids in added lines are
  FR-043 about the cover being a separate file (which is what it says), one pre-existing FR-030
  docstring line edited in place, and one FR-041 *inside a comment explaining why no FR is
  cited*, naming CARD-144's defect. The mistake was not repeated.
- System contract: 45 rules — 14 ✓, 31 ⚠, 0 ✗. ADR-0036/R1 holds and was checked the hard way:
  the mode is genuinely not on `PageSpec` (grep of `src/nonogram/export/` returns nothing, and a
  test asserts `page_spec()` equality across modes on all 14 EC-1 books).
- [Review sync] 1 report → meta/review/

### Orchestrator gates (2026-10-01)

- [Build gate] PASSED on bd59050: **5500 collected, 5491 passed, 2 failed, 7 skipped** — main
  collects 5459, so this card adds exactly its 41 and nothing else. The two failures are the
  long-known stale-heading assertions.
- [Guard] The headline claim verified independently: **zero digests moved** (compared page by
  page against card146's), `changed_pages: []`, and `book_baseline_card128/144/145/146/149.json`
  are **all five byte-identical**. `interior_bytes` 2,680,175 → 2,273,541, **−15.17%**.
- [Orchestrator error, corrected by the implementation] My brief gave the baseline as "5450
  collected, 5441 passed". Both were wrong: 5450 was the *passed* count on main, taken from a
  merge-gate line reading `2 failed, 5450 passed, 7 skipped`. Main collects **5459**. The agent
  caught the conflation and did the arithmetic correctly. Worth recording because the same
  passed-for-collected slip may be in earlier briefs this session.
- [Prediction wrong, and the agent said so first] Both the card and the orchestrator note
  predicted all eleven digests would move. None did. That is the card's most interesting result
  and its central evidential claim — the *unmoved* digests being offered as proof that the
  colour space changed and the ink did not — so the reviewer has been asked to untangle the two
  reasons given for it, because only one of them is load-bearing: if the reader's
  `convert("RGB")` blindness is doing the work rather than the luma-plane identity, the baseline
  proves far less than it appears to.
- [Noted, not decided] The implementation followed the orchestrator's instruction (every earlier
  fixture byte-identical) over the card body's (add a `superseded_by` line to the superseded
  file), and **flagged the divergence rather than choosing it silently** — observing that
  card144, card149 and card146 were none of them given that line by their successors, while
  card145 and card128 were. The chain is already inconsistent; the reviewer decides which way it
  should settle.
### [Fix 1] — cycle-1 review, F-001 and F-004 (test-only)

Two low findings, both latent rot rather than present bugs. The card scored 9.5
with no Critical and no Important, so neither was a gate. `src/`, `migrations/`
and every fixture are untouched: `git diff --stat -- src migrations
tests/fixtures` is empty.

**F-004 — the migration-012 detour is pinned to `"013"`, not to `"head"`.**
`tests/test_book_floor.py::TestMigration012::test_no_backfill_and_a_downgrade_that_drops_the_column`
took its ORM read at `"head"` where it meant revision `013`. Today those are
the same revision; the day 014 lands they stop being, and the two assertions
after the return to 012 — `"floor_overrides" in columns()` and
`overrides() == {"Legacy": None}`, the guard against sqlite's batch recreate
losing the column in 013 — would quietly start meaning something else, with
nothing failing to say so. One string, `"head"` → `"013"`. The round trip is
otherwise unchanged: real `upgrade` → ORM read through `BookManager` →
`downgrade 012` → `downgrade 011` → `upgrade 012`, every assertion kept. The
comment above the call now says why it is the literal revision and not `head`,
and the Worktree notes sentence above ("takes its ORM read at head") is
superseded by this block.

**F-001 — the pre-encode G-2 test now bites on the writer.**
`test_no_mark_moves_on_any_page_bitmap` computed `page.convert("L")` *itself*
and compared it to `rgb[:, :, 0]`. That re-derives the value under test with
the same function the writer uses, which CLAUDE.md names explicitly ("prefer an
independent second implementation over re-deriving a value with the same
function you're testing") — so the test verified Pillow's determinism while its
docstring claimed "the conversion is the writer's own".

It now reads what `_write_page` actually produced. A wrapper around
`BookPDFGenerator._write_page` records the `"RGB"` page the writer was handed,
and a recorder on `Image.Image.save` captures the image the writer handed to
the JPEG encoder; the comparison runs inside that page's own write and drops
both when the frame returns, so nothing is collected and G-3 (peak memory of
one page bitmap, CARD-145) is not traded away to take the measurement. Every
existing assertion is kept, retargeted to the captured page: identity on luma,
identical ink mask at `INK_LEVEL`, no new grey level, equal pure-black and
pure-white counts, and the `checked == BASELINE_PAGE_COUNT == 11` floor, now
asserted after the export rather than after the stream.

**Mutation proof, the reviewer's own M5a** — `_write_page` doing
`page.convert(mode).point(lambda v: 1 if v == 0 else v)`, one new intermediate
level destroying pure black:

| | mutant applied |
|---|---|
| test as it was (commit `bd59050`) | **1 passed** — mutant survives |
| test as repaired | **1 failed** — `AssertionError: page 1 moved` |

`src/nonogram/admin/book_pdf_generator.py` was restored immediately after;
`git diff --stat -- src` is empty.

**Suite:** 5500 collected, 5491 passed, 2 failed, 7 skipped — unchanged from
the card's own baseline. The two failures are the known pre-existing ones
(`test_size_configuration_applied`, `test_batch_creation_form_renders`).

**Not fixed, left open by the owner:** F-002 (`_write_pdf`'s unreachable
`ValueError` guard), F-003 (the migration's confirmed-redundant `UPDATE`),
F-005 (`_write_page`'s `mode="RGB"` default), F-006 (the baseline's conflated
sentence), F-007 (the `superseded_by` chain), F-008 (`book_proof` still
DeviceRGB), and the four model-wide dead check refs.

**Databases:** none created, dropped or recreated. `nonogram_test` is still at
revision `013` with `books` empty, as found (verified after the suite);
`nonogram_dev` and `nonogram_poc` were not touched. F-004's test runs entirely
on sqlite under `tmp_path`.

- [Guard] F-001's repair proven by the orchestrator against the reviewer's own mutation
  (`_write_page` softening pure black by one level): the **repaired** test FAILS on it, and the
  **old** test — restored from bd59050 and run against the same mutant — **passes**. The hole
  was genuinely closed rather than moved. Tree restored afterwards; `src/`, `migrations/` and
  all six fixtures confirmed untouched by the fix commit.
