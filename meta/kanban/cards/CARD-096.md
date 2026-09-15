# CARD-096: Image-mode abandonment is measured and sorted by cause, so CARD-075 and CARD-079 have a baseline to beat

**Status:** in progress
**Priority:** P2
**Category:** enabler (measurement; no production code changes)
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/096-image-abandonment-baseline
**Worktree:** ../PythonProject4-CARD-096
**Source:** owner — "open a card for the image mode abandonment" (CARD-095 out-of-scope observation)
**Idea:** —
**Wave:** 1
**Depends on:** CARD-095 (merged) — whose probe surfaced the rate
**Relates to:** **CARD-075** (ready since 2026-09-12, never started — mask-driven nudge) and **CARD-079** (ready, never started — threshold binarisation behind a switch, owner-gated on rendered grids)
**Touches:** meta/ops/image_abandonment_sweep.py (new), meta/ops/image_abandonment_contact_sheet.py (new), this card
**Review score:** —
**Started:** 2026-09-15
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

About a quarter to a third of the owner's own pictures cannot be made into a
puzzle. That is the single largest gap left in the product: the random path
succeeds 99% of the time at 30x30 since CARD-091.

**The fixes already exist as cards.** CARD-075 replaces the nudge's 2x2
"switching block" guess with the solver's own map of where the ambiguity is.
CARD-079 converts silhouettes with a threshold instead of Floyd–Steinberg
dithering, whose ragged one-cell edges are the classic cause of a non-unique
nonogram. Both were written on 2026-09-12 and neither has started. This card
does **not** add a third fix. It supplies what both lack: a measured **before**,
split by cause, so the owner can see which of the two addresses which failures —
and so neither is judged against a guess. CARD-079's AC-127 measures only *after*
CARD-075; nothing measures before either.

## Measured while scoping

All 25 pictures in `pictures/`, `orchestrator.generate` in image mode at bare
sizes 10, 15, 20, 25 and 30 (125 conversions), on `main` at `45c8a94`.

| size | made | abandoned | timed out |
|---:|---:|---:|---:|
| 10 | 19 | **6** | 0 |
| 15 | 21 | **4** | 0 |
| 20 | 17 | **8** | 0 |
| 25 | 16 | **8** | 1 |
| 30 | 16 | **8** | 1 |

**The nudge rarely rescues.** Of the 125 conversions, 76 were unique first time
and needed no nudge. Of the 47 that were *not* unique and had a nudge to try,
the five-cell nudge rescued **13 (28%)**, using 1–4 cells, and 34 were abandoned.
(The other 2 timed out.)

**The admin's neighbour retry rescues a little more.** For every abandonment at
20 and at 30, the admin's CARD-062 retry at long side −1 and +1:

| size | abandoned | rescued by a neighbour | still lost |
|---:|---:|---:|---:|
| 20 | 8 | 3 | **5 of 25 (20%)** |
| 30 | 8 | 2 | **6 of 25 (24%)**, plus `butterfly.png` timing out |

**Per picture** (M = made, with nudges used; a = abandoned; T = timed out):

```
                         10  15  20  25  30
butterfly.png            a   a   a   T   T     fails at every size
cat_Mouse.png            a   a   a   a   a     fails at every size
dear.png                 a   a   a   a   a     fails at every size
zebra.png                M2  M4  M0  a   a     fails at the large sizes
cat_dog.png              M0  M1  M0  a   a
duck2.png                M0  M0  M0  a   a
frog1.jpeg               M0  M0  a   a   a
dear1.jpg                M0  a   a   a   M0    not monotone in size
eagle-silhouette1.jpg    a   M0  a   a   M1    not monotone in size
... 11 pictures made at every size, 9 of them with no nudge at all
```

### Two populations, which is why both cards may be needed

The size of the solver's undecided mask on the failing candidates splits the
abandonments roughly in two:

- **Small residual ambiguity** — a handful of cells (4–26): `butterfly1` at 10,
  `eagle-silhouette1` at 10/20/25, `img_6` at 10, `duck2` at 25, `wolf_2` at 30.
  A few well-chosen flips could plausibly resolve these; the nudge's current
  ranking is not choosing them. **CARD-075's territory.**
- **Widespread ambiguity** — hundreds of cells (146–738): `cat_Mouse`, `dear`,
  `zebra` at 25/30, `cat_dog` at 25/30, `wolf_face` at 30. No five single-cell
  flips fix hundreds of ambiguous cells; the conversion itself is producing an
  ambiguous picture. **CARD-079's territory**, if thresholding reduces it — and
  possibly neither, for busy multi-subject pictures.

**This split is a hypothesis, not a finding yet**, for a reason AC-1 fixes: the
probe recorded the mask of the *last candidate judged* — for an abandoned picture,
the fifth nudge — not of the original conversion. The nudges could have enlarged
or shrunk it.

## Acceptance criteria

- **AC-1** (a committed, reproducible sweep) — `meta/ops/image_abandonment_sweep.py`
  runs every picture in `pictures/` at a chosen list of sizes and records, per
  conversion: outcome, extent, nudges used, and the **original conversion's**
  undecided-mask size and witness-disagreement size (captured at the first judge,
  not the last), plus fill ratio and elapsed time. Output is a table and a JSON
  file, so CARD-075 and CARD-079 re-run the same command for their *after*.
- **AC-2** (what the owner sees, not only what `generate` sees) — the sweep also
  runs each picture the way the admin batch does, at the size presets
  (`small`, `medium`, `large`, `auto`) through the fit policy and
  `admin.app._generate_image_puzzle`'s neighbour retries, and reports the
  admin-level loss rate per preset.
- **AC-3** (every failure has a cause) — each abandoned (picture, size) is
  classified from the original conversion: **small residual** (mask under a
  stated threshold), **widespread** (above it), **timeout**, with the threshold
  chosen from the measured distribution and written down. A picture that fails at
  every size is flagged separately.
- **AC-4** (the owner can look at it) — `meta/ops/image_abandonment_contact_sheet.py`
  renders one sheet per failing picture: the source picture, the converted grid at
  each failing size, and the undecided cells marked on it. Saved outside the repo
  and put in front of the owner; nothing rendered is committed.
- **AC-5** (a recommendation the owner decides on) — the card closes with: how
  many failures fall to each cause at each size and preset; which card addresses
  which population and in what order; and whether CARD-075's text needs updating
  before it starts — it was written before CARD-074's repair, CARD-090's bound and
  CARD-091's K, and before this measurement existed.

## Guardrails

- **G-1** — no production code changes. Nothing under `src/` or `tests/` moves;
  the sweep and the renderer live in `meta/ops/`, as `retry_bound_sweep.py` does.
- **G-2** — `pictures/` and `pic1/` are the owner's; read only, never restructured
  or added to.
- **G-3** — CARD-075 and CARD-079 are not started, merged into this card or
  rewritten here. AC-5 may *recommend* edits to them; the owner makes them.
- **G-4** — the machine runs nothing else while the sweep times conversions
  (CARD-090's lesson); outcome counts do not depend on load, but the timeout does.
- **G-5** — `nonogram_admin.db`, `src/nonogram.egg-info/*` and the stray PDFs stay
  uncommitted; commit with explicit pathspecs only.

## Open questions for the owner

None before starting — the decisions this card exists to inform come at AC-5.

## Outcome

Run on `main` at `45c8a94`, machine otherwise idle:
`PYTHONPATH=src python meta/ops/image_abandonment_sweep.py` (all 25 pictures, sizes
10/15/20/25/30, presets small/medium/large/auto).

### AC-1 / AC-3 — the engine, with the original conversion's ambiguity

| size | made | first try | after nudges | abandoned | timed out | small residual | widespread |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 19 | 16 | 3 | 6 | 0 | 4 | 2 |
| 15 | 21 | 14 | 7 | 4 | 0 | 0 | 4 |
| 20 | 17 | 16 | 1 | 8 | 0 | 2 | 6 |
| 25 | 16 | 15 | 1 | 8 | 1 | 3 | 5 |
| 30 | 16 | 15 | 1 | 8 | 1 | 2 | 6 |

Fails at every size: `butterfly.png`, `cat_Mouse.png`, `dear.png`.

**The threshold is a share, and the data drew it.** The grids run from 100 to 900
cells, so the count of undecided cells is not comparable across sizes; the share
is. Sorted, the 34 abandonments' undecided shares are
`1.8 2.0 2.1 3.5 4.0 4.0 4.0 4.0 4.8 5.4 8.0 | 22.5 29.3 … 100.0` — nothing
between 8.0% and 22.5%. Small residual is set at **≤ 15% of the grid**: 11
abandonments, 23 widespread.

**The finding the scoping probe could not see.** The scoping numbers were read
off the *last* nudge's candidate. On the original conversion, the cells the
solver's two witnesses actually disagree on are **4 in 27 of the 34
abandonments** — one 2x2 block that can be drawn either way — and never more
than 24, even where line logic leaves 97% of the grid undecided. The undecided
share measures how hard the picture is for line logic; the disagreement measures
how far it is from unique. Nearly every abandoned picture is **one ambiguous
block away** from a puzzle, and today's nudge ranking is not finding the block.

### AC-2 — what the owner sees in the admin

| preset | made at its size | made at a neighbour | abandoned | timed out | lost |
|---|---:|---:|---:|---:|---:|
| small | 19 | 3 | 3 | 0 | **3 / 25** |
| medium | 17 | 3 | 5 | 0 | **5 / 25** |
| large | 16 | 2 | 6 | 1 | **7 / 25** |
| auto | 16 | 2 | 6 | 1 | **7 / 25** |

The columns are exclusive and sum to 25. "Made at a neighbour" is what CARD-062's
retry recovered after the preset's own extent was abandoned.

### AC-4 — the contact sheets

14 sheets, one per picture that failed at some size, rendered to
`/Users/omelnikova/PycharmProjects/CARD-096-contact-sheets/` (outside the repo,
not committed). Each shows the source, then the original conversion at each
failing size with undecided cells tinted. What looking at them adds, which no
number above says:

- **Most widespread failures are dark-grey silhouettes, not busy pictures.**
  `dear1` (a fawn) and `wolf_face` are drawn in dark grey rather than black;
  Floyd–Steinberg dithers the grey into a black/white checkerboard, and the
  silhouette dissolves into exactly the scattered cells a nonogram cannot pin
  down. `dear` is a clean black silhouette carrying a grey **"Pikbest"
  watermark** — the dithered watermark *is* its widespread ambiguity.
  `cat_dog` and `frog1` speckle along thin parts. All of this is CARD-079's
  stated mechanism, visible.
- **Three pictures are outside image mode's calibrated scope** (CON-013:
  high-contrast silhouettes): `cat_Mouse` is line art (a colouring page),
  `butterfly` is intricate line work, `zebra` is a photograph with a fake
  transparency checkerboard baked in.
- **Fidelity, not only reachability, is poor on the failures.** At 16x20
  `wolf_face` is unrecognisable. Whether *made* puzzles look this way too was
  not in scope and was not checked.

### Experiments — what each card would buy (scratch, not committed)

Neither card's code. Three scratch scripts over the 36 dither failures (34
abandonments and 2 timeouts), recorded here so the numbers can be challenged:

1. **Flip inside the witness disagreement** — solve; while not unique and fewer
   than 5 flips, flip the first cell (row-major) where the two witnesses differ;
   cumulative, like the nudge. **19 of 34 abandonments become unique**, 7 with one
   flip; 10 of the 11 small-residual failures. Today's nudge rescued 0 of these.
2. **50% threshold instead of dithering** — `sourcing.image.binarize` swapped for
   the same LANCZOS resize followed by a plain threshold at 128, through the real
   `orchestrator.generate` with today's nudge. **19 of 36 made** — a different 19:
   all five `cat_Mouse` sizes, every `eagle-silhouette1` size, `dear1` at 20/25.
3. **Both** — threshold conversion, then disagreement flips. **32 of 36 unique.**
   Still lost: `butterfly` at 10 and 30, `dear` at 20 and 25. Every failure
   either experiment rescued alone, the combination rescues too.

**What the experiments do not show, and why they are not a decision:**

- **Regressions — measured afterwards, see *Follow-up measurement* below.** The
  first three experiments ran only on pictures dithering fails; whether a
  threshold breaks any of the 89 conversions dither makes today was checked
  separately, and it breaks none.
- **Fidelity.** "Unique" is not "recognisable". `cat_Mouse` made at every size
  from line art may be dots. This is CARD-079's owner gate, and it is binding.
- **The flip rule** is the crudest one (first differing cell). CARD-075's own
  ranking may do better or worse; its cap of 5 was respected.
- **No admin retry** was layered on top, so the admin-level gain is unknown.

### AC-5 — recommendation (the owner decides)

1. **Take CARD-075 first.** It is the safe lever: the nudge only runs on a
   conversion that is *not* unique, so it cannot change a puzzle that is made
   today, and experiment 1 says it could recover roughly half of the
   abandonments within the existing 5-cell cap.
2. **But revise CARD-075 before it starts** — done at the owner's word, on this
   card's branch. Two changes, both from the data: take cells from the
   **witness-disagreement set** first and the undecided mask only as a fallback
   (the disagreement is 4 cells where the mask is a median 35% of the grid); and
   choose each attempt's new cell from the **previous attempt's** verdict rather
   than all n up front from the original (19 against 9, *Follow-up measurement*),
   keeping attempt n nested and exactly n cells from the picture.
3. **Then CARD-079, as it is written** — owner-gated on side-by-side renders of
   every corpus picture. Experiments 2 and 3 say it is the bigger lever (with
   flips, 32 of 36), and the contact sheets show why: dithered dark-grey
   silhouettes and watermarks. Its AC-127 must now also count **regressions on
   pictures dither already makes**, which its current text does not ask for.
4. **Say plainly what image mode is not for.** Line art, intricate line work and
   photographs fail and will keep failing, and the owner's corpus contains all
   three. Whether the admin should warn on upload (CON-013 already scopes image
   mode to silhouettes) is a product question, not a fix.

- **G-1..G-5 held.** Nothing under `src/` or `tests/` changed; `pictures/` was
  read only — a stray symlink my own `ln` created inside the worktree's copy was
  removed at once and never committed; CARD-075 and CARD-079 are untouched.

### Follow-up measurement, taken while revising CARD-075 (owner: "revise CARD-075")

Experiment 1 re-solved after every flip and took the *new* disagreement, and did
not stop a later flip undoing an earlier one. CARD-075 as written is neither: it
flips the best n cells of the **original** conversion, chosen once. Both
variants were re-measured with FR-013's policy half enforced — attempt n differs
from the original conversion in exactly n cells and contains every cell attempt
n−1 flipped — cap 5, on the 36 dither failures:

| nudge variant | dither | threshold |
|---|---:|---:|
| **static** — first n cells of the original conversion's disagreement set, mask fallback | 9 | 23 |
| **adaptive** — attempt n−1's cells plus one new cell from attempt n−1's own disagreement set, mask fallback | **19** | **32** |

- **The nesting guarantee costs nothing:** adaptive with it is 19, the same as
  the unconstrained experiment.
- **Choosing cells once, from the original, loses half the gain** (9 against 19).
  Flipping one cell of a 2x2 ambiguity usually exposes the *next* one somewhere
  the original disagreement set never contained.
- **Regressions:** threshold conversion with adaptive nudges still makes **all 89**
  conversions dither makes today.

This is what CARD-075's revision is built on.

