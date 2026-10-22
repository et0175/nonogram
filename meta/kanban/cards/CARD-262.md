# CARD-262: The page-position guard's door axis is open; close it or name every exemption with a control

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/262-close-the-door-axis
**Worktree:** —
**Source:** CARD-206's **family-regression escalation** at cycle 3/3 (streak 2, 2026-10-22). Owner chose **slice**: the guard is not CARD-206's work, so CARD-206 merged its blank title page with the claim narrowed and the door axis declared an exemption, and this card takes the mechanism.
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** tests/test_book_export_interior_cover.py, src/nonogram/admin/book_pdf_generator.py
**Review score:** —
**Started:** —
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

## Worktree notes

- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`, reading the ADR files **case-insensitively** for the reach-limit idiom. Sanity check: `Touches` includes `tests/**` and `src/nonogram/**`, so ADR-0039 must be in the kept set — if it is not, the derivation is broken, not the scope.
- **[Why this is `architectural` and estimated 1d, not `trivial`]** The diff will be small. Three attempts have already been small. The owner's wave-50 rule floors a claim card at 0.75d and forbids `trivial`; this one is cut at **1d** and `architectural` because its deliverable is a **decided semantics**, and because `Complexity: architectural` is what makes the pipeline read the ADRs in full and demand a declared failure matrix before code — the exact discipline whose absence escalated CARD-206.
- **[Read CARD-206 before writing anything]** Its `[Review 1/3]`, `[Fix 1]`, `[Review 2/3]`, `[Fix 2]` and `[Review 3/3]` notes are the measured history of three failures and one strong partial success. In particular: what the closures *are*, which shapes they catch that nobody wrote branches for, the exemption-as-single-parameter pattern, and the two "fails closed" sentences that were narrowed at the slice.
- **[CARD-206 shipped one uncertified edit, and this card inherits the consequence]** The narrowing (commit `3dd1d11d`) was made after cycle 3, so **no review cycle has seen it**. It is a narrowing plus a declared exemption, so there is less to control than before — but its wording is the thing this card either makes true or replaces, and cycle 1's review here should read it with that in mind.
- **[Use CARD-260's committed instrument]** `tests/kill_matrix.py`, documented in `tests/README.md` from line 453. Do not write another. Keep deletion mutants **line-count-preserving**, aggregate **any-RED**, target the occurrence inside the arm you mean, and **report the DOMAIN of every per-assertion figure** — and note cycle 3's lesson that a mutant can kill *outside* the assert matrix's domain, in which case both domains are recorded rather than a blank matrix quoted.
- **[A measured bound to inherit, not re-derive]** CARD-206 cycle 2 established that **no module outside the generator computes a front-matter-relative interior position today**: an AST census found 23 `page_spec`/`book_page_spec` calls across 5 modules, 18 of them inside the generator, and of the other five only `book_proof.py:767` passes a non-trivial position — a standalone proof document with no front matter. Re-derive it if you rely on it; do not restate it without re-deriving.
- **[Not attempted by any cycle, recorded as unchecked rather than clean]** `__set_name__`, metaclass and `type()`-constructed class routes into the walk. Cycle 3 declined them because no line-count-preserving plant reaches them without restructuring a class body. If this card's semantics (step 1) say they are in scope, they need a plant that does not pretend to be line-count-preserving.
