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
**Review score:** 5.7 (cycle 1, min_score 8 — Critical; the axis is not closed)
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

---

## Worktree notes — implementation (2026-10-22)

### SEMANTICS: what *"the guard enumerates every page position"* means — declared before the code

Written first, as step 1 and AC-1 require, so review checks the implementation against a decision.
Nothing below was measured after the fact; the measurements that follow this block were taken against
it. Where the implementation later diverged from this declaration, the divergence is recorded in
**[SEMANTICS reconciliation]** below rather than edited into this block.

**The guard's subject.** `TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage` reads one
module's text (`src/nonogram/admin/book_pdf_generator.py`) with `ast` and reports, for every interior
page position that module computes, the integer literals that position is built from. Its claim is that
a front-matter page count written as a bare literal cannot hide anywhere in that module.

**It is a static analyser, so its semantics are a failure matrix over AXES.** An axis is one question
the walk must answer about a node, and the walk's answer on each axis is exactly one of three values:

| value | meaning |
|---|---|
| **READ** | the walk analysed the shape and reported its literals |
| **REFUSED** | the walk could not analyse the shape and said so — a `refusals` entry naming line, shape and name, which reds |
| **SILENT** | the walk neither read nor refused it. **Forbidden by ADR-0039/R2 except as a named exemption under R3 with a control that can fail.** |

**The four axes, named.** Three attempts failed because only the first was ever defined.

1. **POSITION axis** — *which expressions in the module are page positions.* Closed by CARD-206 fix 2,
   and this card does not rebuild it. Closed by two closures over the **grammar**, not over a list of
   shapes: (a) the *binding closure* — every binding occurrence of a position name is found from the
   module's own non-`Load` store contexts (`Name`/`Attribute`/`Subscript`, decomposed through
   `Tuple`/`List`/`Starred`), and the binder it sits in is looked up in `BINDERS_READ`; a binder not in
   that table is REFUSED; (b) the *string closure* — a position name held as a bare string in any
   `(class, field)` pair outside `STRING_FIELDS_READ` is REFUSED. One declared R3 exemption:
   `EXEMPTION` (a non-position term of a position expression is read for its written literals and not
   followed into its own bindings), removable with the single analyser parameter `follow_terms`.
2. **DOOR axis** — *which calls in the module are geometry doors (ADR-0036/R2).* **This card's
   subject, and it was SILENT.** Declared semantics, chosen here: *a call whose callee's identity this
   walk cannot derive is REFUSED.* Closed by two closures, and by **no per-shape branch** — neither
   closure mentions `getattr`, `setattr`, `methodcaller`, `attrgetter` or `vars`:
   - **callee-identity closure** — for every `ast.Call` in the module, the callee must be *anchored*:
     `Call.func` is an `ast.Attribute`, or an `ast.Name` whose every binding occurrence in the module
     (through the same `BINDERS_READ` table the position axis uses) holds a value that is itself a
     syntactic `Name` or `Attribute`. A callee of any other node class, or a `Name` bound anywhere to an
     arbitrary expression, is REFUSED. This is what closes a door whose name is **never spelled** —
     assembled at runtime, or taken from data.
   - **door-spelling closure** — a geometry-door name appearing in any `(class, field)` pair outside
     `DOOR_SPELLINGS_READ` is REFUSED. The exact mirror of the position axis's string closure, keyed on
     `GEOMETRY_DOORS` instead. This is what closes a door reached by **spelling its name as data**.
   Each arm is individually removable (`door_arms=`), and **each catches a shape the other misses** —
   so neither is decoration.
3. **MODULE axis** — *which text the walk reads at all.* It parses exactly one module. A position
   computed in another module and passed in is outside the enumeration, not refused by it.
   **DECLARED, not closed** (AC-4), with the measured bound re-derived below. The walk cannot be closed
   on this axis without becoming a whole-program analyser, which is a different artefact.
4. **VALUE axis** — *which wrong positions are wrong in a way an integer literal reveals.* A position
   spelled `0` or `1` is indistinguishable from the legitimate 1-based term, and a position whose
   literal lives outside the module's text (a database row, a config) is not in the AST at all.
   **DECLARED, not closed** (AC-4), and it overlaps rather than leans on
   `TestBookExport_TitlePageCountedEverywhere`'s monkeypatch case, which covers every position that
   reaches a byte of output.

**What the guard does with a shape it cannot analyse**, on every axis: axes 1 and 2 **REFUSE** — a
`refusals` entry, which reds, naming the line and the shape. Axes 3 and 4 are SILENT by declaration, and
each carries its own control below. There is no fifth state and no "assumed clean".

**What a table of planted shapes is.** `PLANTED_SHAPES` and the new door-shape table are **regression
nets over the shapes measured so far — never completeness arguments.** That is a semantic decision, not
a hedge: a closure's completeness claim rests on its *quantifier* (every `ast.Call`; every
`(class, field)`), which the tables cannot establish and are not asked to. Their own control is that a
row may not declare a SILENT outcome: `test_no_planted_shape_is_declared_silent` reds on an empty
declared outcome in either table, so a blind spot can never be parked in a table as acceptable.

**Closed vs declared, decided here:**

| axis | decision | its ADR-0039/R3 control |
|---|---|---|
| POSITION | CLOSED (inherited) | `BINDERS_READ`/`STRING_FIELDS_READ` per-member controls; `EXEMPTION` removable by `follow_terms`, cost asserted |
| DOOR | **CLOSED (this card)** | both arms removable by `door_arms=`; each arm's own shape; the shipped module's refusal count asserted as an equality |
| MODULE | **DECLARED** | an AST census of every geometry-door call outside the module, re-derived and asserted |
| VALUE | **DECLARED** | `POSITION_LITERALS` is the removable parameter: the control is the planted-literal pair |

### [SEMANTICS correction] The declaration was wrong on one clause, and it is corrected here, not rewritten

The SEMANTICS block above is left as it was written, before the code, so review can see what was
decided. **One clause of axis 2 was wrong**, and an independent plant falsified it:

> *"`Call.func` is an `ast.Attribute`, or an `ast.Name` whose every binding occurrence in the module …"*

The clause before the comma is the hole. Treating **every** attribute callee as self-evidently anchored
re-opened the whole F-301 family one storage over. **Corrected to:** *the callee must be a name or
attribute whose every binding occurrence **in its own storage** holds a syntactic `Name` or
`Attribute`.* Both docstrings and the code now say that; the block above does not, deliberately.

Two further refinements, recorded rather than folded into the block:

1. **An annotation-only `AnnAssign` binds nothing.** `field: int` in a dataclass body holds no value, so
   it is not a binding occurrence. Without this the module's own `interior_page_count: int` at
   `book_pdf_generator.py:2889` would make three legitimate calls to the *function* of the same name
   refusals — found by measuring the first draft of the arm, not by reasoning.
2. **The callee-identity arm is scope-insensitive.** The block already said "every binding occurrence
   **in the module**", so this is a bound rather than a divergence: a name bound opaquely in one
   function and used as a callee in another is refused although no door can reach it. That is an
   over-approximation in the **fail-closed** direction (ADR-0039/R2's default deny) and it costs **0
   refusals** on this module, asserted. The module's one real shadowing case — the nested `def technique`
   at `:4448` against the `technique` parameter at `:4350` — is **not** refused, because an `ast.arg` is
   not one of `BINDERS_READ`'s shapes.

### [AC-3] The independent plant falsified this card's own closure, and that is the result

AC-3's control is a plant chosen by **someone other than the author of the walk**. An adversarial
reviewer was given the harness and both tables, told to go where the tables do not, and told that
finding nothing silent would be a useful result. It ran **41 plants, 38 of them in neither table**, and
returned **23 silent**. The author's own 18-row table passed every row while a stranger's shapes did
not — which is exactly what AC-3 exists to expose, and why a table of planted shapes is a regression
net and never a completeness argument.

**What was closed (the defect this card then owned).** The storage family, three plants:
`self._door = getattr(self, "page_" + _SUFFIX)` then `self._door(3 + len(section))` — W0 with `_d`
spelled as an attribute — plus the same door laundered through a helper, and a `__call__` object parked
on an attribute. All three were **SILENT**. They are now W12, W13, W14 and all three **refuse**.

**The obvious fix is wrong, and this is the measurement that chose the real one.** Extending the anchor
check to attribute callees against **one** opaque table costs **51 refusals on a module with no defect
in it** — `text = f"…"` and `draw.text(…)` share a spelling and nothing else; the collisions are `text`,
`line`, `cell_sizes` and `page_spec`. Keying the table on **(storage, spelling)**, with `a local name`
and `an attribute` kept apart and each callee looked up in its own storage, costs **0**. Both figures
re-derived through the same prototype walk (`callee_arm`/`arm` in the scratchpad), and the 0 is asserted
in the suite by `test_the_door_axis_arms_reach_every_call_and_refuse_none_of_them`.

**Three more of the reviewer's plants were already refused and are now rows**, so the net grows rather
than the claim: W15 (an opaque door bound by a `for` target), W16 (a walrus callee), W17 (a door in a
dict on `self`, a subscript callee). None is a shape anyone wrote a branch for — the closures catch
them — which is the reviewer's own conclusion: *"On the `ast.Name` axis, yes — genuinely. I tried to
find an opaque local door the arms miss and failed."*

### [Axis 5, DECLARED not closed] the CALL-GRAPH axis, found by the independent plant

The reviewer's remaining silent shapes are **not** door-axis shapes. They are a position forwarded past
a callee this walk resolves **by name** against the module's own `defs`:

- an **alias of a non-door method** that carries a position — `_f = self.puzzle_pages;
  _f([], 3 + len(section))`. `puzzle_pages`' `first_page` is in the vocabulary; the alias hides the
  literal. The walk refuses this on the *door* (W4) and has nothing for non-door functions.
- a **parameter used as a callee** — a callback `make_spec(3 + len(section))`. A parameter is an
  `ast.arg`, never a binding occurrence under one of `BINDERS_READ`'s shapes, so it can never enter the
  opaque table. A `lambda` in the same place **is** refused (V13), so the gap is specifically a nested
  `def` reached through a parameter.
- a **`*args` forwarder** — `def _answer_spec(generator, *position_args)`. `vararg` is not in
  `posonlyargs + args`, so the fixed point maps no caller argument onto it though the star reaches the
  door.

**This falsified a sentence this card had already written into both docstrings** — *"the walk fails
closed on **both** the position and the door axis"*. True of the position axis's **binding** closure,
false of its **call-graph** resolution. **Narrowed in both docstrings rather than defended**, which is
the board's rule applied to this card's own prose: prefer deleting or narrowing a claim over adding one.
Axis 1 now reads *"closed on binding occurrences … **not** closed on how a position reaches a callee —
that is axis 5"*, and the method docstring points at the class's axis table as the authority instead of
restating it.

### [The VALUE axis] the declaration predicted this before any of it was planted

Axis 4 was declared open in the SEMANTICS block **before the code**, and the reviewer's Groups B and C
are what it predicted:

- **the count spelled in ones** — `… + len(section) + 1 + 1 + 1 + 1`. `POSITION_LITERALS = (0, 1)`
  admits `1` and caps nothing, so three extra front-matter pages are added while the derivation, the
  `GUIDE_PAGE_COUNT` load, the vocabulary, the 23-site equality **and** the 7-site guide equality all
  stay intact. **This is the one I would fix first** and it is not this card's axis.
- **a module constant the literal reader does not reach** — `module_integers` reads only a top-level
  `ast.Assign` of a bare int `Constant`, so `_HIDDEN_FRONT_MATTER: int = 3`, `= 1 + 2`, a constant
  inside an `if` block and `len(_FRONT_MATTER_PAGES)` over a module tuple all defeat V15's mechanism.
- **what counts as an integer** — `int(3.0)`, `True + True + True`, `ord("\x03")`, `int("0x3", 0)`,
  `eval("3 + len(section)")`.

### [The bound has a control that fails in both directions]

`MEASURED_BLIND_SPOTS` holds four of the reviewer's shapes — two value-axis, two call-graph — and
`test_the_declared_blind_spots_are_still_exactly_these` asserts they **are** silent. That is what makes
a declared bound falsifiable: narrow the value axis or close the call-graph axis and it reds, naming the
row, so the declaration is re-measured instead of standing while the code moves underneath it. It is
deliberately **not** a row of `DOOR_SHAPES`/`PLANTED_SHAPES`, because
`test_no_planted_shape_is_declared_silent` forbids a silent outcome there: a blind spot parked in a
regression net as *expected* is the shape ADR-0039/R2 forbids. A bound lives in its own table.

### [TDD] one line per criterion

- **AC-1:** no test — the deliverable is card text. The `SEMANTICS:` block above was written and saved
  **before** the first line of guard code, and before the first commit (`8bc7671f`). Its control is
  that cycle 1's review quotes it; its honesty check is **[SEMANTICS correction]**, which records the
  one clause an independent plant falsified instead of rewriting the block to match the code.
- **AC-2:** `test_every_door_shape_is_read_or_refused_and_never_silent` **red→green**. Red first with
  9 of 12 rows returning `()`; the failure named every silent row. Green after the two closures. Then
  red **again** when the independent reviewer's W12–W14 were added, and green after the
  (storage, spelling) keying.
- **AC-3:** `test_the_declared_blind_spots_are_still_exactly_these` **red→green** (it did not exist
  until the reviewer's plants existed). AC-3's own control is not a test of mine at all — it is the
  reviewer's 41 plants, 23 silent, one of which was a defect in this card's own closure.
- **AC-4:** `test_the_module_axis_bound_is_measured_rather_than_declared` **red→green** — red first
  because the first draft hard-wired `args[1:]` for the position slot, which is review cycle 2's F-203
  defect exactly, and reported nothing; green once the slot is read from each door's own signature via
  `_door_position_slots`. `test_the_declared_blind_spots_are_still_exactly_these` carries axes 4 and 5.
- **AC-5:** no new test; the three equalities are unchanged and re-measured green (23 sites, the same
  six-name vocabulary, 7 guide-counting expressions). Both directions re-certified by mutant below.
- **F-303:** `test_every_binder_read_is_what_makes_its_own_shape_read` **red→green** — red first on
  `Assign` because the tiny per-binder sources define only one of the two doors and an unseedable door
  is itself a refusal (F-203 again); green once only `page_spec` is seeded.

### [Mutants] 16 of 16 ANY-RED, and the domain of every figure

**Domain, stated in full:** the signal is **pytest's own exit code** over the selection, i.e. a
**test-level** ANY-RED, *not* a per-`ast.Assert` kill matrix. The denominator is **collected tests**,
never assert-node count. Every mutant is **line-count-preserving**, applied to
`tests/test_book_export_interior_cover.py` on disk, with `cp -p` backup, restore in a `finally`, and
`shasum -a 256` verified byte-identical afterwards (`0966643820…` before and after both rounds).
SHIPPED was re-run **between** every mutant and was `exit 0, 0 failed` each time.

**The committed instrument was NOT the source of these figures, and that is a declared gap.** A
`tests/kill_matrix.py` run over 13 mutants (`Pass.RERAISING`, selection = the guard class) was started
and **did not finish** — it produced no matrix before it was stopped, so **no per-assertion figure is
quoted anywhere in these notes**. It was stopped with SIGINT so the instrument's own restore `finally`
ran, and the target was then verified against nine pristine markers and `git status`. Recorded as
incomplete rather than replaced by a partial grid: per-arm attribution for these mutants is **owed**,
and the figures below are test-level only.

| round | domain | result |
|---|---|---|
| 1 | each mutant scoped to **one** test nodeid | 13 RED / 3 SURVIVED |
| 2 | the three survivors re-run against the **whole guard class** | **3 RED** |

**Round 1's three survivors were defects in the mutants and in the selection, not findings about the
tests** — and the first of them is this card's own family, hit on its own instrument:

1. **M14** (`POSITION_LITERALS = (0, 1)` → `(0,)`) read SURVIVED under a one-test selection and kills
   **8 arms** against the class. **A scoped negative is unsound here**, so round 1's scoped domain is
   reported for its positives only; no negative result from it is quoted.
2. **M15** changed only the opaque table's *setter* and not its *lookup*, so it **disabled** the arm
   instead of conflating the two storages — a mutant doing something other than what it is named.
   Corrected (`M15b`, both sides) it reds **5 arms**, including the reach test.
3. **M16** changed only a blind-spot row's **label**, which both sides of the equality read, so it was
   invariant — **CARD-206's F-302 defect reproduced in this card's own mutant**. Corrected (`M16b`,
   the row's *body*, so the shape stops being silent) it reds the blind-spot arm.

| mutant | what it deletes | arms red |
|---|---|---|
| `M8_DOOR_AXIS_DELETED` | `DOOR_ARMS = ()` — both closures at once; reproduces F-301 | RED |
| `M1_CALLEE_ARM_DELETED` | the callee-identity closure | RED |
| `M2_SPELLING_ARM_DELETED` | the door-spelling closure | RED |
| `M15b_STORAGES_CONFLATED` | the (storage, spelling) keying, both sides | RED, 5 |
| `M3_DOOR_SPELLING_WIDENED` | `("alias","asname")` → `("Constant","value")` | RED |
| `M4_ASYNCFOR_REMOVED` | `AsyncFor` from `BINDERS_READ` (F-303) | RED |
| `M5_NAMEDEXPR_REMOVED` | `NamedExpr` from `BINDERS_READ` (F-303) | RED |
| `M6_ROW_DECLARED_SILENT` | a `DOOR_SHAPES` row's outcome → `()` | RED |
| `M7_MODULE_BOUND_EMPTIED` | the module-axis allowlist | RED |
| `M9/M10_SITES_±1` | `POSITION_SITE_COUNT` 23 → 24 / 22 | RED both |
| `M11_VOCABULARY_RENAMED` | one of the six position names | RED |
| `M12/M13_GUIDE_±1` | the guide-counting `== 7` | RED both |
| `M14_POSITION_LITERALS_NARROWED` | `1` from `POSITION_LITERALS` | RED, 8 |
| `M16b_BLIND_SPOT_NO_LONGER_SILENT` | a blind spot's silence | RED |

**AC-5 re-certified in both directions:** `M9`/`M10` (site count ±1), `M12`/`M13` (guide count ±1) and
`M11` (a renamed vocabulary member) all red. None of the three equalities has become a floor.

### [Figures, each re-derived and its door named]

- **23 derived position sites, 6 position names, 7 guide-counting expressions** — unchanged by this
  card, re-derived through `_page_positions()` and `_counting_expressions()` and asserted as
  equalities. Door: the guard's own analyser.
- **816 calls in the module, all of them syntactic names, 0 door-axis refusals** — derived through a
  **second, independent** walk written inside
  `test_the_door_axis_arms_reach_every_call_and_refuse_none_of_them`, not by re-calling the analyser.
  Both the 816 and the 0 are asserted.
- **51 → 0 refusals** for the one-shared-table vs (storage, spelling) keying — derived through the
  standalone prototype walks `fixe.py`/`fixe2.py`, and the `0` independently asserted in the suite.
  Collisions named: `text`, `line`, `cell_sizes`, `page_spec`.
- **MODULE axis: 23 geometry-door calls in `src/`, 17 in the generator, 6 outside across 4 modules, 1
  of the 6 passing a non-trivial position** (`book_proof.py:767`, a standalone proof document with no
  front matter). Re-derived through this card's own AST census with the slot read from each door's
  signature. **This differs from CARD-206 cycle 2's restatement of "18 of them inside the generator"**
  — my derivation gives **17**. Re-derived rather than restated, as that card's note asked; the delta
  is reported rather than reconciled, because the two censuses may not have counted the same thing.
- **14 of 18 `DOOR_SHAPES` rows fall silent with both arms removed** — asserted as an equality
  (`SILENT_WITHOUT_THE_DOOR_ARMS`), with the other 4 asserted at exactly 4.
- **41 plants / 38 outside both tables / 23 silent** — the independent reviewer's figures, its own.

### [Honest bounds]

1. **Per-assertion attribution is owed.** Every figure here is test-level ANY-RED. The committed
   instrument did not finish; no kill matrix is quoted.
2. **Three of five axes are open by declaration** — MODULE, VALUE, CALL-GRAPH — each with a control
   that fails. Closed: POSITION (on binding occurrences) and DOOR.
3. **The callee-identity arm is scope-insensitive**, over-approximating in the fail-closed direction.
4. **The reviewer's 23 silent shapes: 3 closed, 4 bounded, 16 neither.** The 16 are all VALUE-axis or
   CALL-GRAPH-axis instances of the four mechanisms named above, and the bound carries two
   representatives of each axis rather than all 16 — a choice made for runtime, and a real gap in the
   bound's resolution, not in its direction.
5. **`__set_name__`, metaclass and `type()`-constructed class routes** are still not reachable by a
   line-count-preserving plant. The reviewer approximated them at module level (its X18, X27) and both
   were silent; a genuine in-class-body plant remains unchecked rather than claimed clean.
6. **`len(calls) == 816` and `inside == 17` will red on any future production edit** that adds a call
   or a door call to the generator. That is intended — they are the closure's denominators — but it is
   a maintenance cost this card is imposing, stated rather than discovered later.

### [Gates] impact set, the tripwires, and the guardrails

- **Impact gate:** `make impact-set BASE=$(git merge-base HEAD main)` → **23 test files**;
  `make test-impact` → **2737 passed, 11 skipped, 0 failed, exit 0**. (`PY=` had to be pointed at the
  main checkout's interpreter: this worktree has no `.venv`, and the Makefile's default
  `./.venv/bin/python` gives `make: *** Error 127` here. Worth a line in `tests/README.md` for the next
  card that works in a worktree.)
- **The full suite was NOT run** — CARD-261 is live in the sibling worktree. Every pytest run in this
  worktree used `NONOGRAM_FULL_SUITE_LOCK=/tmp/card262-impl.lock`; the board's own
  `meta/kanban/.full-suite.lock` was never created, read as authority, or modified.
- **G-1 (no production behaviour change): structurally guaranteed, not argued.** The diff against the
  merge-base is **one file, `tests/test_book_export_interior_cover.py`** — `git diff --name-only … --
  src/` is **empty**. The door axis closed with **zero** production change, because the module's 816
  calls are already all syntactic names. The card's step 2 offered "make a door's identity derivable
  where it is used"; it already was.
- **G-2:** `src/nonogram/export/layout.py` untouched (it is inside that empty `src/` diff). The three
  CON-019 byte-identity tripwires ran **unedited**: `tests/test_export_a4_golden.py` +
  `tests/property/test_cli_exports_byte_identity.py` → **66 passed, exit 0**.
- **G-3:** no database was created, dropped, connected to or truncated; `_refuse_unless_test_database`
  untouched; no `DATABASE_URL` was set in this worktree.
- **G-4:** no new dependency; the guard is stdlib `ast` only.
- **G-5:** the one axis that could not be closed was **declared** (axis 5), not accommodated by
  loosening an arm. No arm was weakened: the only arm whose behaviour changed is the one this card
  added, and it was made **stricter** (attributes as well as locals) after the independent plant.
- **G-6:** no timing measurement is reported anywhere in these notes.
- **Commits:** `8bc7671f` (the closure, the tables, F-303, the axis docstring) and `060190c6` (the
  "missed WITHOUT" equality). Explicit pathspecs only; nothing under `meta/` is staged or committed, so
  this card copy is worktree-only by design.

---

### [Implementation landed] `8bc7671f` + `060190c6` — and **zero production change**

One file changed, `tests/test_book_export_interior_cover.py`.
`git diff --name-only merge-base..HEAD -- src/` is **empty**, so G-1 is structurally guaranteed rather
than asserted. The door axis closed without touching production, because the generator's callees were
already all syntactic names — which is itself the finding: the axis was open as a *guard* hole, not as a
live defect.

**Gates run by the implementation:** impact set 23 files → **2737 passed, 11 skipped, 0 failed, exit 0**;
guard file plus its property neighbour **86 passed**; the CON-019 tripwires, unedited, **66 passed**.
I will run the real gate at the cycle boundary.

**AC-3 did its job in the only way that counts: it falsified the author's own closure.** An independent
plant author ran **41 plants, 38 outside both tables, 23 silent** — against a hand-built 18-row table
that passed every one of its own rows. Of the 23: **3 closed, 4 bounded, 16 carded forward**. The three
closed are one family — `self._door = getattr(self, "page_" + _SUFFIX)` then `self._door(...)`, the same
laundered through a helper, and a `__call__` object on an attribute. That is W0 *with the local spelled
as an attribute*, and it re-opened F-301's whole family one storage over.

**The declaration was wrong in one clause, and the block was left as written with the correction beside
it.** The author had declared a callee anchored when *"`Call.func` is an `ast.Attribute`, **or** an
`ast.Name` whose every binding…"*. The clause before the comma **is** the hole: treating every attribute
callee as self-evidently anchored is what let the storage family through. Corrected to *"in its own
storage"*. Leaving the original visible beside the correction is the right call — a pre-code semantics
block that gets quietly edited to match the code is worth nothing.

**51 → 0, which is how the fix was chosen rather than reasoned.** The obvious repair — one shared opaque
table — costs **51 refusals on a module with no defect in it**, because `text = f"..."` and
`draw.text(...)` share a spelling and nothing else (collisions: `text`, `line`, `cell_sizes`,
`page_spec`). Keyed on **(storage, spelling)** with locals and attributes kept apart: **0**.

**A fifth axis was discovered by the plant and is declared, not closed** — the **call-graph** axis: a
position forwarded past a callee the walk resolves *by name* (an alias of a non-door position method, a
callback parameter used as a callee, a `*args` forwarder). This **falsified a sentence already shipped
into both docstrings** — *"fails closed on both the position and the door axis"* — which is true of the
position axis's *binding* closure and false of its *call-graph* resolution. Narrowed, not defended.
Three of five axes are now open by declaration, each with a control that reds if the hole closes.

### The mutant work, with its domain and its incompleteness stated

**Domain: pytest's exit code over a selection — a TEST-LEVEL ANY-RED. Denominator is collected tests,
never assert-node count, and no per-assertion figure is quoted anywhere.** 16/16 ANY-RED across two
rounds; all mutants line-count-preserving, `cp -p` backup, restore in `finally`, `shasum -a 256`
verified byte-identical before and after both rounds, SHIPPED re-run between every mutant at exit 0.

**The committed instrument did not finish and that is reported as incomplete, not papered over.** A
`tests/kill_matrix.py` run (13 mutants, `Pass.RERAISING`, selection = the guard class) produced **no
matrix** before it was stopped; SIGINT was used so the restore `finally` ran, then nine pristine markers
and `git status` were verified. **Per-arm attribution is owed** and is the first thing the review cycle
should ask for.

**Round 1's three "survivors" were all defects in the mutants or the selection, and two of them are this
board's own recent defects reproduced on the author's own instrument:**

| survivor | what was actually wrong | corrected |
|---|---|---|
| M14 | read SURVIVED under **one nodeid** and kills **8 arms** against the whole class — **a scoped negative is unsound here**, so round 1 is quoted for positives only | RED, 8 arms |
| M15 | changed only the **setter**, not the lookup — it *disabled* the arm instead of conflating the storages, i.e. a mutant that tests nothing | `M15b` → RED, 5 arms |
| M16 | changed only a **label**, which *both sides* of the equality read — **CARD-206's F-302 defect reproduced in the author's own mutant** | `M16b` (the body) → RED |

That table is the most useful thing in the hand-back: it is the no-op-mutant trap from
`tests/README.md` caught three times in one run, by the author, on their own work.

### Figures, and one that disagrees with CARD-206

- **816 calls, all syntactic names, 0 door refusals** — derived by a **second, independent** walk inside
  the test rather than by re-calling the analyser. Both asserted.
- **MODULE axis: 23 door calls in `src/`, 17 in the generator, 6 outside, 1 non-trivial**
  (`book_proof.py:767`). **CARD-206 cycle 2 said 18 inside; this says 17.** Re-derived as that card
  asked, delta **reported and not reconciled** — which is the right handling, and mine to settle.
- 23 sites / 6 names / 7 guide expressions unchanged; **14 of 18** rows silent without the arms,
  asserted as an equality so the arms cannot become decoration.
- F-303 closed for **all 8** `BINDERS_READ` members, not the 2 filed, with per-member controls reading
  each shape twice (with the member → READ, without → REFUSED) and V16–V19 giving `AnnAssign`, `For`,
  `AsyncFor` and `NamedExpr` a planted shape each. The two members CARD-206 shipped with no control
  anywhere now have one.

### Bounds the author declared against itself

1. Per-assertion attribution is **owed**; every figure is test-level.
2. Three of five axes open by declaration, each with a failing control.
3. The callee-identity arm is **scope-insensitive** — it over-approximates in the fail-closed direction.
4. The bound carries **2 representatives per open axis, not all 16** silent shapes — a real gap in the
   bound's *resolution*, chosen for runtime cost.
5. `__set_name__` / metaclass / `type()` in-class-body routes are still unreachable by a
   line-count-preserving plant — **unchecked, not clean**.
6. `len(calls) == 816` and `inside == 17` **will red on any future production edit** that adds a call to
   the generator. Intended — they are the closure's denominators — but a maintenance cost imposed on
   every later book card, and stated now rather than discovered then.

### Carded forward rather than patched here

`POSITION_LITERALS` admits `1` and caps nothing, so `1 + 1 + 1 + len(section)` and
`… + len(section) + 1 + 1 + 1 + 1` pass — the author's own pick for "the one I'd fix first", and the
realistic way front matter grows. `module_integers` reads only a top-level `ast.Assign` of a bare int,
so `_HIDDEN_FRONT_MATTER: int = 3`, `= 1 + 2`, an `if`-block constant and `len(_FRONT_MATTER_PAGES)` all
defeat V15. And what counts as an integer at all (`int(3.0)`, `True+True+True`, `ord("\x03")`, `eval`).
**The pre-code VALUE-axis declaration predicted this class before any of it was planted**, which is the
best evidence this card's "declare semantics before code" requirement earns its keep.

### A protocol conflict the agent flagged instead of silently resolving — and it was right, I was wrong

I instructed it to commit its card copy. Its own hard rule forbids committing anything under `meta/`.
**Its rule is the correct one**: the kanban procedure excludes `meta/` from a card's commits precisely so
card and review prose cannot enter the branch they describe, and the orchestrator syncs the worktree's
notes **one way** into `main` instead. It honoured the rule, left the notes in the worktree copy, and
told me about the conflict rather than picking one silently. The notes above are that one-way sync
(the worktree copy was a pure 332-line append to main's 130 — first 130 lines byte-identical, verified
before copying).

---

### [Review cycle 1] 5.7 — **Critical: the door axis is not closed**, and the plainest counterexample uses no dynamic access at all

Report: `meta/review/20261022T100644Z-CARD-262-cycle1.yml`. One Critical, one Important, six minors.
Arithmetic: `10 − 3.0 (F-401) − 1.0 (F-402) − 0.5 (floor cluster) − 0.3 (prose cluster) + 0.5 credit for
measurement discipline = 5.7`. The **+0.5 credit** is unusual and deserved — the owed attribution was
declared rather than papered over, the falsified clause was left visible, the 816 figure came from a
second independent walk, and every reproducible figure reproduced.

**F-401 (Critical).** The third plant author wrote eight line-count-preserving plants; **all eight reach
the real geometry door with a bare literal and are completely silent.** The plainest one uses no dynamic
access whatsoever:

```python
_d = book_page_spec
_d(None, 3 + len(section))          # outcome=()  refusals=0
```

With that planted the whole guard reads `refusals == []`, `len(sites) == 23`, vocabulary identical,
`_bare_literals == []`, `_outcome() == ()` — **every assertion green**. That is CARD-206's F-301 reading
verbatim, on the card that was sliced out to close it. And it is **not vacuous**: run against the real
production function, `_d(None, 3 + len(section))` returns a `PageSpec` byte-equal to
`book_page_spec(None, 5)` with `parity=ODD`, and four of the plants were compiled and executed against a
module whose `page_spec` records its argument — all four called the real door with 5.

**Two fail-open defaults, one axis — and this is the part that matters architecturally:**

1. `opaque` is a **positive** table. The arm skips any binder not in `BINDERS_READ` with a silent
   `continue` — where the *position* axis appends a refusal — and refuses only `if key in opaque`. So a
   callee name with **no** binding occurrence is anchored **by default**, and the corrected clause
   *"every binding occurrence **in its own storage** holds a syntactic Name or Attribute"* is
   **vacuously true** for zero occurrences. The storage fix moved the hole one *quantifier* over, not
   one storage over.
2. The pre-existing "door referenced without being called" arm is keyed `isinstance(node, ast.Attribute)`
   with no `ast.Name` branch — so the **imported** door `book_page_spec` has no such arm while the
   **method** door does. That is the same `isinstance` keying F-301 was originally filed against.

**Silent:** `_d = book_page_spec` · `import … as _bps` (and `("alias","asname")` is *explicitly
whitelisted* in `DOOR_SPELLINGS_READ`) · `_bps2 = book_page_spec` · `setattr(self,"_door",getattr(self,"page_"+_S))`
· a `match`/`case` capture · the same on the named collision spelling `text` · `except … as` ·
`__set_name__` + `setattr`. **Refused (the controls):** `_d = self.page_spec` · `self.__class__._door = getattr(…)`
· `text = getattr(…)` · a `type()`-built class attribute · `__set_name__` with a *spelled* store.

**So the prediction in my brief was falsified in the direction that counts.** I told the reviewer that a
storage-axis plant should be *refused* and that silence should appear only on the value and call-graph
axes. A storage-axis plant went silent → Critical, exactly as the brief specified it would be.

**ADR-0039/R2 is VIOLATED, and that is a rule reading rather than a judgement.** R2: *"a guard's set is
derived from an authority the runtime can enumerate… Where no such authority exists, the guard defaults
to deny: a shape it cannot analyse is a FAILURE, never a silent pass, and the unanalysable sites become
named exemptions under ADR-0039/R3."* A positive table is default-allow. The contract verdict is R2
violated, R1 and R3 **partial**, the other 11 rules hold.

### The eight attacks, answered — and three of them settle open questions

- **The owed per-arm attribution was produced**, not deferred. `Pass.RECORDING`, selection the three
  door-axis nodeids. **Domain in full:** 154 `ast.Assert` nodes (assert-node count, *not* collected
  tests), 3 collected tests, **11 arms reached**, child instrumentation off, SHIPPED 0 FAIL of 11 reached
  at exit 0 re-run between mutants and equal cell-for-cell, ANY-RED. Removing **either** arm reds exactly
  **one** node, `:2610`. **And it caught the trap in the act: pytest exited 0 on both mutants while the
  matrix recorded a FAIL** — a test-level reading of that very run would have published both as
  survivors. Fourteen mutants remain owed and it says so, keeping *deferred* and *owed* apart explicitly.
- **17 vs 18 is settled, and it reconciles in one line.** Counting rule stated first: a door call is one
  `ast.Call` whose callee names a door, nothing in a comment, docstring or string literal. **17 is
  right.** The +1 in CARD-206's figure is neither a comment nor a literal — it is the
  **`def page_spec` at `book_pdf_generator.py:4036`**. 17 calls + 1 definition = CARD-206's 18. So
  `inside == 17` is pinned to the correct number, and the backlog item I wrote about this delta can be
  closed by this reconciliation rather than by a re-count.
- **W3's claim holds and is the cleanest evidence in the hand-back.** `import operator` is **absent**
  from the planted text, the module is only `ast.parse`d, and both refusals are the guard's own, one per
  arm; with `door_arms=()` → 0 refusals. Not the vacuity shape.
- **`(storage, spelling)` creates no hole of its own.** A colliding spelling buys silence for an
  *attribute* but not for a *local* — and the attribute case is silent for F-401's reason, not the
  keying's. The separation is sound in the direction measured.
- **M14's "a scoped negative is unsound here" is sound and was applied consistently** — audited for
  selective use, none found; every figure in the notes is a positive or an in-process measurement.
- **`len(calls) == 816` is the wrong instrument** (F-404): the degenerate "no calls" case it guards is
  already caught four other ways, and it reds on any call added anywhere in ~7,000 lines. `inside == 17`
  **is** the right equality — keep it. The 14-of-18 figure is a label-list equality plus `len(kept)==4`,
  **not a floor**, and AC-5 was verified in both directions against the module (removal → 22 sites,
  addition → 25), which is stronger than the card's own M9/M10.
- **2-of-16 is a bound, not a gesture** — by *mechanism* it is 2 of ~4 value and 2 of 3 call-graph, with
  three uncovered mechanisms measured and behaving exactly as declared. But **`__set_name__`/metaclass/
  `type()` are reachable** with the harness's own `extra`, *contra* the card's note; a genuine
  in-class-body install stays unchecked.
- **F-407 extends M16 into the shipped code:** CARD-206's F-302 label-invariance shape is live in the
  **shipped** assertions, not only in the author's mutant.

**Gates reproduce.** G-1 zero `src/` change verified (`git diff -- src/` empty; one file, 904/43). The
system contract was derived independently and **reproduces exactly** — projection 41 → kept **14**,
dropped 27, with the case-insensitive idiom grep over the ADR *files* selecting ADR-0036/0037/0039 and
ADR-0039/R1–R3 present, so the sanity check passes; **14 of 14 verdict lines given**. CON-019 tripwires
unedited, 66 passed. Impact gate reproduces at 24 files (23 + the reviewer's probe) → 2740 passed, which
is the implementation's 2737 plus three probe tests. **Scope gate: no escalation** — one file, one
component, zero overlap with CARD-261's `Touches`; "small", not "large but in-scope".

**AC-1's "before" cannot be verified from git**, because `meta/` is uncommitted by procedure. The
reviewer stated that rather than scoring it, which is the right call.

### Where this leaves the card

This is the **third occasion the same family has gated across the slice chain** — CARD-206 cycle 2,
CARD-206 cycle 3 at streak 2 (which produced this card), and now CARD-262 cycle 1. To be precise about
the counter, because I mis-escalated a card earlier this week by misreading it: the `family_regression`
streak *within* CARD-262 is **0**, since cycle 1's findings are attributed to the implementation and not
to a previous fix. The signal is not the config counter — it is that **the slice route has not resolved
the family**, which is a different and more serious thing.

The reviewer's framing of the decision is the right one: **axis 2 is CLOSED or DECLARED, and those are
the only honest options.** Inverting the arm to default-deny is a genuine closure but will refuse
parameters, builtins and imported functions, so its cost must be *measured* on this module first — the
51→0 work is the precedent for how. If DECLARED instead, the silent class needs a named ADR-0039/R3
exemption whose control asserts the three plainest plants **silent** in `MEASURED_BLIND_SPOTS`, and both
docstrings' *"Closed"* must become *"closed on callees with a spelled binding occurrence"*. Either way
**the `ast.Name` branch belongs in the referenced-without-called arm** — `_d = book_page_spec` is a
two-line real-world shape, not an exotic one.
