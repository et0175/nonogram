# CARD-286: The impact derivation cannot see a coupling no import edge carries — so it fails OPEN on the player, and wide on the book

**Status:** ready
**Priority:** P2
**Category:** ops
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/286-impact-set-sees-what-tests-read
**Worktree:** —
**Source:** owner request 2026-10-23 ("we wouldn't run book rendering tests for changes in player or in core algorithms and vice versa") + CARD-271's fix pre-gate finding PG-2 and its merge gate, both measured; backlog.md @ops items "scripts/impact_set.py is blind to static assets" and "the browser-fixture family's node-id registry is discoverable only by a run nobody makes in the inner loop"
**Idea:** —
**Wave:** —
**Created wave:** 55
**Deferred waves:** 0
**Depends on:** —
**Touches:** scripts/impact_set.py, tests/test_impact_set.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`review.test_scope: impact` already narrows every review cycle, and the full
suite already runs only at the merge gate and the wave smoke test. The policy
the owner asked for is therefore in place; what is missing is a derivation that
can be trusted with it. Three measurements from CARD-271, 2026-10-23, all
reproducible from the commands quoted:

**1. It fails OPEN on a static asset — the one direction its own docstring
says it must never fail.** `scripts/impact_set.py
src/nonogram/admin/static/admin.css src/nonogram/admin/static/solver.js`
returns **23 files**, and the intersection with the **16** test files that name
`player-board` / `player-clue` / `player-stage` / `admin.css` is **EMPTY**.
The cause is in `select()` (`:307`): a changed path with no Python module name
resolves `module = module_name_for(...) or tests_module_name_for(...)` to
`None` and hits `continue` (`:344`/`:352`), on the stated grounds that it
"changes no import edge, and the always-on scanners already cover the
tracked-tree guards that DO read it". True for a guard that reads the asset as
**text**; false for a browser test that loads it at **runtime**, which is how
every player test reads these two files. `changed_from_git`'s own docstring
(`:378`) states the property being broken.

**2. And wide in the other direction at the same time.** The 23 files it does
return for `solver.js` include `tests/test_book_difficulty_dots.py`,
`tests/test_admin_binding.py`, `tests/test_admin_regrade.py` — book and
binding tests that do not read it. So for an asset card the selection is wrong
in **both** directions simultaneously: it names the always-on scanners and
omits the real readers. A cycle gated on it would run book renders and no
player board.

**3. A coupling can also be a subprocess, not an import.** CARD-271's merge
gate went red on
`tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured`:
the card added 27 node ids to the browser-fixture family and registered none,
and **25 of the 27 had been owed since the implementation commit**. That guard
names none of the card's selectors, so it was outside the 17-file selection
the card gated on four times, and it reaches the family through a
`--collect-only` **subprocess**, so there is no import edge to follow either.
Four gate selections, two full-depth review cycles, a pre-gate and two
fix-round re-derivations passed over it. The first thing to see it was a
24-minute full suite.

**The fix shape, and it is one this script already uses elsewhere: derive the
edge, or fail closed.** A static asset's readers are derivable from the asset
itself — a test that loads `admin.css` at runtime names the file, or one of the
selectors/identifiers the asset declares. That is exactly the `SCAN_IDIOMS`
precedent at `:102`: match the tree as text where the import graph cannot see
the coupling. Where no reader is derivable for a changed path, the answer is
**`FULL`**, not a quiet omission — which is what every other unmodelled path
in this script already does (ADR-0039/R2's default-deny, applied to the
board's own evidence rather than to product code).

**What NOT to do.** Do not fix this with a hand-maintained map of families
("book tests ⊥ player tests"). Measured 2026-10-23, that partition is already
false: `tests/test_book_finalise_guide_preview_layout.py:6` reads
`static/admin.css` (the Finalise guide preview shares the admin stylesheet
with the player), so a "player" asset has a book reader. And a hand-maintained
map is the same artefact class as the registry in measurement 3 — a census a
card can break without ever learning it did. Derive it.

**The direction that is already right, and must stay right.** A core change
must keep pulling the book tests in: `src/nonogram/admin/book_pdf_generator.py`
imports `nonogram.difficulty`, `nonogram.errors`, `nonogram.export`,
`nonogram.export.layout` and `nonogram.export.pdf`, so the book pipeline sits
on top of the core algorithms and the import graph models that correctly. Only
the asset and subprocess couplings are missing.

**Price the work before trusting it.** The 2026-10-15 profile
(`meta/profiling/suite-hotspots-20261015.md`) puts the render-heavy set at
**21.23 %** of the suite and the browser family at **39.78 %**, so a player
card that stops running book renders and a book card that stops running the
browser family are worth roughly a fifth and two fifths of each cycle. Record
today's equivalents from `meta/profiling/suite-durations-20261023.txt` beside
them; a narrowing whose saving is not measured is a guess.

## Acceptance criteria

- **AC-1** (happy, the omission): *Given* `src/nonogram/admin/static/solver.js`
  and `src/nonogram/admin/static/admin.css` as the changed set, *when* the
  selection is derived, *then* it contains every test file that names those
  filenames or a selector the assets declare — at minimum the 16 files naming
  `player-board`/`player-clue`/`player-stage`/`admin.css` plus
  `tests/test_book_finalise_guide_preview_layout.py`. (test:
  `TestImpactSet_AStaticAssetSelectsTheTestsThatReadIt`)
- **AC-2** (guard, default-deny): *Given* a changed path for which no reader
  can be derived, *when* the selection is derived, *then* the answer is `FULL`
  and the reason names the path and the rule that produced it. (test:
  `TestImpactSet_AnUnderivablePathFailsClosedAndSaysWhy`)
- **AC-3** (happy, the subprocess coupling): *Given* a changed
  `tests/test_puzzle_solver_*.py`, *when* the selection is derived, *then* it
  contains `tests/test_browser_fixture_scope.py`. (test:
  `TestImpactSet_TheBrowserFamilyGuardFollowsItsFamily`)
- **AC-4** (guard, the direction that must not regress): *Given* a change to a
  core module the book pipeline imports (e.g. `src/nonogram/export/layout.py`),
  *then* the selection still contains the book render tests it contains today —
  asserted as a superset of a recorded baseline, so narrowing cannot silently
  drop them. (test: `TestImpactSet_ACoreChangeStillReachesTheBookTests`)
- **AC-5** (guard, completeness over the asset tree): *Given* every file under
  `src/nonogram/**/static/`, *then* each one has a derivation path and the set
  of asset extensions the script knows how to read is asserted as an equality,
  not a floor — a new asset type with no rule fails the suite rather than
  joining the silent class. (test:
  `TestImpactSet_EveryShippedAssetHasADerivation`)
- **AC-6** (edge, no false narrowing): *Given* each of the three measured
  cases above, *when* the derived selection is run, *then* it is a **subset**
  of what the full suite runs and a **superset** of the tests that actually
  exercise the change, both enumerated in the card. (recorded, verified by
  review)
- **AC-7** (happy, measured): *Given* the 2026-10-23 profile, *then* the card
  records what a player card and a book card each save under the repaired
  derivation, against the full-suite figure. (recorded, not asserted)

## Guardrails

- G-1: Fail **closed**. No change may make an unmodelled path return anything
  but `FULL`; the whole defect is a `continue` where a `FULL` belonged.
- G-2: The always-on scanners stay in every selection — they are what cover
  the tracked-tree guards, and this card narrows nothing that is already
  always-on.
- G-3: Do not edit `src/**`. This is board tooling; a production change to make
  a derivation easier is out of scope and would be a different card.
- G-4: Do not solve this by returning `FULL` more often in general. A
  derivation that answers `FULL` for every asset card is correct and useless —
  AC-6's subset/superset pair is what keeps both halves honest.
- G-5: Do not introduce a hand-maintained family map or any other census a card
  must remember to update (see "What NOT to do"). Every set this card adds is
  derived, or it is asserted as an equality with a completeness test
  (ADR-0039/R1, ADR-0039/R2).
- G-6: `--base <rev>` keeps returning `FULL` when a changed path lies outside
  `KNOWN_ROOTS` (`:95`) — e.g. the repo-root `ONLINE_GAME_SPECIFICATION.md`,
  which is why `--base main` answers `FULL` today. That behaviour is correct
  and is **not** to be "fixed" by widening `KNOWN_ROOTS`; if it is to change at
  all, it changes by making the path's readers derivable, and AC-2's reason
  line makes the `FULL` auditable instead of mysterious.
- G-7: Out of scope — the `Touches`-is-a-prediction problem (its own @ops
  item: a card can touch a hotspot it never declared, as CARD-206 did with
  `tests/helpers/book_corpus.py`), retiring subsumed tests (CARD-220), and
  reshaping the browser-family registry itself (its own @ops item). This card
  makes the registry *reachable*; it does not redesign it.

## Architecture context

- **FR:** — (board tooling)
- **ADR:** ADR-0039/R1 (a claim needs a control that can fail — AC-2/AC-5),
  ADR-0039/R2 (a guard set derived from an enumerable authority is
  default-deny — G-1/G-5), ADR-0006/R1 (no new dependency).
- **CON:** —
- **Components:** none (scripts + tests only).
- **Trace:** not applicable.

## Worktree notes

—
