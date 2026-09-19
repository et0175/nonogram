# CARD-069: Up to three size options per picture, one puzzle per size

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false  _(three decisions recorded 2026-09-19 — see Decisions)_
**Skill:** python-pro
**TDD:** red -> green -> mutation check (4 mutants, all caught)
**Branch:** card/069-size-options-per-picture
**Worktree:** ../PythonProject4-CARD-069
**Source:** owner, 2026-09-12: "possibilities to add/remove sizes (and corresponding predicted outputs) — actually, we need to have 3 possible options per picture: min, max and fixed"
**Idea:** —
**Wave:** —
**Depends on:** CARD-067 (merged 9c97d88 — same page, and the prediction endpoint this builds on)
**Touches:** src/nonogram/admin/image_manager.py (a picture carries a list of size options), src/nonogram/admin/app.py (preview save, the generate loop, the batch size record, the results lines), src/nonogram/admin/templates/image_preview.html, src/nonogram/admin/templates/generate_batch.html, tests (CARD-058/061/062/064/065 all assert against a single size)
**Review score:** —
**Started:** 2026-09-19
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Decisions taken on starting, 2026-09-19

The card leaves three things to decide. Two it delegates in as many words
("decide whether... and say which"); the third is the owner's.

**1. Four options, not three — one per mode (owner, 2026-09-19).** The card
says three (fixed, min, max), from the 2026-09-12 note. There are four modes,
and `short` is not decorative: it is what the **small** preset sets — 10 on
the short side, the long side following the picture (CARD-061) — so a picture
created from that preset starts in a mode a three-option UI could neither show
nor re-add, and dropping it would delete a choice the page offers today. The
cap is therefore "at most one option per mode", which is four.

**2. Un-ticking the last option is refused, not a removal.** The card asks
whether removing the last option should remove the picture. It is refused,
with a message pointing at CARD-067's Remove button. Removing a picture
deletes the uploaded file; inferring that from "I unticked a size" makes a
destructive act out of a sizing tweak, and the explicit button is one click
away. A picture with no sizes would also have to mean something in the
generate loop, and "silently contributes nothing" is the worst of the
available meanings.

**3. Adding a mode that is already there replaces its value.** AC-5 asks
refuse-or-replace. Replace: the UI is a tick per mode with its own value box,
so "add fixed 25 when fixed 20 exists" is a user editing a number, not
creating a duplicate. Refusing would make the obvious gesture an error.

**Naming (AC-7), spelled out.** When a picture yields **more than one**
puzzle, every name from it gains its extent — `"c11 (15x10)"` — whether the
name was typed or derived from the filename. When it yields one, the name is
untouched, which is what keeps AC-3's "behaves exactly as today" true down to
the string. So the suffix marks *the reason* two names could collide, rather
than appearing on every puzzle in the system.

## Why and decision (owner, 2026-09-12)

A picture currently carries exactly one size (`size_mode` + `size_value`)
and the batch makes exactly one puzzle from it. The owner wants up to three
options per picture — min, max and fixed — each with its own predicted
output, and **one puzzle per selected size**: a picture with two options
ticked yields two puzzles in the batch.

Naming, per the owner: either a name per option, or the size appended to the
generated name. Default to appending the size (e.g. "c11 (15x10)") and let a
typed name win, so two puzzles from one picture are never
indistinguishable.

This is the one item of the 2026-09-12 review that changes the data model,
which is why it is last and on its own.

## What to implement

1. **A picture carries a list of size options**, not one. Each option is a
   `(mode, value)` pair as today (`fixed` with a value, `short` with a
   value, `min`, `max`), with at most one option per mode. The default for a
   freshly uploaded picture stays exactly one option, the batch preset's, so
   nothing changes for a user who doesn't touch it.
2. **Per-option predicted output.** Each option shows its own extent, fit
   status and note (CARD-064's fits / moved-to-Large / cannot-fit), through
   CARD-067's prediction endpoint.
3. **Add and remove options** on the preview card, capped at the three
   modes. Removing the last option is the same as removing the picture from
   the job (CARD-067) — decide whether to block it or to treat it as a
   removal, and say which.
4. **Generation: one puzzle per option.** The batch loop iterates
   `(picture, option)` pairs. Per option, everything CARD-062 and CARD-064
   established applies unchanged: the ±1 retry on abandonment, the move to
   Large, the skip, and the result lines — each naming the picture *and* the
   size, since a picture can now appear several times.
5. **Everything downstream that assumed one puzzle per picture** has to
   follow: the batch's `sizes` record, the "Generated N puzzle(s) from M
   image(s)" line (N is no longer bounded by M), the confirmation page's
   one-row-per-picture table, and the generated-puzzles page, where puzzles
   from one picture should read as a group.
6. **The older tests assert a single size** (CARD-058, CARD-061, CARD-062,
   CARD-064, CARD-065 and `test_image_batch_size_fix`). Update them
   deliberately to the single-option default, with replacements, never by
   deletion.

## Acceptance criteria

- **AC-1** — a picture with fixed 20 and min ticked produces two puzzles in
  one batch, at the two predicted extents, with distinguishable names.
- **AC-2** — each option shows its own predicted output and status on the
  preview and the confirmation pages, including one option that fits and one
  that moves to Large on the same picture.
- **AC-3** — a picture with one option behaves exactly as today: same
  extent, same name, same result lines (pin the current behaviour first, so
  the regression is visible).
- **AC-4** — per option, CARD-062's ±1 retry and CARD-064's move/skip act
  independently: one option can be skipped while another generates from the
  same picture, and the results say which size was skipped.
- **AC-5** — at most one option per mode; adding a duplicate mode is
  refused or replaces the existing one (state which); the UI cannot exceed
  three options.
- **AC-6** — the batch's recorded sizes and the generated count match what
  was actually produced, with more puzzles than pictures.
- **AC-7** — names never collide for one picture: two options give two
  distinct names, and a typed name is kept (with the size still
  distinguishing them).

## Guardrails

- G-1: The sizing rules themselves do not change. `size_fit()`,
  `MIN_KEPT_SHARE`, `SIZE_PRESETS`, `derive_extent` and the retry stay as
  they are; this card changes how many of them run per picture.
- G-2: A picture with one option is byte-identical in behaviour to today
  (AC-3) — this is the regression risk that matters.
- G-3: Do not delete or weaken the existing single-size tests; update them
  with replacements.
- G-4: Admin-only; no edits under `sourcing/`, `orchestrator.py`, `cli.py`
  or the web adapter.

### Delivered 2026-09-19

**The model (item 1).** `ImageFile.size_options` — a `SizeOption(mode, value)`
list, one per mode, at most four. A freshly uploaded picture gets exactly one,
the batch preset's, so a batch nobody re-sizes is the batch it always was.
`size_mode`/`size_value` remain the **first option's**, in both directions:
`update_image_size` writes through to it, and every caller that predates this
card keeps the answer it had.

**The fits (item 2).** `size_fits()` returns one `OptionFit` per option, each
judged by `_size_fit_for(mode, value)` — the rule `size_fit()` itself now
calls. One implementation, so a per-option verdict cannot drift from the one
the page used to show (G-1: no sizing rule changed).

**Generation (item 4).** The loop iterates `(picture, option)` pairs built up
front, so the counts, the clock's "not started" list and the results lines all
speak about the same unit of work. CARD-062's ±1 retry and CARD-064's
move-to-Large and skip act per option, and the results lines carry the size
when a picture has more than one — `"wide.png (fixed 20): moved up to Large"`.

**Counts (item 5).** The batch records every ticked size and plans
`sum(len(options))`, not `len(images)`. The two stopped being the same number
with this card.

**Naming (AC-7).** A picture with several options puts its extent in every
name from it — `"eagle-silhouette1 (11x20)"` — typed or derived. With one
option no name is written at all, which is what keeps AC-3 true down to the
string.

**The page (items 2-3).** The existing mode select and cells box stay as the
picture's first size; beneath them, **"Also make this picture at"** offers the
other three modes as toggles, each showing its own predicted extent and its
own moved/skipped warning. Server-rendered from the same rule — no sizing
arithmetic in the browser (CARD-067 AC-6), and a POST per toggle rather than a
fetch, so two quick clicks cannot leave a card showing a size it is not set to.

### The three decisions, as built

Four options not three (owner), un-ticking the last one refused rather than
treated as removing the picture, and adding an existing mode replaces its
value. Reasoning in the Decisions section above; each has a test.

### Verified by eye

`~/Documents/nonogram-reviews/CARD-069/extra-sizes.jpg` — the running admin
with `eagle-silhouette1` carrying three sizes (11×20 fixed, 10×17 short,
17×30 max) and `konek` carrying one. The card's own ratio explains each
extent, which is CARD-067's work paying off here.

### Tests

`tests/test_card_069_size_options.py`, 19 tests. **AC-3 first**, pinned on
`main` at `7de4c85` before any of this existed: one option, one puzzle, the
same extent, no name written. Then per-option fits on a 2.8:1 picture whose
modes genuinely disagree (`fixed 20` moves to Large at 30×11, `short 10` fits
at 28×10 — measured, not derived); a 20:1 picture where every option agrees it
cannot fit; the add/replace/remove rules; two options making two puzzles at
two extents with two names; one size moved while another generates; and the
page's toggles.

**Every pre-existing single-size test passes untouched** — CARD-058, 061, 062,
064, 065 and `test_image_batch_size_fix` were not edited at all, which is a
stronger form of G-3 than the card asked for (it expected them to need
deliberate updating). That is the evidence for G-2.

**Mutation check** — four mutants: the last option becoming un-tickable, a
duplicate mode appending instead of replacing, the loop reverting to one
puzzle per picture, and the names losing their extent. All four caught.

**Full suite: 3,478 passed, 0 failed**, one deselection
(`test_size_configuration_applied`, unrelated).

### Out-of-scope observation

Item 5's last clause — "the generated-puzzles page, where puzzles from one
picture should read as a group" — is **not** done. They are distinguishable by
name and sort together by it, which is enough for AC-7, but there is no
grouping UI. Left out deliberately rather than half-built: it is a
presentation choice the owner should see options for.

