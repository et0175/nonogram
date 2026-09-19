# CARD-099: The generated-puzzles page reads as pictures, not as a list — group a picture's sizes, and stop miscounting

**Status:** done
**Priority:** P2
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** red -> green -> mutation check (6 mutants, all caught)
**Branch:** card/099-group-a-pictures-puzzles
**Worktree:** ../PythonProject4-CARD-099
**Source:** owner, 2026-09-19 ("open a card for grouping puzzles on the generated page") — CARD-069's item 5, left out deliberately; plus a miscount found while scoping it
**Idea:** —
**Wave:** 1
**Depends on:** CARD-069 (merged 19564e5) — the page only has several puzzles per picture because of it
**Touches:** src/nonogram/admin/app.py (the generated_puzzles route's counts and ordering), src/nonogram/admin/templates/generated_puzzles.html, src/nonogram/admin/static/admin.css, tests
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-19
**Closed:** 2026-09-19
**Actual:** 0.5d
**Merge commit:** —
**Blocked by:** —

## Why

CARD-069 made a picture produce one puzzle per ticked size. The page that
shows the result was written when those were the same number, and it shows.

**1. It miscounts, and the miscount is mine.** The summary line reads
`"{{ puzzles|length }} puzzle(s) from {{ total_images }} picture(s)"`, where
`total_images` is `batch_job.total_count` — the number CARD-069 changed from
`len(images)` to the planned *puzzle* count, so that the batch record would
match what the batch actually makes. Both ends are now the same number and
the sentence is nonsense. Measured on this tree, one picture with two sizes
ticked:

> **2 puzzles from 2 pictures.** Approve the ones worth printing.

This is a defect introduced by CARD-069 and not caught by its tests, which
asserted the puzzles and their names rather than the page's prose. It is
listed first because it is wrong now, on `main`, rather than merely
unbuilt.

**2. Puzzles from one picture do not read as a group.** Since CARD-069 they
carry the extent in their names — `"eagle-silhouette1 (11x20)"` — so they are
distinguishable and they sort together, which was enough for that card's
AC-7. But the page is a flat list of cards, each repeating the same `Source`,
and a reviewer approving a batch has to notice by reading filenames that
three of the cards are the same picture at three sizes. That is the item
CARD-069 left out deliberately, because how it should look is the owner's
call and not a detail to inherit from whoever implemented it.

## What to implement

1. **Fix the count first, with its own test.** The sentence needs two honest
   numbers: how many puzzles were made, and how many *pictures* they came
   from. The picture count is available — the puzzles carry `source_image` —
   and the batch's `total_count` should stay what CARD-069 made it (the
   planned puzzle count), because the batch record's job is to say what the
   batch was for. Do not fix the sentence by reverting that.
   Also state the shortfall honestly when there is one: `filtered_count` is
   currently `total_images - len(puzzles)`, which after the fix means
   "planned but not made" — quality-filtered, skipped or never started — and
   the wording should not call all of that "filtered out by the quality
   threshold".
2. **Group the cards by source picture** — the presentation choice, below.
3. **Order deterministically**: pictures in the order they were uploaded,
   and within a picture by extent, so two reviewers see the same page and a
   re-render does not reshuffle it.

## The presentation choice (for the owner, before item 2 is built)

Three shapes, cheapest first. They are not exclusive — (a) is a prerequisite
for neither (b) nor (c), but it is the smallest thing that removes the
confusion.

- **(a) A heading per picture.** The cards stay as they are; a small heading
  — the filename, the ink ratio, and "3 sizes" — precedes each picture's
  cards. Cheapest, no layout change, and enough for a reviewer to see the
  grouping at a glance.
- **(b) One card per picture, its sizes inside it.** The picture is shown
  once with its grids side by side, each with its own extent, grade and
  Approve control. Reads best for a picture with two or three sizes; a
  bigger change to the card markup and to how per-puzzle actions are wired.
- **(c) A "sizes" badge and a filter.** Leave the list flat, mark each card
  with which of its picture's sizes it is (`11×20 · 1 of 3`), and let the
  list be filtered to one picture. Least disruption to an existing habit of
  scanning a flat list; does least for the confusion.

**Recommendation: (a) now, and keep (b) as a follow-up if the owner wants
it after seeing a real batch.** (a) is reversible, is a template change
only, and can be judged on a rendered page in minutes; (b) is worth doing
only once somebody has reviewed a multi-size batch and can say what they
actually want to compare.

## Acceptance criteria

- **AC-1** — for a batch of one picture with two sizes ticked, the summary
  line says two puzzles and **one** picture.
  *test:* `TestGeneratedPage_CountsPuzzlesAndPicturesSeparately`
- **AC-2** — for a batch of three pictures at one size each, the same line
  says three and three: the single-size case is unchanged.
- **AC-3** — the shortfall wording distinguishes "filtered out by the
  quality threshold" from "not made" where the page can tell them apart, and
  says nothing it cannot support where it cannot.
- **AC-4** — a picture's puzzles appear together, in extent order, with the
  grouping visible on the page (whichever shape the owner picks).
- **AC-5** — a batch where every picture has one size renders exactly as it
  does today apart from the count fix — the regression guard, pinned before
  the grouping is built.

## Guardrails

- G-1: No change to what is generated or stored — this card is the page.
  `get_batch_puzzles`, the batch record and the puzzle rows are read-only
  here.
- G-2: Do not revert CARD-069's `create_batch(count=planned)`. The batch
  record means "what this batch is for"; the page's sentence is what needs
  fixing.
- G-3: The per-puzzle Approve/Reject controls keep working for every puzzle,
  grouped or not — a grouping that made one control stand for several
  puzzles would be a silent change to what Approve means.
- G-4: Admin-only; nothing under `sourcing/`, `orchestrator.py` or the CLI.
- G-5: Commit only your own files — explicit pathspecs.

## Architecture context

- **FR:** — (admin presentation; no requirement changes)
- **Components:** the admin panel's review surface
- **Trace:** none

## Worktree notes

—

### Delivered 2026-09-19

**The count (item 1).** The route computes two numbers where it used one.
Puzzles are counted from the rows on the page; pictures are counted from the
sources those rows name, through the same grouping the page renders, so the
sentence and the headings can never disagree. `batch_job.total_count` keeps
CARD-069's meaning — what the batch planned — and is now named
`planned_count`, which is the name it should have had when its meaning
changed. Measured end to end on `butterfly.png` with two sizes: **"2 puzzles
from 1 picture"**, where `main` says "2 puzzles from 2 pictures".

**The shortfall (AC-3).** `"; N of the M planned was/were not made"`, and no
cause. The page genuinely cannot tell quality-filtered from skipped-as-too-
elongated from refused-by-the-store from never-started — they all arrive as an
absent row — so the old clause naming the quality threshold was a guess
dressed as a fact. Now a picture whose only size the clock never reached reads
"1 of the 2 planned was not made" rather than being blamed on its quality.

**The grouping (item 2, option (a)).** A `<section class="picture-group">` per
picture: a heading with the filename, a `N sizes` badge where there is more
than one, and a rule to the right margin. The cards themselves are untouched
— which is the point of option (a), and is what keeps G-3 true without
thinking about it: every puzzle still carries its own Approve and Reject.

**The ordering (item 3) is the part that was not free.** `PuzzleFilter`'s
default sort is `batch_id,-size,quality`, so the page is handed its puzzles
widest-first with the pictures interleaved — a picture's sizes were never
adjacent to begin with. `group_by_picture` therefore computes both orders:
pictures by when their first puzzle was made (the upload order, since the
generate loop iterates `(picture, option)` pairs built in that order), sizes
by area ascending. Both fall back to name and extent, so the page is a pure
function of the rows.

**The ink ratio is not in the heading**, though the card's sketch of option
(a) had it there. It is a property of the uploaded file, which this page does
not have — the batch record carries no image list and the puzzle rows carry
only the filename. Getting it here would mean either re-opening the picture
per heading or widening what a batch stores, and neither is worth it for a
number the preview page already shows while the sizes are being chosen.

**A random batch** has no pictures behind it, so it renders one unlabelled
section and a sentence that claims none: `"10 puzzles."` rather than an
invented picture count. The old wording said "from N pictures" for random
batches too.

### Verified by eye

`~/Documents/nonogram-reviews/CARD-099/` — `grouped-top.jpg` (the lede and
`butterfly.png` at two sizes) and `grouped-three-sizes.jpg` (`dear.png` at
10x10, 19x19 and 29x30 under one heading). The three-size shot is the argument
for the card: side by side it is obvious at a glance that 10x10 has lost the
deer entirely and 29x30 has kept it, which is the comparison a reviewer was
previously making by reading filenames off scattered cards.
`grouped-page.html` is the rendered page itself, with the grids inlined.

### Tests

`tests/test_card_099_grouped_page.py`, 19 tests. **AC-5 first** — three
pictures at one size each still reading "3 puzzles from 3 pictures", and a
control pair per puzzle — then the defect, the shortfall wording, the random
batch, the grouping and the two orders.

**Mutation check** — six mutants: the unnamed group counted as a picture, the
planned count used as the picture count (the original defect), pictures
ordered by name, sizes left in the order they arrived, the size badge on a
single-size picture, and the shortfall blaming the quality threshold again.
The name-ordering mutant **survived the first run**: every other test happened
to upload its pictures in alphabetical order, so sorting by name passed them
all. `test_group_by_picture_follows_the_upload_order_not_the_alphabet` and its
page-level twin were written for that, and all six are caught now.

**Full suite: 3,495 passed, 0 failed**, 26 skipped, one deselection
(`test_size_configuration_applied`, unrelated).
