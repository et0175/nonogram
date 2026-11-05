# CARD-360: `pdf_levels` and `pdf_two_up` — 6 reds in the two modules where the seam is already present

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
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
**Touches:** tests/test_book_pdf_levels.py, tests/test_book_pdf_two_up.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

> **⚠ UNVERIFIED FIGURES, 2026-11-05.** This card quotes **57 M10 reds / 35 cause lines**. They are CARD-337's round's roll-up and **three readers have now tried and failed to verify them** (CARD-358's round, its review, and the orchestrator). The review's census aborted on its own gate at 14 of 20 modules — *the instrument working*, a zero-collect most plausibly caused by a foreign lock appearing mid-run, since the guard refuses in `pytest_configure`. **And one component has already moved:** CARD-356's module measures 26 reds, not its stated 25. **Do not quote the roll-up as fact; re-derive your own module's count at the start**, which is what scopes your card anyway.

## The population, from CARD-337's cross-tab

**8 reds under the five-kind probe; this card owns 6.** The other 2 are **M8** (placed-edge,
`assert 0.2313… <= (0.0423… + 1e-09)`) in `pdf_two_up`, and they are **CARD-352's** — CARD-336
closed, so they were re-routed there.

| module | mechanism | reds | owner |
|---|---|---|---|
| `tests/test_book_pdf_levels.py` | M10 medium-blind empty read | 2 | this card |
| | M9 byte identity | 2 | this card |
| `tests/test_book_pdf_two_up.py` | M10 medium-blind empty read | 2 | this card |
| | **M8 placed-edge** | **2** | **CARD-352** |

## Why these two modules are grouped, and it is a measured property

**They are the only two modules of the thirteen where the `interior_images` seam is ALREADY
present** — class S0 in CARD-337's seam derivation. So whatever their reds are, they are **not**
a missing seam, and that rules out the whole family of repair the original CARD-337 was built
around. Their mechanisms are what is left when the seam is not the answer.

**M9 byte identity is the interesting half.** Its signatures:

```
AssertionError: assert b'\xff…' == b'\xff…'
interior page N is not the page it was
stored page N is …
```

**A byte comparison across a medium change is a claim about determinism, not about pixels.** Two
renderings of the same page as operators can be byte-identical; a raster rendering and an
operator rendering cannot. **So the question is what identity means once a page is a stream** —
and whether the claim was ever about bytes or about "the same page came back".

**Byte identity also appears in `pdf_band` AFTER its seam is planted** (3 cells, where the
unplanted census shows zero), which is why CARD-337's old AC-2 enumeration of this family was
incomplete. **If you settle what identity means here, say what it implies for those three.**

**M10 warning:** board-wide M10 is 57 reds across 35 cause lines — a residual, not a mechanism.
Re-split your 4 before trusting the label.

## What to implement

1. **Settle what byte identity means for an operator page**, and state it. That is the card's
   substance; the M10 reds are probably cheaper.
2. **Re-split the 4 M10 reds** across the two modules and report the histogram.
3. Repair or disposition each per ADR-0042/R6, stating re-expression or retirement-with-survivor.
4. **Say what your identity answer implies for `pdf_band`'s three post-seam byte-identity
   cells** — a statement for CARD-356, not a fix here.

## Acceptance criteria

- **AC-1** *Given* the M9 reds, *then* the card states what identity means for a page written as
  operators, and the claim is **asserted** in that form rather than commented.
  (test: named by the implementation; state it)
- **AC-2** *Given* the five-kind probe, *then* both modules' red counts are stated before and
  after, and `pdf_two_up`'s 2 M8 reds are **still present and attributed to CARD-352**.
  (test: named by the implementation; state it)
- **AC-3** *Given* the 4 M10 reds, *then* their cause-signature histogram is reported.
  (check: review-lens)
- **AC-4** *Given* each repair, *then* a plant re-breaks it with its matched control green in the
  same run and `0 skipped`.
  (test: named by the implementation; state it)
- **AC-5** *Given* CARD-356's three post-seam byte-identity cells, *then* this card states what
  its identity answer implies for them — a routing statement, not a repair.
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
