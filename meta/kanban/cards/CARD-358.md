# CARD-358: `tests/test_book_interior_type_floor.py` — 7 reds, all M10, in the module that sat in neither of CARD-329's populations

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/358-interior-type-floor-m10`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-358
**Source:** Module-sliced out of CARD-337 at the decompose station, 2026-11-04, on the owner's "module slicing" instruction. CARD-337's own item 0 refuted its premise three ways and its round then derived the mechanism x module cross-tab; that table reconciles to 143 reds in both directions. The axis was changed from mechanism to MODULE because the round measured that a mechanism-sliced partition cannot run concurrently at all -- nine of thirteen modules split across mechanisms, `tests/test_book_pdf_band.py` would have needed five separate cards to edit it, and nothing could have run beside the M10 card. The file axis is the one the scope gate enforces.
**Idea:** —
**Wave:** 79 <!-- DISPATCHED 2026-11-05T06:23Z as wave 79's vector-slice card. Premise VERIFIED under the five-kind probe: 8 failed / 43 passed, 7 M10 (this card) + 1 M1 (CARD-322). First step of the ADR-0042 slice the owner reopened after eleven days. Cut off the stamping commit so it cannot un-stamp its own Wave. -->
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_interior_type_floor.py
**Review score:** —
**Started:** 2026-11-05T06:23Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The population, from CARD-337's cross-tab

> **✓ PREMISE VERIFIED AT THE STATION, 2026-11-05 — it reproduces EXACTLY.** Run under this card's
> own stated condition, the five-kind probe (`pytest -p scratchpad.card338.probe_five_kinds`, the
> instrument CARD-338 landed): **8 failed / 43 passed**. Classified by re-running each failing node
> and reading its cause: **7 are M10 (this card's)** and **1 is M1 (CARD-322's)** — the
> `monkeypatch.py` `KeyError: <PageKind.TITLE: 'title'>` delitem site, on
> `test_lifting_a_declaration_makes_the_stream_arm_read_that_page`. The 8 = 7 + 1 split is exactly
> what the card claims.
>
> **Note for the round, because it will mislead you otherwise:** on `main` *without* the probe this
> module is **51 passed, 0 failed**. The reds are a property of the converted end state, not of the
> tree — so a bare `pytest tests/test_book_interior_type_floor.py` will tell you nothing and look
> like a refuted premise. The orchestrator made that mistake first and checked the condition before
> announcing it.

**8 reds under the five-kind probe; this card owns 7.** The other is **M1**
(`monkeypatch.py: KeyError: <PageKind.TITLE: 'title'>`, a `delitem` site) and is **CARD-322's**.

| mechanism | reds | the line the gate prints |
|---|---|---|
| **M10** medium-blind empty read | **7** | a residual — see below |

## Why this module matters out of proportion to its seven reds

**It is the 22nd module — the one that sat in NEITHER of CARD-329's populations.** It reaches
the medium hazard through **the medium decision itself**, which is a third population both of
that card's filters were structurally blind to. CARD-329's "the arithmetic closes" was true of
the 20 modules it chose and not of the tree, and this module is the counterexample.

**And it is the cleanest available test of whether M10 can be split at all.** This card's reds
are **pure M10** with no other mechanism mixed in, in one small module. Board-wide M10 is 57
reds across **35 cause lines** held together by a catch-rule with **25** top-level alternations (⚠ this card said *sixteen*; measured **25**, re-derived by the orchestrator with escape-aware depth tracking (my first two counts were wrong — escaped `\(`/`\)` were being read as groups) — ADR-0039/R4) — the
"other" bucket ADR-0039/R2 forbids, wearing a label. **If M10 is really several mechanisms, this
is the cheapest place to find out**, and the answer scopes CARD-354, CARD-355, CARD-356 and
CARD-357, which hold 45 M10 reds between them.

**So treat the split as this card's primary deliverable, not a precondition of it.** Report the
histogram even if the repair turns out trivial.

## Two taxonomy findings from CARD-337's round, which bear directly on your split

Measured while classifying its own single M10 red, and both are reasons the label is not a
diagnosis:

1. **M10's label is wrong for at least one member.** The rule's description is *"medium-blind
   read returns EMPTY"*, and CARD-337's M10 red is a read that returns a **full 2550×3300
   bitmap**. Nothing is empty. It matched M10 only via the alternation
   `'is the blank title page'` — a string from the cause line, not a mechanism. **So when you
   split your 7, expect the label to describe some members and not others, and say which.**
2. **M11 is keyed on a MODULE FACT standing in for a mechanism.** Its rule is anchored on the
   literal `test_book_pdf_band.py`, so CARD-337's red — *mechanically the identical
   `_write_page`-counter collapse* — could not match it and fell through to M10. Both routes
   happened to land on the card owning that module, so nothing mis-routed this time. **The next
   one will.** If your split finds a write-counter collapse, this is why it will not be labelled
   one.

**Recommend re-keying M11 by mechanism** rather than by module, and report whether your 7 contain
anything the taxonomy would mis-key the same way. `scratchpad/card338/classify_reds.py` holds the
rules; **CARD-338 is closed, so a change there is a finding with a measurement, not an edit you
make silently.**

## What to implement

1. **Split the 7 M10 reds by cause signature** and report the histogram. State whether they
   share a cause.
2. **Name the mechanism(s)** in terms a taxonomy could hold — `classify_reds.py`'s `RULES` is
   the authority, and if a rule should be added, propose it as a finding rather than editing
   CARD-338's instrument.
3. Repair or disposition each, per ADR-0042/R6.

## Acceptance criteria

- **AC-1** *Given* the 7 M10 reds, *then* their cause-signature histogram is reported and each is
  named as a mechanism or stated to share one — **this is the card's primary deliverable**.
  (check: review-lens)
- **AC-2** *Given* the finding, *then* the card states what it implies for the 45 M10 reds held
  by CARD-354/355/356/357 — a scoping statement, not a fix.
  (check: review-lens)
- **AC-3** *Given* the five-kind probe, *then* the module's red count is stated before and after,
  and the M1 red is **still present and attributed to CARD-322**.
  (test: named by the implementation; state it)
- **AC-4** *Given* each repair, *then* a plant re-breaks it with its matched control green in the
  same run and `0 skipped`.
  (test: named by the implementation; state it)

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

## Worktree notes

[Round, commits `95c25cb6` + `adaac606`] **Done, and the primary deliverable landed: M10 is THREE
mechanisms, not one.** Probe-scoped **8F/43P → 1F/51P**, the one remaining red being CARD-322's M1
delitem, left standing untouched — a card that repairs its neighbour's red hides which card the
repair belonged to. Unlifted: 51P → 52P, the extra node a new control. The orchestrator's 8 = 7 + 1
split reproduced exactly. **The three-mechanism finding is propagated onto CARD-354/355/356/357**,
which hold 45 M10 reds between them and whose disposition differs by mechanism.

[Round] Per-red disposition: the 4 **A** reds **re-expressed** as a union of the two arms
(`TextCall.exempt` and `StreamFace.exempt`, neither keying on a face's size); the 2 **B** reds
**re-expressed** against `book_guide_vector`'s own per-face record with two structural bounds that
can fail, and **stated in the docstring as genuinely narrower** than what they replaced; the 2 **C**
reds **re-expressed plus 4 retirements with named survivors**, each survivor verified to exist and
each class name **resolved by `ast` against its enclosing `ClassDef`** rather than by text. The new
intersection is asserted **non-empty**, so the day `DIVIDER` stops being raster this reds and that
card owes a reading or a survivor.

[Round] **AC-4: 9/9 mutants re-broke their claim**, matched control green in the same run, `0 skipped`
asserted on the baseline **and on all nine mutant runs**. Five are named edge mutants, and the
non-vacuity one is the important one — `divider-declared-vector`: without it the repair reads green
over a claim that had ceased to exist. Every `src/` file restored **from captured content**,
SHA-256-identical both ends, `git status src/` clean.

[Round] **Two `SCOPE+` fixes under the owner's cut bar, both found by its own measurement and both
the right call.** First, the matched control for the claim it re-expressed **had gone vacuous under
the probe**: it asserted against a hard-coded triple that the *conversion itself* satisfies, so the
band could have gone on being drawn or stopped and the control read green either way — ADR-0039/R1
made that one its own. Second, **a derived parametrize that empties into a SKIP**: a mutant collapsed
the derivation and pytest reported `got empty parameter set`, giving **2 skipped in a module whose
baseline is 0**. A skip is not a deny (ADR-0039/R2); it now yields a named sentinel refused by name,
so it fails saying what happened. That mutant run went `10F/38P/2S → 12F/38P/0S`.

[Round] **A figure of the orchestrator's brief does NOT reproduce, and it is retracted here and on
CARD-354** (ADR-0039/R4): M10's catch-rule has **25** top-level alternations, not *sixteen*. The
round counted 25; the orchestrator re-derived 25 independently — **on the third attempt**, the first
two having been wrong because escaped `\(`/`\)` were being counted as groups. The enumeration is
legible and item 8 is the nested `IndexError: (…|…)`, correctly one. The companion figures
(57 reds, 35 cause lines) are CARD-337's round's and **neither the round nor the orchestrator has
re-derived them** — they remain unverified rather than confirmed.

[Round] **Two taxonomy findings for whoever owns the taxonomy.** M11's rule is anchored on the
literal `test_book_pdf_band.py`, a **module fact standing in for a mechanism** — it would have
excluded all seven of these reds regardless of mechanism, so nothing mis-routed this time but the
defect is confirmed structurally, and re-keying M11 by mechanism is the right call. And mechanism
**B has no rule at all**.

[Round] **A decision the round handed up, and the measurement makes it larger than its question.**
AC-4's instrument could not be committed: force-adding it red
`test_no_new_artefact_file_is_force_added_into_the_resolver_domain`, because the file spells
`ADR-0039/R2`, `ADR-0042/R6`, `CARD-296 AC-5`, `CARD-314 AC-3/AC-4` and more, and the check-ref
search is a **text** search. **That gate working, not failing.** The round un-tracked it
(`adaac606`) and the gate is green again. **The orchestrator's ruling: instruments stay in the
worktree and vanish with it; the findings live in the card record, which is what actually has to
survive.** Measured while deciding, and it is the uncomfortable part: **67 instruments under
`scratchpad/` are ALREADY tracked**, and they name test functions in bulk — `census-converted.txt`
alone spells **182**, `card329/mutate.py` 32, `card338/census_five_kinds.py` 21, `impact.txt` 27. The
gate never fired on them because, as its own docstring says, it is *"deny-by-default over the ignore
rules, not over the resolver's domain"* — so everything tracked **before** `scratchpad/` became
ignored is grandfathered and invisible. CARD-335 stopped the new pollution and the existing set
remains. **Not carded** under the cut bar: it is not blocking the vector slice, and the owner's
priority is finishing ADR-0042. Recorded here as the pointer.

[Round] **One full-suite red the round raised and explicitly declined to clear** — correctly, since
"I see no mechanism" is not a measurement: `tests/test_browser_fixture_scope.py::
TestBrowserFixtures_OrderIndependent::test_reverse_order_passes` passes file-scoped (31 passed, with
its own lock held, so the lock is not the cause) and reds only in the full suite. It spawns a **child
pytest**, so it is suite-interaction- or load-shaped. **Context the orchestrator added:** CARD-349's
gate ran an **armed** full suite hours earlier at **10402 passed / 0 failed**, so main was clean —
which makes this either this card's or a load artefact, and not a pre-existing red. **The merge gate
settles it on the merged tree**; it is not cleared here. The round's own suite was on `95c25cb6`,
before `adaac606`, so no suite yet describes the final commit.
