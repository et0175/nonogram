# CARD-312: ADR-0042/R6's guard, built from a corrected enumeration — the 321 pixel-reading sites disposed of, and the flip R6 has been owed since October

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-299's implementation round 1, 2026-10-29, which refused item 4 with four measurements the orchestrator verified. Cut on owner decision the same day. Inherits CARD-299's AC-3 verbatim.
**Idea:** —
**Wave:** —
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** CARD-299
**Touches:** tests/test_book_pdf.py, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md, meta/profiling/adr-0042-migration-census.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

ADR-0042/**R6** — *a claim about an interior page's geometry, rule widths or tone is
asserted against the content stream of the written PDF, not against a rendered
bitmap* — has been a `review-lens` since 2026-10-25 and CARD-299 was its delivery
card. **CARD-299 delivered the conversions and refused the flip**, with four
measurements that the orchestrator reproduced:

1. **Two of the six sites R6 enumerates are not interior PDF readings at all.**
   `tests/property/test_book_layout.py:364` and `tests/property/test_book_two_up.py:682`
   both call `getpixel` on a PIL image, and **neither module mentions
   `BookPDFGenerator` even once**. No PDF ⇒ no content stream to assert against.
   Both are COMP-007's drawing surface, which CON-019 puts outside ADR-0042's reach.
2. **The two cited authorities disagree by about 50×.** R6 names **6** sites. Re-deriving
   with `meta/profiling/adr-0042-migration-census.md`'s *own* two regexes reads
   **34 files / 321 sites**.
3. **The census is stale in the damaging direction.** It records 32 files / 315 sites
   at `c12c33ce` (2026-10-25); the same derivation read **34 / 321** four days later.
   **The migration surface grew during the phase that exists to shrink it.**
4. **An idiom count cannot express "the set is empty."** CARD-299's own *correct*
   conversion raised one module's occurrences **8 → 13** while making its assertions
   exact. A guard that ratchets that count **reds on the work it exists to
   encourage.**

So the flip was refused because a guard built from R6's enumeration is built from a
wrong set — the `c12c33ce` defect, a rule reading as mechanically checked by a test
that cannot see its breach. **This card builds the guard R6 actually needs and then
flips it.**

## What to implement

1. **Correct R6's own enumeration first.** The rule names six sites and two are not
   interior PDF readings. Amend R6's statement or its comment so the rule describes
   its real subject, and say in the ADR that two named sites were wrong. **A guard
   derived from an uncorrected rule inherits the error.**
2. **Dispose of the 321 sites, derived not listed.** Re-derive with the census's own
   regexes (so the figure is reproducible), then partition every site: an interior
   PDF reading that must convert · a **COMP-007 drawing-surface** reading that is
   outside the rule (the item-3 class) · an independent **oracle** R6 exempts by name
   · a reading already converted. Per ADR-0039/R2 a site the walk cannot classify is
   a **FAILURE**, never a silent pass.
3. **The discriminator CARD-299 says is decidable — build it.** The round's own
   words: *an `==` against a declared `*_PT` width is reconstruction; a bracket or an
   ordering is a device fact.* `tests/test_book_grid_rules.py` already separates the
   two **by hand** (CARD-227's work), so the hand-made separation is the oracle to
   derive against.
4. **Refresh the census and date it.** It is four days stale and moved the wrong way.
   Record the new figure with the derivation that produced it, so the next card does
   not re-derive a third different number.
5. **Then flip R6** to the guard's node id, and only then. **Spell the ref as a BARE
   NAME** — the node-id form measures as a DEAD check ref on this board (107 → 108),
   while the bare name resolves to the `def` itself.

## Acceptance criteria

- **AC-1** (inherited from CARD-299's AC-3, verbatim): *Given* `tests/**`, *then* the
  guard enumerates interior pixel idioms and the set is empty, with every exemption
  declared and carrying its own control. (test:
  `tests/test_book_pdf.py::test_no_interior_claim_is_made_by_measuring_ink` — the node
  id R6's comment names. **Two mutants**: reintroduce an ink scan on an interior page
  — it reds; and an exemption's control must fail with the exemption removed.)
- **AC-2** (the count is not the measure): *Given* a **correct** conversion that
  raises an idiom count, *then* the guard stays **green** — demonstrated with
  CARD-299's own 8 → 13 case as the control. **This is the AC that stops the guard
  reddening the work it exists to encourage, and it must be shown, not argued.**
- **AC-3** (the enumeration is corrected and the correction is visible): *Given* R6,
  *then* its named sites are all interior PDF readings, and the two that were not are
  recorded as corrected rather than silently dropped.
- **AC-4** (R6's flip is honest): *Given* the ADR, *then* R6's `check:` is a live
  **bare-name** ref whose test exists, collects and passes, **and** the validator
  reports no new warning — warning **sets** diffed with `comm`, never counts
  compared, and the binary named.
- **AC-5** (the census is current and reproducible): *Given*
  `meta/profiling/adr-0042-migration-census.md`, *then* its figure matches a
  re-derivation at the commit it names, and the derivation is recorded beside it.

## Engineering constraints

- **EC:** across `tests/**`, the partition of pixel-reading sites is derived and
  total — every site lands in exactly one class and an unclassifiable one fails —
  with the class counts recorded as count **plus digest** rather than as a list, so a
  site moving is visible without naming every site in tracked code.

## Guardrails

- **G-1: do not convert a COMP-007 drawing-surface reading.** `test_book_layout.py`
  and `test_book_two_up.py`'s probes read PNGs by design; CON-019 and ADR-0042/R7 put
  them outside this rule. Converting them is the error this card exists to stop
  repeating.
- **G-2: do not touch the independent oracles R6 exempts by name**, nor
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` or the A4 golden.
  **Note:** that first name has **no definition** — only docstring mentions at
  `tests/property/test_cli_exports_byte_identity.py:3` and `:157` — so verify the
  tripwire by **running its module**, never by resolving the name.
- **G-3: do not flip R6 until the guard exists and AC-2 is demonstrated.** A flip
  onto a count-ratcheting guard is worse than the lens; that is why this card exists.
- **G-4: no `src/` change.** This is test-side, like CARD-299. The page conversion is
  CARD-309's.
- **G-5: no test deleted, renamed, skipped or merged** — `parametrize` ids included.
  (**gate**: node-id set difference with `-o addopts=''`, both trees.)
- **G-6: a skip-related control attaches its marks by ASSIGNING `pytestmark`, never by
  decorator** — `_conditional_silences` reports a `skipif` whatever it is keyed on,
  and a decorator in a synthetic probe reds the host-state-silence guard tree-wide.
  Verify `_conditional_silences(<your source>) == []`.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R6 — an interior claim is asserted against the content stream (check: review-lens → **this card's AC-1 flips it**)
- ADR-0042/R7 — the scope statement that keeps COMP-007's surface out (check: review-lens)
- CON-019 — book geometry never changes the CLI's or web UI's exports, byte-for-byte (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
- ADR-0039/R1-R2 — a claim needs a control that CAN fail; a guard's set is derived and an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0006/R1 — the dependency baseline (check: **DEAD REF** — verify the substance; see CARD-307)

## Architecture context

- **FR:** FR-033, FR-043, FR-030
- **ADR:** **ADR-0042/R6** (this card is its delivery), ADR-0042/R7, ADR-0039/R1-R2
- **Components:** none in `src/` — the test tree and the ADR
- **Trace:** `trace.yml` holds **no ADR-0042 rule rows at all** (measured 2026-10-29: prose only, at `:1813` and `:1853`), so no rule row is re-stamped. Do not write a Trace line promising one — the mistake CARD-298 inherited.

## Worktree notes

- **CARD-299 is the dependency and the reason.** Read its round-1 record before
  starting: it holds the four measurements, the medium-gating pattern every converted
  reading now uses, and the proof that a stream-read assertion is **vacuous** while
  all seven page kinds are raster.
- **This card can land before any page converts**, like CARD-299, because it is a
  guard over `tests/**` rather than a reading of a vector page.
