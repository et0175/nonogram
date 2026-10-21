# CARD-259: CARD-252's record is written in three places; single-source it and control the pointer

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 0.75d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/259-single-source-the-record
**Worktree:** ../PythonProject4-card-259
**Source:** CARD-257 review cycle 1, F-005 (a second surviving doubling) and the card's own declared residue (`reset_engine()` is 135 lines for a 6-line body)
**Idea:** —
**Wave:** 52 (dispatched 2026-10-21; queued — moved from 51 at wave-51 dispatch: it depends on CARD-260's instrument, and the owner's cap is 2 active cards)
**Depends on:** CARD-257 (merged `b441ba00` — it created the single source this card points at), CARD-260 (**consume its committed instrument; do not build a sixth**)
**Touches:** tests/conftest.py, src/nonogram/db/session.py, tests/test_db_engine_lifecycle.py
**Review score:** —
**Started:** 2026-10-21T22:30:00Z · **Closed:** — · **Actual:** — · **Merge commit:** —
**Blocked by:** —

## Why — CARD-257 retired one doubling and the review found the next one behind it

CARD-257's cut 1 retired a rule that had **no control**: *"the same words in two places"* was itself a
claim, and nothing red if the two copies drifted. It replaced it with AC-2 — an equality over the
mechanism's own parameters, derived from the code. That worked, and its cycle-1 review then found the
same pattern one file over.

**F-005, measured:** `tests/conftest.py:472-478` still carries, verbatim in substance, the step-3
narration CARD-257 cut from `session.py` — *"Deliberate, but not load-bearing, and the earlier reading of
G-3 here was wrong"*, the moved-ahead-of-Alembic measurement, and *"re-measured as cycle-1 review mutant
R7"*. It is uncontrolled, it is review history shipped inside code, and it was absent from CARD-257's
residue list, which is the part worth a card: the residue was written honestly and still did not see it.

**The card's own declared residue is the other half.** `reset_engine()`'s docstring is **135 lines for a
6-line body**. Its `Who calls it and why` and `What is pinned, and what is not` sections are CARD-252's
record, outside CARD-257's three cuts — correctly deferred rather than taken, because taking them would
have made that card a rewrite of another card's record. This is the card that takes them.

So **CARD-252's record exists in three places**: `session.py`'s `reset_engine()` docstring, `conftest.py`'s
step 3, and `tests/test_db_engine_lifecycle.py`'s class docstring opening paragraph. One of those three is
now **load-bearing for a control** (CARD-257 F-004), which is what makes the drift expensive rather than
untidy.

## What to implement

1. **One statement of the convention and its measurement**, in `reset_engine()`'s docstring, with
   `conftest.py` step 3 reduced to what the *caller* needs — the ordering and why step 3 is last — plus a
   pointer. The refutation, the re-measurement and the mutant name are CARD-252's record, not a thing a
   fixture reader needs inline.
2. **Give the pointer a control, the way CARD-257's AC-2 did.** Not a string comparison of docstrings: an
   equality over the mechanism's own parameters, derived from the code, extended to `conftest.py` as a
   third text. CARD-257's control reads the globals from `session.py`'s AST and the spelling heads off the
   compiled patterns; extend the *same* control rather than writing a second one.
3. **Word-bound every membership test it adds.** CARD-257's gating finding was that `engine` is a
   substring of `reset_engine`, `_init_engine`, `_engine_url` and `create_engine`, so the arm could not
   fail for that name. Any text check this card adds carries the word boundary and a **per-name** matrix.

## Acceptance criteria

- **AC-1** *Given* the single-sourced record, *then* each clause of CARD-252's record appears **once**,
  and the other two sites carry a pointer. No clause is lost: split the retired copies and show every one
  survives somewhere, as CARD-257's AC-1 did.
- **AC-2** (the control) *Given* the three texts, *then* one test holds that all three agree on the
  mechanism's parameters, **derived from the code**, with every membership test word-bounded and a
  **per-name, per-text** kill matrix — three names × three texts, not one mutant that happens to pick a
  name without the hazard.
- **AC-3** *Given* the cuts, *then* `tests/test_db_engine_lifecycle.py`'s per-assert kill matrices are
  unchanged for every arm, measured with the line-count-preserving instrument and **any-RED aggregation**.
- **AC-4** (guard) *Given* all cuts, *then* the tree sweep is unchanged — 9 sites, 6 pairs, dict-equal,
  zero matches elsewhere — and `session.py`'s docstring-stripped AST hashes to **exactly what it hashes to
  at this branch's merge-base**, proving the `session.py` edit is docstring-only rather than asserting it.
  **Derive the expected value; do not trust a literal on this card.** Compute it as
  `git merge-base HEAD main` → that revision's `src/nonogram/db/session.py` → `ast.parse` → drop the
  leading string `Expr` of every `Module`/`ClassDef`/`FunctionDef`/`AsyncFunctionDef` (substituting `Pass`
  for a body that empties) → `ast.dump` → SHA-256 of the dump, and record the dump length beside it.

  **This card shipped a stale pin and it was caught at dispatch, not by the suite.** It read
  `bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c` (dump length 9154) and called it
  "byte-identical to main's". That value is **correct for `b441ba00`** (CARD-257's merge, where the card was
  cut) and the method above reproduces it there exactly — which is what establishes the method rather than
  the number. But **CARD-258 then changed `session.py`'s code**, and at `4584caf4` and at main the value is
  `49978874aa80a43a851d2146473dcf342b18c8884d8b854fb2366ba1477fbf49`, **dump length 9487**. Asserted
  against main as written, AC-4 would have red on the card's first commit, for a reason that has nothing to
  do with the card. This is the wave-48 figure rule in its purest form: *a figure committed to a card is a
  claim, and its control is recomputation* — no mutant catches a stale number.

## Guardrails

- G-1: **No mechanism change.** Docstrings and comments only, plus the one extended control.
- G-2: No clause retired without a named surviving statement.
- G-3: `nonogram_poc` is never created, dropped, connected to or truncated; `_refuse_unless_test_database`
  is neither widened nor bypassed.
- G-4: No new runtime dependency (ADR-0006/R1), stdlib only.
- G-5: ADR-0036/R4 — no codepoint in U+25A0..U+25FF, U+2022 or U+2219 in any `src/nonogram/**` string
  literal, docstrings included. `pdf_generator.py`'s three U+2022 are the declared exemption; a clean-scan
  claim over the whole tree would be false.

## System contract

_Re-derived at dispatch (2026-10-21) by `system_rules.py --card CARD-259 --root meta/architecture`
(`card_scope: touches`), curated under `meta/kanban/curation.md`: **projection 29 → kept 10,
dropped 19**. A projection — fix the source artifact, never this list._

**Derivation, so a later reader can reproduce it:** keep every `check.kind: review-lens` rule (nothing
executes them, so a reviewer is the only enforcement), plus every `kind: test` rule belonging to an ADR
whose text declares a reach limit — the idiom *"reach, stated rather than implied"*, matched **in the ADR
files and case-insensitively**, because the lens output carries no comment text and ADR-0039 writes it in
capitals. That selects **ADR-0036, ADR-0037, ADR-0039**. The remaining 19 `kind: test` rules are
dropped: the suite executes them on every gate, so listing them adds a line a reviewer must read and
changes nothing about whether they hold.

**Sanity check (curation.md's own):** this card's `Touches` includes `tests/**` and `src/nonogram/**`, so ADR-0039 must be in the
kept set — it is (ADR-0039/R1, ADR-0039/R2, ADR-0039/R3). The previous contract on this card did not exist: the card carried a `[System contract]` note asking for exactly this derivation at dispatch, naming the case-insensitive read. That note is now discharged.

**Review-lens — nothing executes these; the reviewer is the control** (5):

- **ADR-0022/R1** — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from one integer.
- **ADR-0038/R6** — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the solution before the puzzle is solved, and any public phase reopens this ADR (CON-021).
- **ADR-0038/R7** — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra.
- **ADR-0038/R8** — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. Once a CI pipeline exists, it installs Chromium (playwright install chromium) before running them; until then there is no CI, and that is a known gap, not a met clause.
- **CON-021** — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No other surface — the CLI, the web UI, or any public or hosted page — offers an interactive or playable puzzle. Play state is never persisted on the server: no progress, marks, error count, score or solve time is written to a database, file or server, no network request is made per mark, and no user account exists for playing (CON-017). The one place play state may be kept is the browser's own localStorage, per puzzle, so that a puzzle reopened in that browser resumes where it was; it never leaves that browser. The admin player ships the puzzle's solution grid to the browser to compute the error count and the solved state; this is permitted for the admin panel only, and a public or reader-facing player must not send a puzzle's solution to the browser before the puzzle is solved.

**Reach-limited — the ADR itself states its checks do not reach code written later** (5):

- **ADR-0036/R3** — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same difficulty glyph, and four slightly different dots cannot be fixed once a book is on paper. — check: `test_the_books_own_pages_carry_no_undeclared_round_mark`
- **ADR-0036/R4** — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: the cheapest way to print a difficulty dot is to append a bullet to a header string, and that route bypasses the one drawing site and CON-020's type floor at once. — check: `test_no_module_types_a_round_mark_as_a_character`
- **ADR-0039/R1** — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: caught WITH the set member present, missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage, and must be narrowed to what is measured or deleted. — check: `test_the_control_for_each_spelling_depends_on_the_set`
- **ADR-0039/R2** — A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where no such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE, never a silent pass, and the unanalysable sites become named exemptions under ADR-0039/R3. — check: `test_the_guard_sets_are_derived_and_not_hand_written`
- **ADR-0039/R3** — An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT absorb — caught with the exemption removed, missed with it in place — is held to an equality against the sites that exist today, and records whatever it still cannot see as a measured bound with its own failing control. — check: `test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw`

_Dropped (19), each executed by the suite on every gate: ADR-0006/R1, ADR-0027/R2, CON-005, CON-009, CON-010, CON-011, CON-012, INV-001, INV-002, INV-003, INV-005, INV-006, INV-007, INV-008, INV-009, INV-010, INV-011, INV-012, INV-013._

## Worktree notes

- **[Env]** forge 2026.8.17. No `meta/.skills.yml`, so no `forge.min_version` to compare and no `models:`
  block — agents inherit the session model.
- **[Dispatched]** wave 52, 2026-10-21T22:30:00Z, alongside CARD-206 on the owner's wave-boundary decision.
  Verified disjoint from it on every file, so the two run genuinely in parallel.
- **[Estimate corrected at dispatch: 0.5d → 0.75d, `trivial` → `standard`]** Not a re-scoping — the owner's
  wave-50 estimation rule says *the claim-card floor is 0.75d, and a card whose subject is a claim or a
  measurement may not be estimated `trivial`, whatever its diff size.* This card's subject is a claim
  (prose triplicated in three texts, one copy load-bearing for a control), so the rule applies by its own
  terms. The evidence it was written from is now two waves deep: wave 50's two cards were cut at 0.25d and
  took ~0.8d each, and wave 51's CARD-260 was cut at 0.75d and took **3.3d**. The estimate prices the edit;
  the cost is the certification. 0.75d is the floor, not a prediction.
- **[The stale pin in AC-4 was found at dispatch — see AC-4]** The method reproduces the card's own figure
  exactly at `b441ba00`, which is what proves the method and condemns the number: CARD-258 moved
  `session.py` afterwards. AC-4 now says to derive the value from the merge-base instead of trusting a
  literal.
- **[Do not take timing measurements]** other cards may share this machine.
- **[The trap]** This is the third card in a row to cut prose that was each added to close a real finding.
  The failure mode is cutting a sentence that is the **only** statement of a bound. CARD-257 paid for this
  with a 41-clause survival diff; do the same.
- **[The second trap]** `tests/test_db_engine_lifecycle.py`'s class docstring **opening paragraph is
  load-bearing** — it is the only place all three globals are written out, and the control holds the text
  to names in double backticks, which the scan does not count. CARD-257 F-004 added a clause saying so.
  Do not delete that paragraph as CARD-252 history without moving what the control needs.
- **[Instrument traps, all three paid for already]** aggregate **any-RED**, never last-write-wins (a RED
  from an assert inside a `for` loop is otherwise lost); keep mutants **line-count-preserving**; target the
  occurrence **inside the arm you mean** (identical source lines appear earlier in the file and a
  first-occurrence replacement silently mutates the wrong arm, returning a false all-green); and report the
  **domain** of any per-assertion figure — CARD-256 reported a test count as an assertion count.
- **[Three latents inherited from CARD-257, all measured, none gating there]** This card already takes the
  two texts they live in, so it is their natural home.
  - **L-1** `AUDIT NAME-DEL-BACKTICKED[engine]` — replace only the backticked ```engine``` and keep the bare
    English prose: the names arm stays **PASS** (backticked occurrences 0, whole-word `engine` 10 prod /
    1 guard). The control is per-name-over-the-whole-text, not per-sentence. A **partial reword** of the
    enumeration therefore would not red for `engine`, while `SessionLocal`/`_engine_url` would.
  - **L-2** `AUDIT HEAD-DEL-FIRST[setattr(]` — delete only the first, mechanism-describing occurrence: the
    heads arm stays **PASS** (`setattr(` left 5 prod / 3 guard). Nothing shipped claims an occurrence count,
    which is why it was declared rather than fixed.
  - **L-3** `target in guard` is still a substring test, so an identifier strictly *extending* the dotted
    path (`…reset_engine_pool`) would satisfy it without being a pointer. Measured: **0** such occurrences
    in either text and **0 anywhere under `src/` or `tests/`** — a measured bound, not a finding. **A right
    lookahead closes it and stays PASS on SHIPPED**, and is cheap.
- **[Use CARD-260's committed instrument — owner decision, wave 50 retrospective. Do not write a sixth.]**
  The six traps below are CARD-260's acceptance criteria, each a control that can fail. They are listed here
  only so this card can tell whether the instrument it imports actually carries them:
  (1) deletion mutants must be **line-count-preserving**, or the numbering shifts and every assert reports
  NOT-REACHED; (2) aggregate **ANY-RED** over every execution, never last-write-wins, or a RED from an
  assert inside a `for` loop is lost; (3) **target the occurrence inside the arm you mean** — identical
  source lines appear elsewhere in the file and a first-occurrence replacement silently mutates the wrong
  arm, returning a false all-green (the NAMES-BLIND **message** occurs **five** times, and the whole
  source line `assert names, …` only **four** — see the note below — in
  `test_db_engine_lifecycle.py`); (4) **restore every patched attribute** and re-run SHIPPED all-PASS
  *between* mutants — a leaked patch and a real kill look identical; (5) **a mutant must delete the thing
  as the text shows it** — deleting a literal `.SessionLocal` that neither text contains (both write
  `.<name>` and the arm substitutes a placeholder) returns PASS, and **a no-op mutant and a surviving mutant
  look identical**. And over all of them: **report the DOMAIN of every per-assertion figure** — an
  instrumented-only kill is an attribution a plain run cannot make; a plain-only kill is an observation the
  instrument cannot make, and only the second kind corrupts a figure.
- **[The five-vs-four note, measured by CARD-260]** in `test_db_engine_lifecycle.py` the NAMES-BLIND
  assert's **message** occurs **5** times (`:816, :859, :914, :960, :1087`) but the **whole source line**
  only **4** (`:859, :914, :960, :1087`), because `:816` is `assert built, …` and the rest are
  `assert names, …`. A mutant keyed on the line finds four. CARD-257's arm is `occurrence=2`, at `:859`.
- **[A seventh shape, found by CARD-260 in its own work: a SMALL line shift misattributes, and that is
  worse than a blank reading.]** Its first AC-1 plant deleted **one** line, shifting the asserts from
  `{9,10,11,18,19}` to `{8,9,10,17,18}` — **overlapping** the pristine numbering, so the matrix was
  silently *misattributed* rather than all-NOT-REACHED, and the assertion written to catch it was simply
  false. Only a shift large enough that no moved lineno lands on a pristine one reads as NOT-REACHED.
  **A misattributed cell looks like a measurement; a NOT-REACHED cell looks like a problem.**
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`, reading the ADR files
  **case-insensitively** for the reach-limit idiom. This card is about ADR-0039/R1.
