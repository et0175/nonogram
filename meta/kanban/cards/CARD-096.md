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
