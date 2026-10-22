# CARD-262: The page-position guard's door axis is open; close it or name every exemption with a control

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/262-close-the-door-axis
**Worktree:** ../PythonProject4-card-262
**Source:** CARD-206's **family-regression escalation** at cycle 3/3 (streak 2, 2026-10-22). Owner chose **slice**: the guard is not CARD-206's work, so CARD-206 merged its blank title page with the claim narrowed and the door axis declared an exemption, and this card takes the mechanism.
**Idea:** —
**Wave:** 53
**Depends on:** —
**Touches:** tests/test_book_export_interior_cover.py, src/nonogram/admin/book_pdf_generator.py
**Review score:** —
**Started:** 2026-10-22T08:08:13Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why — the same claim was made and broken three times, each by the fix for the last

This card exists because CARD-206's review loop **regenerated one defect three times** and `cmd-start-review`'s family-regression detector escalated it at streak 2. The family, in one sentence:

> **The guard keeps claiming a reach it has not measured.**

| cycle | finding | attribution | what the claim was |
|---|---|---|---|
| 1 | F-102 | the implementation | *"**Every** front-matter position after it counts from here rather than from a literal"* — a bare literal survived, invisible to both controls |
| 2 | F-201 | **fix 1** | the rebuilt guard "enumerates every page position in the module" — **8 of 9** planted shapes escaped silently, and one sentence of its declared blind spot was false |
| 3 | F-301 | **fix 2** | *"**And it fails closed** … a shape a position flows through that none of them names is a refusal"* — true of positions, **false of doors** |

Fix 2's work was good and most of it stands: it replaced shape-enumeration with two **closures** (binding occurrences from the module's own store contexts; string fields from a four-member allowlist, everything else a refusal), so three shapes nobody wrote a branch for are caught — a `match`/`case` capture, a lambda parameter default, a module function's return value. The orchestrator confirmed the closure generalises by planting a seventeenth shape its author never considered (a position hidden in a **string constant** argument to `setattr`): **exit 1, two tests red**.

**What it did not close is the other axis.** `called(call)` recognises a door only as `ast.Name` or `ast.Attribute` in `Call.func`, and the refusal for an unrecognised door is keyed on `isinstance(node, ast.Attribute)`. A door whose identity is not a syntactic name in the call position is **dropped before either closure sees it** — not read, and not refused. Measured, four shapes:

```
_d = getattr(self, "page_spec"); _d(3 + len(section))        -> pytest exit 0, nothing reds
getattr with an assembled name                               -> silent
a door through a local string variable                       -> silent
operator.methodcaller("page_spec")                           -> silent in the guard's domain
```

The orchestrator reproduced the first independently, line-count-preserving, file restored byte-identical: **F-102's exact literal reaches the real geometry door** while `refusals == []`, `tuple(vocabulary) == POSITION_NAMES`, `len(sites) == 23`, `_bare_literals == []`, the per-door control and the sixteen-row shape table **all pass**. `getattr(` is already an idiom of that module (`book_pdf_generator.py:5245`), so this is not an exotic shape.

**And the table cannot catch the class.** `PLANTED_SHAPES` has sixteen rows and every row declares a non-empty outcome, so it regresses only on shapes its author chose. A table of planted shapes is a regression net, never a completeness argument — which is the lesson the three cycles above actually taught, and the one this card must not relearn.

## What to implement

1. **Decide and declare the semantics BEFORE writing code.** This is a `Complexity: architectural` card for one reason: three attempts failed because nobody defined the term. Write into the card, first, what *"the guard enumerates every page position"* means — over which axes (position, door, and any third), which syntactic shapes, and what the guard does with a shape it cannot analyse. The failure-matrix discipline, applied to a static analyser. **A guard whose semantics are decided after its code is the shape that escalated CARD-206.**
2. **Close the door axis, or declare it with a control.** Either make a door's identity derivable where it is *used* rather than where it is spelled, or keep the exemption and give it what ADR-0039/R3 demands — a control that is **caught with the exemption removed and missed with it in place**. Fix 2's position-axis exemption is the model to copy: it is a single analyser parameter (`follow_terms`), not a per-shape branch, so removing it catches the whole class at once, which the cycle-3 reviewer verified on a shape the control does not contain.
3. **Give `PLANTED_SHAPES` a control, or stop it reading as completeness.** Today it cannot fail on the class. Either add a row whose declared outcome is *empty* (so a silent pass is a red) — the shape CARD-260's instrument uses — or narrow its docstring to "a regression net over the shapes measured so far", which is what it is.
4. **Close F-303, inherited from CARD-206 cycle 3:** 2 of `BINDERS_READ`'s 8 members — `AsyncFor` and `NamedExpr` — have **no control anywhere**; `comprehension` and `withitem` do, via planted shapes V7 and V12. A member of a derived set with no control is the set's own ADR-0039/R1 defect, and this is the third time that exact shape has appeared on this board (CARD-206 F-203 on `GEOMETRY_DOORS`, then here).

## Acceptance criteria

- **AC-1** *Given* the semantics declared in step 1, *then* the card states them **before** the first code commit, and the review can check the implementation against them rather than against a reading invented afterwards. (test: the declaration is card text; its control is that cycle 1's review quotes it.)
- **AC-2** *Given* a geometry door reached through `getattr` with a literal name, with an assembled name, through a local string variable, and through `operator.methodcaller`, *then* each is either **read** (its position enumerated) or **refused** (red, naming line and shape) — never silent. All four demonstrated, and `operator.methodcaller`'s demonstration must be made in a domain where the kill is the guard's own assertion, not production raising `NameError` for an unimported module (cycle 3 measured that confusion).
- **AC-3** *Given* a shape neither the implementer nor the reviewer enumerated, *then* the closure still reads or refuses it. Its control is a **plant chosen by someone other than the author** of the walk — the orchestrator's `setattr`-in-a-string-constant plant is the precedent, and a card that only passes its author's own table has not met this.
- **AC-4** (exemption) *Given* any axis left open, *then* it is a named ADR-0039/R3 exemption whose control is **caught with the exemption removed, missed with it in place**, and whose cost is **asserted** (how many sites change), not declared.
- **AC-5** (guard) *Given* the whole change, *then* `len(sites)`, the vocabulary and the guide-counting count stay **equalities** that red in **both** directions — addition and removal. Cycle 3 supplied the removal direction for all three and it must not regress to a floor.

## Guardrails

- G-1: **No production behaviour change.** The module has **0 offenders and 23 derived sites** today and every page number is right; this card changes what the guard *sees*, not what the generator *does*. A change to `src/nonogram/admin/book_pdf_generator.py` beyond making a door's identity derivable is out of scope.
- G-2: Do not edit `src/nonogram/export/layout.py` (CARD-204's), and keep the three CON-019 byte-identity tripwires green without editing them.
- G-3: `nonogram_poc` is never created, dropped, connected to or truncated; `_refuse_unless_test_database` is neither widened nor bypassed.
- G-4: No new runtime dependency (ADR-0006/R1); stdlib only.
- G-5: **Do not weaken an arm to make a broader claim true.** CARD-259 measured the alternative: extending a control to texts it could not hold reds immediately, and relaxing the arms to accommodate that would trade a real control for a broader, emptier one. If an axis cannot be closed, declare it (AC-4) rather than loosening what already works.
- G-6: Take no timing measurements and report no durations.

## Architecture context

- **Components:** COMP-009 (`book_pdf_generator.py`) and its test guard. No requirement's verifying test changes.
- **ADR:** **ADR-0039/R1–R3** are the whole subject — a claim needs a control that can fail; a guard's set is derived from an authority the runtime can enumerate and **a shape it cannot analyse is a FAILURE, never a silent pass**; every exemption carries a control for what it must not absorb. ADR-0036/R2 (geometry reached only through COMP-007's layout functions) is why a "door" is the right authority at all.
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## System contract

_Derived at dispatch (2026-10-22) by `system_rules.py --card CARD-262 --root meta/architecture`
(`card_scope: touches`), curated under `meta/kanban/curation.md`: **projection 41 → kept 14, dropped
27**. A projection — fix the source artifact, never this list._

**Derivation:** keep every `check.kind: review-lens` rule (nothing executes them, so a reviewer is the
only enforcement), plus every `kind: test` rule belonging to an ADR whose text declares a reach limit —
the idiom *"reach, stated rather than implied"*, matched **in the ADR files and case-insensitively**,
because the lens output carries no comment text and ADR-0039 writes it in capitals. That selects
**ADR-0036, ADR-0037, ADR-0039**. The remaining 27 `kind: test` rules are dropped: the suite executes
them on every gate.

**Sanity check (curation.md's own):** `Touches` includes `tests/** and src/nonogram/**`, so ADR-0039 must be kept — it is
(ADR-0039/R1, ADR-0039/R2, ADR-0039/R3).

**ADR-0036/R2 is the rule this card's authority rests on** — *book page geometry is computed only by COMP-007's layout functions with the book's PageSpec* — because that is what makes a geometry **door** the right thing to derive page positions from at all. And ADR-0039/R2's second clause is the card's gating subject: *a shape it cannot analyse is a FAILURE, never a silent pass.*

**Review-lens — nothing executes these; the reviewer is the control** (8):

- **ADR-0022/R1** — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from one integer.
- **ADR-0033/R1** — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membership mirror (puzzles.book_id).
- **ADR-0036/R2** — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself.
- **ADR-0037/R1** — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only.
- **ADR-0038/R6** — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the solution before the puzzle is solved, and any public phase reopens this ADR (CON-021).
- **ADR-0038/R7** — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra.
- **ADR-0038/R8** — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. Once a CI pipeline exists, it installs Chromium (playwright install chromium) before running them; until then there is no CI, and that is a known gap, not a met clause.
- **CON-021** — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No other surface — the CLI, the web UI, or any public or hosted page — offers an interactive or playable puzzle. Play state is never persisted on the server: no progress, marks, error count, score or solve time is written to a database, file or server, no network request is made per mark, and no user account exists for playing (CON-017). The one place play state may be kept is the browser's own localStorage, per puzzle, so that a puzzle reopened in that browser resumes where it was; it never leaves that browser. The admin player ships the puzzle's solution grid to the browser to compute the error count and the solved state; this is permitted for the admin panel only, and a public or reader-facing player must not send a puzzle's solution to the browser before the puzzle is solved.

**Reach-limited — the ADR states its checks do not reach code written later** (6):

- **ADR-0036/R1** — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. — check: `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`
- **ADR-0036/R3** — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same difficulty glyph, and four slightly different dots cannot be fixed once a book is on paper. — check: `test_the_books_own_pages_carry_no_undeclared_round_mark`
- **ADR-0036/R4** — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: the cheapest way to print a difficulty dot is to append a bullet to a header string, and that route bypasses the one drawing site and CON-020's type floor at once. — check: `test_no_module_types_a_round_mark_as_a_character`
- **ADR-0039/R1** — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: caught WITH the set member present, missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage, and must be narrowed to what is measured or deleted. — check: `test_the_control_for_each_spelling_depends_on_the_set`
- **ADR-0039/R2** — A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where no such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE, never a silent pass, and the unanalysable sites become named exemptions under ADR-0039/R3. — check: `test_the_guard_sets_are_derived_and_not_hand_written`
- **ADR-0039/R3** — An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT absorb — caught with the exemption removed, missed with it in place — is held to an equality against the sites that exist today, and records whatever it still cannot see as a measured bound with its own failing control. — check: `test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw`

_Dropped (27), each executed by the suite on every gate: ADR-0006/R1, ADR-0022/R3, ADR-0022/R4, ADR-0027/R2, ADR-0032/R1, ADR-0032/R2, ADR-0038/R3, CON-005, CON-009, CON-010, CON-011, CON-012, CON-015, CON-016, CON-020, INV-001, INV-002, INV-003, INV-005, INV-006, INV-007, INV-008, INV-009, INV-010, INV-011, INV-012, INV-013._

## Worktree notes

- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`, reading the ADR files **case-insensitively** for the reach-limit idiom. Sanity check: `Touches` includes `tests/**` and `src/nonogram/**`, so ADR-0039 must be in the kept set — if it is not, the derivation is broken, not the scope.
- **[Why this is `architectural` and estimated 1d, not `trivial`]** The diff will be small. Three attempts have already been small. The owner's wave-50 rule floors a claim card at 0.75d and forbids `trivial`; this one is cut at **1d** and `architectural` because its deliverable is a **decided semantics**, and because `Complexity: architectural` is what makes the pipeline read the ADRs in full and demand a declared failure matrix before code — the exact discipline whose absence escalated CARD-206.
- **[Read CARD-206 before writing anything]** Its `[Review 1/3]`, `[Fix 1]`, `[Review 2/3]`, `[Fix 2]` and `[Review 3/3]` notes are the measured history of three failures and one strong partial success. In particular: what the closures *are*, which shapes they catch that nobody wrote branches for, the exemption-as-single-parameter pattern, and the two "fails closed" sentences that were narrowed at the slice.
- **[CARD-206 shipped one uncertified edit, and this card inherits the consequence]** The narrowing (commit `3dd1d11d`) was made after cycle 3, so **no review cycle has seen it**. It is a narrowing plus a declared exemption, so there is less to control than before — but its wording is the thing this card either makes true or replaces, and cycle 1's review here should read it with that in mind.
- **[Use CARD-260's committed instrument]** `tests/kill_matrix.py`, documented in `tests/README.md` from line 453. Do not write another. Keep deletion mutants **line-count-preserving**, aggregate **any-RED**, target the occurrence inside the arm you mean, and **report the DOMAIN of every per-assertion figure** — and note cycle 3's lesson that a mutant can kill *outside* the assert matrix's domain, in which case both domains are recorded rather than a blank matrix quoted.
- **[A measured bound to inherit, not re-derive]** CARD-206 cycle 2 established that **no module outside the generator computes a front-matter-relative interior position today**: an AST census found 23 `page_spec`/`book_page_spec` calls across 5 modules, 18 of them inside the generator, and of the other five only `book_proof.py:767` passes a non-trivial position — a standalone proof document with no front matter. Re-derive it if you rely on it; do not restate it without re-deriving.
- **[Not attempted by any cycle, recorded as unchecked rather than clean]** `__set_name__`, metaclass and `type()`-constructed class routes into the walk. Cycle 3 declined them because no line-count-preserving plant reaches them without restructuring a class body. If this card's semantics (step 1) say they are in scope, they need a plant that does not pretend to be line-count-preserving.
