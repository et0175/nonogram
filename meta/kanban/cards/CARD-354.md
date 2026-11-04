# CARD-354: `tests/test_book_solved_answer_key.py` — 33 reds, the largest single module of the conversion residue

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2c (1d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Module-sliced out of CARD-337 at the decompose station, 2026-11-04, on the owner's "module slicing" instruction. CARD-337's own item 0 refuted its premise three ways and its round then derived the mechanism x module cross-tab; that table reconciles to 143 reds in both directions. The axis was changed from mechanism to MODULE because the round measured that a mechanism-sliced partition cannot run concurrently at all -- nine of thirteen modules split across mechanisms, `tests/test_book_pdf_band.py` would have needed five separate cards to edit it, and nothing could have run beside the M10 card. The file axis is the one the scope gate enforces.
**Idea:** —
**Wave:** —
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_solved_answer_key.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The population, from CARD-337's cross-tab

**33 reds under the five-kind probe — the largest of the thirteen modules**, and this card owns
all of them. Nothing routes out.

| mechanism | reds | the line the gate prints |
|---|---|---|
| **M10** medium-blind empty read | **21** | no single signature — `assert []` / `assert set()` / `IndexError: index 0 is out of bounds for axis 0 with size 0` / `assert False` / `printed no …` |
| **M7d** in-module `ContentStream` read | **12** | `AttributeError: 'ContentStream' object has no attribute {'width'\|'tobytes'\|'crop'\|'convert'}` |

**M10 is a residual, not a mechanism, and that is this card's main risk.** Board-wide it is 57
reds across **35 distinct cause lines** and 8 modules, held together by a catch-rule matching
sixteen alternations and positioned last-but-one in the taxonomy. Every other mechanism has
1–7 signatures. **So "21 M10 reds" is 21 reds that did not match a more specific rule** — the
"other" bucket ADR-0039/R2 forbids, arriving with a label.

**Item 0: re-split your 21 M10 reds by cause signature before pricing or implementing.** If
they are three mechanisms wearing one label, say so and expect a re-cut; if they genuinely share
a cause, name it. This card's estimate assumes the latter and the assumption is **unmeasured**.

## What to implement

1. **Re-split M10** (above). Report the signature histogram.
2. **The 12 M7d reds** are a module-local reader meeting a content stream where it expected an
   image. The repair is per-site and the question for each is the ADR-0042/R6 one: re-express
   against the stream, or retire with a named survivor. **Say which, per site, with the reason.**
3. **Where a claim has no subject in the converted medium, retire it with a named survivor** —
   do not weaken it into something that passes vacuously. CARD-337 is the worked example of a
   claim with no vector subject.

## Acceptance criteria

- **AC-1** *Given* the five-kind probe, *then* this module's red count is **stated before and
  after**, derived by the committed census, and every remaining red is either routed with an
  owner or carries a stated ADR-0042/R6 disposition.
  (test: named by the implementation; state it)
- **AC-2** *Given* the 21 M10 reds, *then* their cause-signature histogram is **reported**, and
  if it shows more than one mechanism that is a finding, not a detail.
  (check: review-lens)
- **AC-3** *Given* each repaired site, *then* a plant re-breaks it and the matched control is
  green **in the same run**, with `0 skipped` asserted — and because many of these are
  fixture-raised, state how many node ids each plant moves.
  (test: named by the implementation; state it)
- **AC-4** *Given* a claim retired rather than re-expressed, *then* the survivor is **named** and
  the retirement is asserted, not merely commented (ADR-0039/R1).
  (check: review-lens)

## How to measure, and the instrument is not yours to build

**Re-derive your own population before implementing anything.** The instruments are committed:

- `scratchpad/card338/census_five_kinds.py` — the driver (drives `probe_five_kinds.py`). **Run
  it, do not rebuild it.** CARD-338 owns, committed and refusal-proved it.
- `scratchpad/card338/classify_reds.py` — the mechanism taxonomy.
- `scratchpad/card337/cross_tab.py` — the mechanism × module table. It **imports** `RULES` /
  `classify` from `classify_reds.py` rather than restating the taxonomy; keep that property if
  you extend it.

**Two hazards in those instruments, both measured:**

1. **`classify_reds.py` is NOT filter-agnostic.** Faithful on the five-kind dump (143/143, exit
   0, no "other" group). On a `PUZZLE`-only dump of the same thirteen modules it leaves **13 of
   78 unclassified and exits 1** — loud, but only if you read the exit code. **Scope nothing
   from a `PUZZLE`-only reading.**
2. **A mechanism census of the UNPLANTED tree is not the census after a repair.** Measured:
   `pdf_band` shows **zero** byte-identity reds unplanted, and **three** among the survivors
   once the `interior_images` seam is planted. So your post-repair survivors may carry
   mechanisms your pre-repair census does not list. Re-census after your repair, not only
   before.

**And `-rfs` omits ERRORs — use `-rEfs`.** That matters more here than usual: **21 of the 40
M7d reds board-wide print as `ERROR at setup`**, fixture-raised, so one repair flips many node
ids at once and one plant can re-break many. Clear `addopts = "-q"` with `-o addopts=` as **two
argv items**. The worktree has no `.venv` — use
`/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python`.

## Guardrails

- **G-1** — **No `src/` change.** Every product-behaviour red in this module family is routed to
  **CARD-322** (M1 delitem, M2 expected-side gap, M3 `Image`-arrived-as-vector, M3b the cp1252
  title refusal). If your measurement indicts the generator, that is a **finding and a routing**,
  not an edit.
- **G-2** — **Do not widen a bound or a tolerance to make a cell pass.** `EDGE_TOLERANCE_MM`,
  `EDGE_TOLERANCE_PX` and `HALF_PIXEL_MM` are not yours to move.
- **G-3** — **Stay inside your `Touches`.** The module partition is what makes these cards
  concurrently runnable; a card that reaches into a sibling's module destroys that property.
  Planting a mutant into another module and restoring it byte-identically is a measurement and
  is allowed — the SHA-256 pair is the proof — but leaving an edit there is the violation.
- **G-4** — No new runtime dependency (ADR-0006/R1): stdlib + Pillow + NumPy is closed.
- **G-5** — Take no timing measurements and report no durations; other work shares the machine.
- **G-6** — A full suite needs the board's lock (`meta/kanban/.full-suite.lock`, structured,
  identity is the **worktree**, no pid). **Never** set `NONOGRAM_IGNORE_FULL_SUITE_LOCK` and
  never redirect `NONOGRAM_FULL_SUITE_LOCK` — the guard fires in `pytest_configure` for **any**
  selection, so a redirect blinds a file-scoped run to a gate that *is* holding it.
- **G-7** — **G-8 standing: do not connect to the production database.** `conftest.py` refuses
  by URL text before connecting; do not widen or bypass `_refuse_unless_test_database`.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate; where none
  exists it defaults to **deny** (check: review-lens)
- ADR-0039/R4 — a figure recomputed and refuted is retracted everywhere it was written
  (check: review-lens)
- ADR-0042/R1 — interior pages are operators (check: review-lens)
- ADR-0042/R6 — a claim that has no subject in the converted medium is re-expressed against the
  content stream or retired with a named survivor (check: review-lens)
