# CARD-061: MIN_SIZE floor forces small (N=10) puzzles square, discarding picture content

**Status:** ready
**Priority:** P2
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** medium
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/061-min-size-floor-vs-smallest-n
**Worktree:** —
**Source:** project owner, 2026-09-11, while visually testing CARD-058 on real pictures ("picture preview depends on the selected puzzle size ... small size — it's trimmed and not squeezed"; later: "main difficulty in generation of small (10*10) puzzles — they mostly look bad")
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/sourcing/random_grid.py, meta/architecture/decisions/adr/0022-grid-extent-and-size-range.md, src/nonogram/admin/app.py (the `size_mapping` preset table), tests pinning `derive_extent`/`_derived_extent`
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** — (a design decision, see "Decide first" — not an external blocker)

## What to implement

**Documented for now, deliberately not implemented.** The owner asked for this
to be recorded, not fixed, on 2026-09-11. It touches shared `sourcing/`
arithmetic the CLI relies on and would revise ADR-0022/R4, so it must not be
picked up as a side effect of an admin-UI card — it is its own decision.

### The finding

ADR-0022/R4 (`meta/architecture/decisions/adr/0022-grid-extent-and-size-range.md:121-151`)
says a bare `--size N` is the grid's **longer** side and the shorter side is
`round(N * short/long)` of the source's own ratio, floored at `MIN_SIZE`. The
arithmetic is `_derived_extent` in `src/nonogram/sourcing/random_grid.py:218`:

```python
derived = max(MIN_SIZE, round(stated * shorter_edge / longer_edge))
```

`MIN_SIZE` is 10 (`random_grid.py:79`) and, since CARD-023 narrowed the range
project-wide, 10 is **also the smallest allowed `N`**. Those two roles collide
at the bottom of the range: at `N = 10` the derived side is `max(10, ≤10)`,
which is 10 for *every* source. So the smallest puzzle is **forced square
regardless of the picture's shape** — the source-tracking that ADR-0022 exists
to provide is switched off precisely at N=10, and the grid silently crops the
picture instead (the "trimmed, not squeezed" the owner saw). Nothing raises:
this is the *floor* path succeeding, not the `SizeTooSmallForSource` *refusal*
path, so CARD-058's substitution note does not (and cannot) cover it.

The effect fades quickly as N grows, because the floor only bites when
`round(N * short/long) < 10`:

| N | source ratios that still track exactly | content retained for c11 (1.54:1) |
|---|---|---|
| 10 | none — every non-square source is forced to 10x10 | 65% (10x10) |
| 12 | up to 1.2:1 | 78% (12x10) |
| 15 | up to 1.5:1 | ~98% (15x10) |
| 20 | up to 2:1 | ~100% (20x13) |

Verified on a real picture from the owner's corpus:
`~/MyProjects/books/nonograms/images/christmas/balls/c11.jpg`, ink bounding
box 229x149 (1.537:1). The "small" preset (`admin/app.py:217`, `"small": (10,
"fixed")`) gives a forced 10x10 keeping 65% of the picture; "medium" (N=20)
gives 20x13 and keeps essentially all of it — which is exactly the difference
the owner observed between the two presets.

ADR-0022 already states the *refusal* consequence of the floor plainly ("asking
for a smaller puzzle refuses pictures a larger one would accept", lines
146-151) but does **not** state this *success-path* consequence — that at the
minimum N the shape rule degenerates to a square and crops. It should, whatever
is decided below.

### Two things are tangled in "10x10 puzzles look bad" — keep them apart

1. **The floor collision above** — a real, fixable shape defect: the picture is
   cropped to a square when it should not be.
2. **Resolution** — 100 cells is very little for a recognizable picture no
   matter how it is cropped. A 10x10 of a picture that *is* square will still
   look coarse. This card is about (1); fixing (1) will not make (2) go away, and
   the follow-up investigation should measure both separately (e.g. compare the
   owner's "bad" 10x10s against the same pictures at 15x10 / 20x13 to see how
   much of the badness is shape vs. cell count).

### Decide first (owner's call, not the implementer's)

Options, cheapest first. They are not mutually exclusive — A + C is a
plausible combination.

- **A. Accept and document.** Keep `MIN_SIZE = 10` as both floor and smallest
  N; record the square-at-N=10 consequence in ADR-0022 (a History entry plus
  one sentence next to the refusal consequence), so it stops being a surprise.
  Zero code risk. Does nothing for the puzzles themselves.
- **B. Retarget admin's "small" preset.** `batch_create.html:59` already
  labels it "Small (10-15 cells)"; changing `"small": (10, "fixed")` to 15
  (or `min` mode with 15) keeps sources up to 1.5:1 tracking exactly and
  accepts up to 3:1. Admin-only, no ADR change, no CLI impact — the CLI user
  who types `--size 10` still gets today's behaviour. Likely the largest
  practical win for the owner's workflow at the smallest cost.
- **C. Warn when the floor forced a square.** CARD-058's pattern applied to the
  success path: when `derived == MIN_SIZE` *and* the unfloored value was below
  it, surface a note ("shape floored to 10 — N cells or more would keep this
  picture's proportions"). Admin-UI-only, but needs `sourcing/` to expose the
  fact (a second return value or a sibling helper alongside `derive_extent`),
  so `Touches` grows to `random_grid.py` — still no behaviour change.
- **D. Decouple the floor from the smallest N.** Let the derived short side go
  below 10 (say floor 5) so a 10x7 is possible. This is the only option that
  fixes N=10 itself, and it is the expensive one: it revises ADR-0022/R4 *and*
  CARD-023's project-wide 10..30 range (`validate_size` at `random_grid.py:105`
  refuses any side under 10; export layouts, the measured 30x30 deadline
  fixture, the property corpora and the web/admin size validators all assume
  ≥10 per side), and it changes the N/5 : 1 refusal ceiling that
  `_smallest_workable_size` (`random_grid.py:224`) derives from the same floor.
  Needs a forge:architect-adr-writer pass before any code.

Recommendation to start the discussion, not a decision: **A + B now** (cheap,
targets the owner's actual workflow), **C** if the owner still hits the case
through explicit sizes, **D** only if 10-wide puzzles with a non-square shape
are a real product requirement — in which case it becomes a wave-scoped
decision card, not a fix.

1. Owner picks option(s) above; record the choice in this card and, for
   anything touching R4's statement, in ADR-0022 via forge:architect-adr-writer.
2. Only then implement, on a branch from this card, with `Touches` narrowed to
   the chosen option.
3. Whatever is chosen, add the missing success-path sentence to ADR-0022 (the
   floor at N=10 yields a square and crops) — that part is unconditional.

## Acceptance criteria

- **AC-1** — given this card is picked up, when work starts, then the chosen
  option (A/B/C/D or a combination) is recorded in this card *before* any
  `sourcing/` or ADR edit lands, and any change to R4's statement goes
  through an ADR revision, not a code-only edit.
- **AC-2** — given `c11.jpg` (or an equivalent ~1.5:1 fixture committed under
  `tests/`) at the admin "small" preset, when the batch preview renders, then
  the outcome the chosen option promises is observable: either the note (C),
  a non-square grid (B via N=15, or D), or — for A alone — nothing changes and
  ADR-0022 now names the consequence.
- **AC-3** — ADR-0022 states, next to its existing refusal consequence, that at
  the minimum N the derived side is forced to `MIN_SIZE` and the grid stops
  following the source's shape (unconditional, all options).
- **AC-4** — `tests/property/test_solver_uniqueness.py` and the tests pinning
  `derive_extent` still pass; for option D specifically, the `_derived_extent`
  tie-to-even property test and the `SizeTooSmallForSource` refusal-message
  tests are updated deliberately, not weakened, and the new floor is pinned by
  a test that fails against `MIN_SIZE`-floored code.

## Guardrails

- G-1: No silent top clamp, ever — `_derived_extent`'s "longer side is exactly
  `stated`" property (ADR-0022/R4, `random_grid.py:199-203`) is untouched by
  every option.
- G-2: Do not change the CLI's refuse-with-message behaviour on
  `SizeTooSmallForSource` as a side effect; if option D moves the ceiling, the
  message's "smallest workable N" must still be computed by
  `_smallest_workable_size` from the *same* helpers, not hand-derived.
- G-3: Options A/B/C must not touch `MIN_SIZE`, `validate_size`, or any test
  under `tests/property/` — those belong to option D and its ADR revision only.
- G-4: Keep the two causes separate in any write-up: do not claim the floor fix
  makes 10x10 puzzles "look good" without a side-by-side against the same
  pictures at a larger N.
