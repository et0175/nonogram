# CARD-259: CARD-252's record is written in three places; single-source it and control the pointer

**Status:** review
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
**Touches:** tests/conftest.py, src/nonogram/db/session.py, tests/test_db_engine_lifecycle.py, tests/test_kill_matrix.py, tests/README.md, tests/helpers/undefined_table_report.py  _(corrected 2026-10-22 from three files — cycle-1 F-107; `test_kill_matrix.py` and `README.md` were declared `SCOPE+` by the implementer, and `undefined_table_report.py` by fix round 1 — its module docstring names CARD-252 and the derived deny-default fails on a text with no pointer)_
**Review score:** 8.5 (cycle 3/3 — ✓ threshold reached, 0 Critical, 0 Important, certification complete)
**Started:** 2026-10-21T22:18:12Z · **Closed:** — · **Actual:** — · **Merge commit:** —
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

- **AC-1** *(amended 2026-10-22 — see `## Amendment`; the original said "the other two sites")* *Given*
  the single-sourced record, *then* each clause of CARD-252's record appears **once**, and **every other
  text that restates it carries a pointer** — where the set of such texts is **derived, not enumerated by
  this card**. No clause is lost: split the retired copies and show every one survives somewhere, as
  CARD-257's AC-1 did, and **ship the survival table** — a count without names is not evidence (cycle-1
  F-102).
- **AC-2** (the control) *(amended 2026-10-22)* *Given* the derived set of texts, *then* one test holds
  that **every** text in it agrees on the mechanism's parameters, **derived from the code**, with every
  membership test word-bounded and a **per-name, per-text** kill matrix over the whole derived set — not
  one mutant that happens to pick a name without the hazard.
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

- **AC-5** (new, 2026-10-22 — the amendment's own criterion) *Given* the tree, *then* the set of texts the
  control holds is **derived from an authority the runtime can enumerate** and **defaults to deny**: a
  docstring that carries CARD-252's signature and is neither the keeper nor a pointer is a **FAILURE**, and
  a text the derivation cannot analyse is a failure too — never a silent pass. This is ADR-0039/R2
  verbatim, applied to this card's own set. Its control is a **planted fifth text**: add a docstring
  carrying the signature, and the test must red naming it; remove it, and the test must pass. A derivation
  whose plant does not red is the defect this criterion exists to prevent.

## Guardrails

- G-1: **No mechanism change.** Docstrings and comments only, plus the one extended control. *(The
  2026-10-22 amendment widens "the one extended control" to include the derivation AC-5 requires. It is
  still one control, and still the only mechanism this card adds.)*
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
- **[Dispatched]** wave 52, 2026-10-21T22:18:12Z, alongside CARD-206 on the owner's wave-boundary decision.
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

---

## Worktree notes (implementation, 2026-10-22)

### Reading of the card, stated so a reviewer can disagree with it rather than guess

CARD-252's record exists in three texts. AC-1 says each clause appears **once** and *the other two*
sites carry a pointer -- one site keeps the record, two point at it. "What to implement" 1 names the
keeper: **`reset_engine()`'s docstring**. So the record stays there, and `conftest.py`'s step 3 and the
class docstring's opening paragraph were reduced to pointers. `reset_engine()`'s docstring is therefore
**not** shortened by this card; what was removed is the duplication at the other two sites, plus two
clauses that were there a third time and are now absorbed into the keeper (see the survival table).
**Declared bound:** the "135 lines for a 6-line body" residue named in `## Why` is unchanged in length.
No AC asks for it to shrink -- AC-4 asks the opposite, that the `session.py` edit be docstring-only --
and relocating CARD-252's record into a *fourth* text would have recreated the problem. If the board
wanted the keeper trimmed, that is a different card and this note is where to start it.

### AC -> test -> red->green

- **AC-1: test `clause_survival` (card-time, scratch) red->green.** 44 clauses of the retired copies,
  each with a **named** surviving statement, machine-checked by phrase presence in the named file.
  First run: 41/44 (three rows had the wrong line-wrap in the phrase, i.e. the *check* was wrong, not
  the code) -> corrected -> **44/44**. Failing state demonstrated: deleting the R7 clause's only
  surviving statement from `session.py` gives `43/44` and names the lost clause; restored and verified
  (`shasum -a 256` equal, `diff -q` clean).
- **AC-2: test `test_all_three_convention_texts_agree_on_the_mechanisms_parameters` red->green.**
  Red first, before any prose was written, with exactly the right reason:
  `conftest.py's pointer at the call site does not name every global _init_engine() creates
  (['SessionLocal', '_engine_url', 'engine']) as a whole word` / `assert {'engine'} == {...}`. Green
  after `conftest.py`'s pointer was written.
- **AC-3: test `test_ac7_the_four_arm_grid_of_card_257_reproduces` red->green.** Red first on its own
  precondition (`assert set(arms) <= linenos` -- `:859` and `:878` are no longer assert linenos at
  HEAD), green after the four constants were re-derived. CARD-257's grid reproduces cell for cell.
- **AC-4: test `derive_hash` + `independent_sweep` (card-time, scratch) red->green.** The AST half is
  green before and after by construction, so its red is a *planted mechanism change*: `_reset_count
  += 1` -> `+= 2` keeps the dump length at 9487 and moves the digest to `5a26f679...`. The sweep half
  is the standing `test_no_test_file_outside_the_exemption_sets_those_globals`, re-derived here by a
  second implementation.

### AC-2's kill matrix -- three names x three texts, with the DOMAIN of every cell

Every cell deletes the name **as its text shows it**: every whole-word occurrence inside that text's
own docstring span, replaced by `Z`-fill of equal length (line-count-preserving), by explicit 1-based
occurrence over the whole file, applied in descending order.

| name | `prod` (reset_engine's docstring) | `guard` (class docstring) | `conftest` (the new pointer) |
| --- | --- | --- | --- |
| `SessionLocal`  | FAIL @ `:897` | FAIL @ `:897` | FAIL @ `:897` |
| `_engine_url`   | FAIL @ `:897` | FAIL @ `:897` | FAIL @ `:897` |
| `engine`        | FAIL @ `:897` | FAIL @ `:897` | FAIL @ `:897` |

**Domains, stated per column because they are not the same:**
- `prod` and `guard` (6 cells): CARD-260's committed instrument, `Pass.RECORDING`, ANY-RED, child
  instrumentation **off**, denominator **47 `ast.Assert` nodes** (not a collected-test count; the
  selection collects **1** test), SHIPPED `0 FAIL of 4 reached` at pytest exit 0, re-run between
  mutants. Each mutant: `exit 0, 4 reached, 1 FAIL`. Because the recording pass suppresses the raise,
  that reading is an **attribution**, not an observation -- so the same 6 were re-measured under
  `Pass.RERAISING`: same 6 FAIL cells at `:897`, pytest **exit 1** (true propagation, which a plain run
  would also see), the pointer arm `:916` NOT-REACHED as the short-circuit requires. No cell is
  instrumented-only.
- `conftest` (3 cells): **plain-run domain only.** The instrument *refuses by identity* an edit landing
  on `tests/conftest.py` (`_refuse_forbidden_path`, `_FORBIDDEN_PATHS`) because that file carries the
  database guard, so these cells **cannot** be measured by it. Measured by an uninstrumented pytest:
  exit 1, the arm read off pytest's own reported lineno (`:897`) and the assert's own label
  (`conftest.py's pointer at the call site ...`). The control reads the conftest text **first** so that
  the first failing assert *is* this arm -- that ordering is what buys the attribution a plain run
  cannot otherwise give. SHIPPED re-run (exit 0) **between** every mutant; `cp -p` backup in
  `tempfile.mkdtemp()`, restore in `finally`, verified `shasum -a 256` **and** `diff -q`
  (`13152427f87e...` before and after). Occurrence counts deleted: `SessionLocal` 1, `_engine_url` 1,
  `engine` **6**.
- **Honest bound on this column:** a plain run has no per-arm matrix. It gives one first-failing assert,
  so these three cells are attributed by *position in the loop plus the message*, not by the
  instrument. That is the weaker attribution and the stronger observation, and it is the only reading
  available without widening a database guard -- which G-3 forbids outright.

The heads arm's `conftest` cells were measured in the same plain domain and are reported as a bonus,
not as an AC: `HEAD-DEL[setattr(@conftest]` and `HEAD-DEL[.<name>@conftest]` both FAIL @ `:908`, one
occurrence each on disk -- unlike the prod text, where L-2 survives because there are six.

### AC-3 -- the file's arms are unchanged, arm for arm and not address for address

`test_ac7_the_four_arm_grid_of_card_257_reproduces` passes: six `DOC-NAME-DEL` cells RED at the names
arm, four `DOC-HEAD-DEL` RED at the heads arm, `NAMES-BLIND` RED at the preamble with the three arms
below it NOT-REACHED, `POINTER-ROT` and `POINTER-DEL-WORD` RED at the pointer arm,
`CONTROLS-RENAME-ONLY` PASS, SHIPPED all-PASS. Domain: committed instrument, `Pass.RECORDING`, ANY-RED,
14 mutants, line-count-preserving, each scoped to its own docstring span by occurrence.

The **addresses** moved and the **grid** did not:

| arm | at the merge-base | at HEAD |
| --- | --- | --- |
| preamble | `:859` | `:877` |
| names | `:878` | `:897` |
| heads | `:889` | `:908` |
| pointer | `:897` | `:916` |

The two loop arms now execute **three** times per run instead of two, so each `DOC-NAME-DEL` cell is
one RED among three outcomes -- ANY-RED is doing more work than before, not less.

### SCOPE+

- **`SCOPE+ tests/test_kill_matrix.py`** -- CARD-260's two anchors index `test_db_engine_lifecycle.py`
  by **absolute line number** held in module-level literals (`NAMES_BLIND_OCCURRENCES`,
  `PREAMBLE/NAMES/HEADS/POINTER`) and by the anchored test's **name** (`FOUR_ARM`). Any edit inside
  this card's `Touches` moves them, so they are updated **in the same commit as the file they index**:
  `NAMES_BLIND_OCCURRENCES (816, 859, 914, 960, 1087) -> (818, 877, 935, 981, 1108)`, the arms as
  tabled above, `NAMES_BLIND_ARM_OCCURRENCE` unchanged at **2**, the two counts unchanged at **5**
  (message) and **4** (whole source line), and `FOUR_ARM`'s selection renamed. All re-derived from
  HEAD's own parse, not guessed. No mechanism in that file was changed.
- **`SCOPE+ tests/README.md`** -- line 644 recites the same four addresses. Leaving them is the stale-pin
  failure this card's own AC-4 was cut from, so they are updated with the grid-not-address distinction
  stated beside them.

### Finding about CARD-260's deliverable (recorded, not reimplemented around)

All six traps the card lists **are** carried by the instrument I imported, each with a control that can
fail, and one is carried further than the card states:

1. line-count-preserving: `test_ac1_a_line_count_shifting_mutant_is_refused`, with the planted positive
   `test_ac1_the_planted_shifting_mutant_runs_green_and_reports_nothing`. And the **seventh shape** the
   card describes (a small, overlapping shift that misattributes) is closed structurally, not by line
   count: the target's assert **topology** is re-derived from disk after every mutant, so a moved,
   swapped or merged assert is refused (`test_ac1_an_equal_line_count_edit_that_moves_an_assert_is_refused`,
   `..._two_asserts_swapped_are_refused_though_the_linenos_are_identical`,
   `..._merges_two_asserts_onto_one_line_is_refused`).
2. ANY-RED: `test_ac2_any_red_and_last_write_wins_disagree_where_it_matters` plus a real two-iteration run.
3. the occurrence inside the arm you mean: `test_ac5_the_five_occurrence_case_from_the_wild_...`,
   `test_ac5_an_explicit_occurrence_hits_exactly_that_lineno` (parametrized over all five).
4. restore + SHIPPED between mutants: `test_ac4_two_sequential_mutants_each_see_a_clean_shipped`,
   `test_ac4_a_leaked_patch_is_caught_by_the_shipped_re_run_between_mutants`, and the five
   restore-verification arms.
5. a no-op mutant: `test_ac5_a_no_op_mutant_is_refused`.
6. the DOMAIN of every figure: `test_ac6_every_figure_this_instrument_prints_carries_its_pass` and three more.

**F-1 (finding, worth a card):** the instrument refuses a *mutant* that shifts a lineno and re-derives
its topology from disk -- but **its own anchors do neither.** `test_ac7`'s precondition is
`assert set(arms) <= linenos`, a **membership** test: it is satisfied by *any* four assert linenos in
the file, so it certifies that the four constants are asserts, never that they are *those four arms*.
What made this card's shift read loudly rather than as a misattribution is the shift's **size**, not
the check: measured, `:859` and `:878` are no longer assert linenos at HEAD, which is what red.
`:897`, however, **is** -- it was the pointer arm at the merge-base and is the names arm now, which is
precisely the overlapping-shift misattribution CARD-260 recorded as its seventh shape, standing inside
its own anchor. **Honest bound:** I did not construct a shift that lands all four old addresses on
other asserts, so the misattribution is *undemonstrated here* -- what is measured is that the check
cannot tell one apart. I did not redesign the anchor (the dispatch brief says to record rather than
reimplement around); I updated the literals and wrote the grid-not-address distinction into the
anchor's own docstring, where the next agent will read it.

**F-2 (smaller):** running `tests/test_kill_matrix.py` transiently mutates `src/nonogram/db/session.py`
and `tests/test_db_engine_lifecycle.py` on disk (it is its own second anchor). Any digest of those files
read **while that file's suite is running** is meaningless. I hit this: a `shasum` taken mid-run read
`0fd37d9d...` where the pristine file is `03a882c7...`, and the docstring-stripped AST matched the
merge-base *anyway*, because the mutants in flight were docstring-only -- a reading that looked clean
and was not a reading of the shipped file at all. Every figure below was re-taken after the run exited.

### AC-4, derived -- not one literal trusted, including the brief's

Method, implemented independently of any committed helper: `git merge-base HEAD main` -> that
revision's `src/nonogram/db/session.py` -> `ast.parse` -> drop the leading string `Expr` of every
`Module`/`ClassDef`/`FunctionDef`/`AsyncFunctionDef`, substituting `Pass` for a body that empties ->
`ast.dump` -> SHA-256.

| revision | dump length | SHA-256 |
| --- | --- | --- |
| `b441ba00` (CARD-257's merge, where the card was cut) | **9154** | `bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c` |
| `4584caf4` (CARD-258) | 9487 | `49978874aa80a43a851d2146473dcf342b18c8884d8b854fb2366ba1477fbf49` |
| `main` | 9487 | `49978874...` |
| **`27ca88c7` (`git merge-base HEAD main`)** | **9487** | **`49978874aa80a43a851d2146473dcf342b18c8884d8b854fb2366ba1477fbf49`** |
| **this worktree, after all cuts** | **9487** | **`49978874aa80a43a851d2146473dcf342b18c8884d8b854fb2366ba1477fbf49`** |

So the `session.py` edit is docstring-only: **proved** by recomputation against the merge-base, not
asserted. The method's own control is that it reproduces the card's stale figure *exactly* at
`b441ba00` (9154 / `bdb10905...`), which is what establishes the method rather than the number -- and
condemns the number, since CARD-258 moved the file afterwards. The digest's failing state is measured:
a one-token **mechanism** change (`_reset_count += 1` -> `+= 2`) leaves the dump length at **9487** and
moves the digest to `5a26f679...`, i.e. the length is not the control and the digest is.

**Declared bound -- why this is NOT committed as a test.** A merge-base comparison is **inert after
merge**: once `HEAD` is `main`, `git merge-base HEAD main` is `main` itself and the test compares
`session.py` to itself, green forever whatever anybody does to it. A control that cannot fail after the
commit that adds it is narrative. Hard-coding the digest instead is what this card's AC-4 did, and it
rotted inside two waves. So AC-4's AST half is a **card-time guard**, recorded here with its method and
its failing state; its standing half is the tree sweep below, which has no baseline to rot.

Sweep half of AC-4, re-derived **in a second domain** (a regex-free reimplementation: `str.find` plus a
hand-rolled forward scan, no `re`, no shared helper -- reproducing a figure with its original method
only confirms the method): **6 pairs, 9 sites**, dict-equal to `_EXEMPT_HAND_SET_SITES`, and **zero**
matches in any other file under `tests/` -- including the two files this card edited. The standing
`test_no_test_file_outside_the_exemption_sets_those_globals` agrees.

### The three inherited latents

- **L-1 `NAME-DEL-BACKTICKED[engine]` -- re-measured, left declared, with the reason.** Reproduced
  exactly: the prod text holds whole-word `engine` **12** times of which **2** are backticked, the guard
  text **2** of which **1** is -- so deleting only the backticked ones leaves **10 prod / 1 guard**,
  which is CARD-257's recorded post-mutant figure to the digit. It is **not** closed, and the reason is
  measured rather than preferred: the obvious closure is to require each name *inside double backticks*,
  and with **two** backticked `engine` in the prod text that closure does not close it either -- a
  partial reword still leaves one. A closure that does not close is worse than a declared latent.
- **L-2 `HEAD-DEL-FIRST[setattr(]` -- re-measured, left declared.** `setattr(` occurs **6** times in the
  prod text and **4** in the guard text, so deleting the first leaves 5/3 and the heads arm stays PASS
  -- CARD-257's figure reproduced. Left declared on purpose: the only closure is an **occurrence-count**
  claim, and a count that moves whenever prose is edited is exactly the stale pin AC-4 was cut from.
  Nothing shipped claims an occurrence count. (Measured aside: in the **new** conftest text each head
  occurs exactly **once**, so there a single-head deletion *does* red -- see the heads cells above.)
- **L-3 `target in guard` -- CLOSED, and it stays PASS on SHIPPED.** The pointer arm is now
  `re.search(rf"(?<![A-Za-z0-9_]){re.escape(target)}(?![A-Za-z0-9_])", guard)`. Measured on the shape
  the guard was **not** written from: an identifier that merely extends the dotted path
  (`nonogram.db.session.reset_engine_pool`) satisfies the substring test (`substring=True`) and fails
  the bounded one (`word-bounded=False`), while SHIPPED satisfies both. CARD-257's bound reproduced:
  **0** occurrences of an extending identifier anywhere under `src/` or `tests/`.

### Guardrails

- **G-1 no mechanism change.** `session.py`: docstrings only, proved by AC-4's AST equality.
  `conftest.py`: docstring only (`git diff` touches no statement). `test_db_engine_lifecycle.py`:
  docstrings, plus the one extended control -- a third entry in its `texts` tuple and the L-3 lookahead.
  `test_kill_matrix.py`: four literals, one selection string and prose; no mechanism.
- **G-2 no clause retired without a named surviving statement.** 44/44, with a demonstrated failing state.
- **G-3.** `nonogram_poc` never created, dropped, connected to or truncated; it is not named anywhere in
  this diff. `_refuse_unless_test_database` is untouched -- and so is the instrument's own refusal to
  edit `tests/conftest.py`, which is **why** the third column is a plain-run reading rather than an
  instrumented one. I routed around the guard's *reach*, never around the guard.
- **G-4.** stdlib only (`ast`, `re`, `subprocess`, `shutil`, `tempfile`, `pathlib`). No new dependency;
  the scratch scripts are not committed.
- **G-5 ADR-0036/R4.** `TestDifficultyDots_HasExactlyOneDrawingSite` 29 passed. Independent scan of
  every `str` constant under `src/nonogram/**` for U+25A0..U+25FF / U+2022 / U+2219: the only hits are
  `src/nonogram/admin/pdf_generator.py:321`, three U+2022 -- the **declared exemption**, unchanged. A
  clean-scan claim over the whole tree would be false and is not made.

### Green set (not the full suite -- the orchestrator owns that gate)

`tests/test_kill_matrix.py tests/test_db_engine_lifecycle.py tests/test_db_url_driver.py
tests/test_db_connect_timeout.py tests/test_full_suite_lock.py` -> **189 passed, 2 skipped**. The 2
skips are this file's `db_required` tests with no reachable test database; they skip **green**, so AC-1
and AC-2 of `TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema` are **not** evidence from
this run. Declared, not glossed.

`tests/test_guard_integrity.py tests/test_suite_profile.py` -> **530 passed**: the structural censuses
over the whole test tree (the lateral-import guard among them) are unaffected by any of this. And
`tests/conftest.py`'s own docstring-stripped AST is **equal** to the merge-base's (33624 bytes), so that
file's edit is docstring-only too -- the same proof as AC-4's, run on the second file rather than
claimed from the first.

### Honest bounds, collected

1. The clause survival check is **phrase presence** in a named file. It shows the words survive where
   this card says they do; it does not show the meaning does, and a row whose named home is wrong would
   still pass if the phrase happened to occur there.
2. The `conftest` column is a **plain-run** reading: one first-failing assert, not a per-arm matrix.
   The conftest-first ordering is what makes that assert the arm under test, and that ordering is a
   property of the control, not of the measurement.
3. AC-4's AST half is a card-time proof, inert as a committed test (see above). Its standing half is the
   sweep.
4. F-1's misattribution shape is **undemonstrated here**; what is measured is that the anchor's
   precondition cannot distinguish it.
5. L-1 and L-2 remain open, each with a measured reason why the available closure is not one.
6. `reset_engine()`'s docstring length is unchanged. This card removed the duplication, not the residue.
7. The two `db_required` tests in the edited file did not run.
8. No timing measurement was taken and none is reported anywhere above.
9. `NONOGRAM_FULL_SUITE_LOCK` was redirected to `/tmp/card259-scratch.lock` for every run in this
   worktree; `meta/kanban/.full-suite.lock` was never read, created, modified or deleted.

---

### [Build gate — PASSED] impact-scoped, and the scope is a declared deviation

`d85b48b0` in the worktree, impact set of eight files — the card's three, plus
`test_kill_matrix.py` (edited as `SCOPE+`), `test_full_suite_lock.py` (the guard, because
`tests/README.md` changed), `test_cli.py` (the structural import guard, because `src/` changed),
`test_db_url_driver.py` and `test_db_connect_timeout.py`:

**815 passed, 2 skipped, 0 failed, EXIT=0.**

The 2 skips are this file's `db_required` tests with no reachable test database, which the agent
declared rather than glossed: `TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema`'s
AC-1/AC-2 are **not** evidenced by this gate.

**The scope is a deviation from `config.yml`, and the reason is structural rather than a preference.**
`review.test_scope` reads `full` and has since wave 26 — its only commit. A full-suite gate takes
`meta/kanban/.full-suite.lock`, and CARD-255's guard makes `pytest_configure` **raise
`pytest.UsageError` on a foreign holder** — so a full run taken here would have red every test run
CARD-206's implementation agent made in its own worktree, for the whole ~16.5 minutes. With
`max_concurrent: 2` and `test_scope: full`, those two settings cannot both be honoured while two cards
are live: the first card to reach a gate breaks the other. `cmd-start-review` resolves this explicitly —
impact-scoped runs do not take the lock, and the full suite still runs at the merge gate, which is one of
the two backstops that make the narrowing safe. CARD-260's cycles ran impact-scoped for the same reason
and recorded nothing; this gate records it. **Owner decision owed:** flip `test_scope` to `impact` (making
the practice the policy), or lower `max_concurrent` to 1 so `full` is actually reachable.

---

### [Review 1/3] Score: 6.5 — below threshold 8. 0 Critical, **3 Important (all gating)**

Report: `meta/review/20261021T231000Z-CARD-259-cycle1.yml` (validated by `yaml.safe_load`).
Mutation check (Step 8f) ran its **diagnosis** half — four mutants, each establishing a finding — and
emitted `deferred(cost)` for its certification half, correctly, because gating findings are present.
No full suite (CARD-206 concurrent); every mutated file restored and verified `diff -q` clean and
`shasum -a 256` equal.

**[Family] The family regressed, and it regressed into the card's own subject.** Three of the five
scoring findings are **ADR-0039/R1** — a claim with no control that can fail — on the card whose entire
purpose is retiring exactly such claims. That is sixteen-plus consecutive in this family across four
waves. `review.family_regression: on` fired; see the routing note below for why this is not simply
"one more fix round".

**F-101 (high) — there is a FOURTH text, and the diff's new sentence claims there are three.**
Confirmed independently by the orchestrator before accepting the finding:

- `src/nonogram/db/session.py:288` now reads *"**This docstring is the only statement of that
  convention, of CARD-252's record above, and of the bound below.**"* The middle clause is new in this
  diff and it is **false on disk**.
- `tests/test_db_engine_lifecycle.py`'s **module docstring (lines 1–57)** is a fourth text restating
  CARD-252's record: the defect mechanism ("kept it, pool and all, and connections opened before the
  DROP were handed back out"), the withdrawn AC-3, the precondition-not-the-race bound, and both gate
  signatures.
- **The drift has already happened, and it is a disagreement about what was measured, not a wording
  difference:** the keeper at `session.py:250` says *"Four consecutive **waves** of this board's build
  gates reported failures that reproduced on no second run"*; the fourth text at
  `test_db_engine_lifecycle.py:14` says *"Four consecutive **build gates** on this board"*. A wave
  contains several gates. One of these is wrong and nothing in the tree can say which.
- **Nothing reads the fourth text.** The extended control reads `reset.__doc__` (`:774`),
  `type(self).__doc__` (`:879`), `_rebuild_public_schema.__doc__` (`:881`) and
  `app_session.reset_engine.__doc__` (`:882`) — the three enumerated texts. A fifth copy in the module
  docstring would red nothing.

**F-102 (high) — AC-1's "44/44 clauses survive" cannot be recomputed.** The card says "(see the survival
table)" and no survival table exists; the check was a scratch script. G-2 therefore ships a **count with
no names**. It bites concretely: the retired conftest phrase *"Four consecutive build gates on this board
reported failures that reproduced on no second run"* is **absent** from the named keeper and present
**verbatim** in the module docstring — so whichever file that row named, the row is wrong. This is the
implementer's own declared bound 1 landing on the one retired clause that carries a number, and the
card's own trap at `:154` had said *"CARD-257 paid for this with a 41-clause survival diff; do the same."*

**F-103 (high) — the control's docstring credits a property that does nothing.** It claims the conftest
text "is read **first**, so a mutant on that text reds on the loop's first iteration and names its own
arm". Both halves refuted by execution: swapping the read order line-count-preservingly leaves the AC-2
test **passing at exit 0**, and conftest-first vs conftest-last produce **byte-identical** evidence. The
attribution comes from the assertion's `{label}`, not from the order. So the property the card credits
for the whole conftest column is inert, and the property that actually does the work is never named.

**F-105 (medium) — a figure reported as "reproduced to the digit" was measured at the wrong revision.**
L-1's guard-column figure is the **merge-base**'s: the guard text held 2 whole-word `engine` (1
backticked) at `27ca88c7` and **1 of 1** at HEAD, because this diff cut the sentence that carried the
other. The reviewer's mutant on it **kills**. So L-1's guard half is **closed** and the record says it
survives. The prod half (12, of which 2 backticked → 10) does reproduce.

**What HELD under attack** — recorded because a review that only lists failures is not a measurement:
the extended control itself (all three enumerated texts held to parameters derived from the code, no text
reduced to a quoted literal, both arms killing on the third text); **L-3 genuinely closed** by a
two-sided lookahead; **AC-4 held**, including the judgement that its AST half is inert after merge, with
the tree sweep re-derived in a **third** implementation (6 pairs, 9 sites, dict-equal, zero matches
elsewhere); **every word boundary**, AST-enumerated; **G-1, G-3, G-4 and G-5** all under independent
re-derivation, with ADR-0036/R4 measured at exactly 3 hits in `src/nonogram/**`, all of them
`pdf_generator.py:321`'s declared U+2022 exemption. Scope gate **PASS** (F-107's stale `Touches` costs no
contract rule: `tests/**` still selects ADR-0039, `src/nonogram/**` still selects ADR-0036/R4).

---

## Amendment 2026-10-22 — the set is derived, not enumerated (owner decision)

**The card's premise was wrong by one text, and the fix is not to correct the count.**

Review cycle 1 (6.5) found a **fourth** text restating CARD-252's record —
`tests/test_db_engine_lifecycle.py`'s module docstring, lines 1–57 — which this card's own diff then
contradicted by adding, at `src/nonogram/db/session.py:288`, *"This docstring is the only statement of
that convention, of CARD-252's record above, and of the bound below."* The drift between keeper and
fourth text was **already live and factual**: `session.py:250` says "Four consecutive **waves** of this
board's build gates", the fourth text says "Four consecutive **build gates** on this board". A wave holds
several gates; one is wrong; nothing in the tree says which.

**Two routes were put to the owner: extend the hand-written set from three texts to four, or derive it.
The owner chose to derive it.** The reason is the pattern rather than this instance: CARD-257's residue
was found one file over, which is what created CARD-259; CARD-259's residue has now been found one file
over again. That is three generations of the same discovery, and **a hand-list of four gets a fifth
text.** Enumerating the sites is the defect; it is the same defect ADR-0039/R2 was written for, and
ADR-0039 is in this card's contract.

So AC-1 and AC-2 are amended to speak of a **derived** set, and **AC-5** is added to carry the derivation
itself with a planted-fifth-text control. The title still says "three places" and is left alone
deliberately: it records what the board believed when the card was cut, and the amendment is the
correction. `Touches` is corrected to the five files the work actually spans (cycle-1 F-107); the scope
gate was re-run and no contract rule changes — `tests/**` still selects ADR-0039, `src/nonogram/**` still
selects ADR-0036/R4.

**What this amendment does not do:** it does not license a rewrite of `reset_engine()`'s 135-line
docstring. The implementer's declared bound stands — no AC asks the keeper to shrink, and relocating the
record would create yet another text. Reducing the residue remains a different card.

---

## Worktree notes (fix round 1, 2026-10-22 — answering review cycle 1)

### The owner's amendment, implemented: the set is DERIVED and it denies by default (AC-5)

**The authority** is the file system plus `ast`: every `*.py` under `src/nonogram/` and `tests/`,
enumerated with `Path.rglob` and parsed, and **every** module, class and function docstring collected.
No file is listed. `_CARD_252_AUTHORITY_ROOTS` and `_card_252_record_texts()` in
`tests/test_db_engine_lifecycle.py` are the whole derivation.

**The signature** is the whole-word token `CARD-252` — the record's own card id. A docstring that carries
it must be either the **keeper** or a **pointer**; anything else is a FAILURE naming its path, line and
qualified name.

**The keeper** is derived from the function object, not from a path spelling: `(file, qualname)` of
`app_session.reset_engine`, cross-checked against its live `__doc__` (flattened, because CPython dedents
a docstring at compile time while the AST keeps the literal's indentation — the two are the same prose
and never the same bytes).

**The roles, and which arm holds which text, both derived:**

| role | derived predicate | arms applied | texts at HEAD |
| --- | --- | --- | --- |
| keeper | `(path, qualname)` of the function object | names, heads | 1 |
| convention-stating | names **more than one** of `_global_names_assigned_by("_init_engine")` as a whole word | names, heads, pointer | 3 (incl. the keeper) |
| pointer-only | names at most one | pointer | 8 |

The `>1` threshold *is* the discriminator and it is a **declared bound**: a text naming exactly one global
is read as prose. Measured at HEAD: **3** texts enumerate more than one (the keeper, `conftest.py`'s
pointer, the guard class docstring — the same three the hand-written tuple held, now arrived at by
derivation), **2** name exactly one (both module docstrings, both carrying the pointer), **11** carry the
signature in all.

**What the derivation can see:** every docstring under those two roots, including ones written later,
including a module docstring (which is what cycle 1 found it blind to), and including a file it cannot
parse — which it **fails** on rather than skipping. A root that is not a directory fails it too.

**What it cannot see, stated rather than claimed sound:**
1. **A restatement that never names `CARD-252`.** The signature is one hand-written token; ADR-0039/R2
   asks the *set* to be derived, and it is, but the predicate is not. Measured bound: of every docstring
   under the roots that does **not** name the card, **2** carry a marker of the record
   (`pg_prepared_statements`, "not load-bearing"), and **neither restates a figure or a bound of it** —
   `test_no_server_side_prepared_statement_is_ever_created` *measures* the `pg_prepared_statements` zero
   in its own body rather than quoting it, and `tests/test_web_server.py:1858` uses the words "not
   load-bearing" about CORS. So the residue is zero today **by inspection, not by construction**, and a
   fifth text that avoids the token is invisible. That residue is unbounded in principle.
2. **Anything that is not a docstring under those two roots.** Running code, comments, Markdown, and any
   `*.py` elsewhere in the repo. Measured: **zero** docstrings naming `CARD-252` in any `*.py` outside
   `src/nonogram/` and `tests/`.
3. **Prose agreement.** The arms hold parameters (the globals, the spelling heads, the pointer), never
   meaning. Two texts can satisfy every arm and still disagree — which is exactly how the waves/gates
   drift survived cycle 1, and why the survival table's `figure`/`bound` rows carry a separate
   single-occurrence check.

**The planted-fifth-text control, in both states.** Committed, synthetic, in
`TestCard259_TheDerivedSetOfTextsDeniesByDefault` (planted into a `tmp_path` tree, never into this
repository): a docstring carrying the signature and no pointer is found and named; the *same* docstring
with the pointer added is clean; an identifier that merely extends the dotted path does **not** satisfy
it; an unparseable file and a missing root both fail. And in the **real tree**, as a mutant:

- **planted** — `PLANT-FIFTH-TEXT[tests/db_name.py]`, one line substituted in its module docstring
  (`"""CARD-244 —` → `"""CARD-244, CARD-252 —`, line count preserved): the deny arm at `:1145` reads
  **FAIL** under the instrument, and a plain `pytest` exits **1** with
  `AssertionError: a docstring names CARD-252 and is neither the keeper nor a pointer to
  nonogram.db.session.reset_engine ... /…/tests/db_name.py:1 <module>` — **it names the plant**.
- **removed** — `cp -p` restore, `shasum -a 256` equal (`b024c046…`) and `diff -q` clean: the same
  selection exits **0**.

### F-101 — closed, both halves

**The false uniqueness claim.** `src/nonogram/db/session.py`'s closing paragraph no longer says "the only
statement". It says the keeper holds every **measured figure and declared bound** of the convention and of
CARD-252's record, that every other docstring naming the card carries a pointer back, and that this is
**enforced** — naming the derivation, its authority, its deny-default and the fact that the previous rule
was a hand-written list three cards running found short by one. The claim's control is the derivation
itself plus the plant above.

**Mutants (DELETING the mechanism the claim names, line-count-preserving, instrument, `Pass.RECORDING`,
ANY-RED, SHIPPED re-run between mutants, all restored and verified):**

| mutant | what it deletes | result |
| --- | --- | --- |
| `DERIVE-DEL[signature]` | the signature regex (`CARD-252` → `ZZZZ-999`) | keeper arm `:1090` **FAIL** |
| `DERIVE-DEL[enumeration]` | the file sweep (`rglob("*.py")` → `"*.qy"`) | keeper arm `:1090` **FAIL** |
| `DERIVE-DEL[keeper-signature]` | the card id in `session.py` (9 occurrences) | keeper arm `:1090` **FAIL** |
| `DERIVE-DEL[names-threshold]` | the `>1` role predicate (`> 99`) | keeper-in-texts `:1104` **FAIL**, names/heads NOT-REACHED |
| `POINTER-DEL[undefined_table_report]` | that text's only pointer | deny arm `:1145` **FAIL** |
| `POINTER-DEL-ALL[lifecycle module docstring]` | **both** of its pointer occurrences | deny arm `:1145` **FAIL** |
| `POINTER-DEL[test_ac7]` | that text's only pointer | deny arm `:1145` **FAIL** |
| `PLANT-FIFTH-TEXT[db_name.py]` | nothing — **adds** a fifth text | deny arm `:1145` **FAIL**, naming it |

**A surviving mutant, recorded rather than hidden:** `POINTER-DEL[lifecycle module docstring]` deleting
**one** of that text's two pointer occurrences leaves the deny arm **PASS**, correctly — the text still
carries a pointer. It is the L-2 shape (a mutant must delete the thing as the text shows it, and that text
shows it twice); `POINTER-DEL-ALL` is the mutant that measures the mechanism, and it kills.

**The drifted figure, re-derived from the record rather than chosen between the two strings.**
`meta/kanban/cards/CARD-252.md:30-39` — *"Measured cost, **four consecutive waves**, each a full ~16-minute
suite re-run plus a fresh diagnosis"* — with a four-row table: wave **45** CARD-248's build gate; wave
**46** *the wave smoke test, first run*; wave **47** CARD-251's build gate; wave **48** CARD-247's build
gate. Corroborated independently by `CARD-251.md:612-651` ("the wave-46 smoke test's first run dying on
`FATAL: database … does not exist`") and `CARD-248.md:359` (`uuid.UUID(hex=inf)`).
`meta/kanban/suite-timing.log` does not exist in this worktree and was not used.

**So both shipped sentences were wrong, in different ways** — "four consecutive **waves of this board's
build gates**" over-attributes all four runs to build gates, and "four consecutive **build gates** on this
board" gets the unit wrong as well. The keeper now states the derived figure once: **one failing run in
each of four consecutive waves — 45, 46, 47 and 48 — each failure reproducing on no second run; three of
those four runs were build gates, the fourth was wave 46's smoke test on its first run**, with the
derivation named in the sentence. The module docstring no longer restates it and sends the reader to the
keeper instead.

**The class — every figure the derived texts share.** AST-enumerated every number token (digits and
`zero`…`twelve`, word-bounded) in all **11** derived texts and grouped by token. Only **one** token denotes
the same measurement in two texts, and it is this one. Everything else that co-occurs is coincidental
(`3` as a step number and as `AC-3`; `two` as "two exceptions" and "two spellings"; `nine` as nine helpers
and nine mutants). Each of the keeper's own numeric claims was additionally re-derived against
`CARD-252.md`: `24/24` (`:257`), `pg_prepared_statements` 0 after 40 executions (`:264-265`), OID `2950`
(`:274`) — all reproduce; "nine helpers, ~180 lines of machinery and eleven controls" reproduces against
`CARD-254.md:25`.

### F-102 — closed: the survival table ships, and 44 is withdrawn

**44/44 could not be reproduced** (the script was never committed), so that figure is **withdrawn** rather
than restated. In its place: `_CARD_252_CLAUSE_SURVIVAL` in `tests/test_db_engine_lifecycle.py` — **21
rows**, each `(retired_from, clause, home, surviving_phrase, kind)`, checked by
`TestCard259_TheDerivedSetOfTextsDeniesByDefault::test_every_retired_clause_has_a_named_surviving_statement`.

- **How to recompute it** (written into the constant's own comment): `git diff -U0 <merge-base>..HEAD --
  tests/conftest.py tests/test_db_engine_lifecycle.py`, take the removed docstring lines of the two retired
  texts, join them, split at sentence boundaries and then at `;` and at em-dash-introduced independent
  clauses. That split yields **21** clauses; the count is a product of a stated method, not a remembered
  number, and the test holds a **floor** (`>= 21`) so the table cannot silently shrink.
- **Phrases are compared whitespace-flattened**, which is what broke the predecessor's first run (41/44
  from three wrong line-wraps): a line-wrap is not a drift.
- **`figure` and `bound` rows carry a second check**: the surviving phrase must occur in **exactly one**
  text of the derived set. That is the mechanism that single-sources a measurement, and it is the row that
  caught cycle 1's drift.
- **The reconciled row** (row 13) is the one F-102 named: retired `"Four consecutive build gates on this
  board reported failures that reproduced on no second run, and they are the motive for the card"`, home
  `src/nonogram/db/session.py::reset_engine`, surviving phrase `"one failing run in each of four
  consecutive waves -- 45, 46, 47 and 48"`, kind `figure`. The old phrase is now in **no** text as a
  measurement.
- **Rows checked hardest first, as the brief asked:** of the 21, **9** are `bound`, **3** are `figure`,
  **9** are `narration`. All 12 figure/bound rows hold the exactly-one-text check.

**Mutants:** `TABLE-DEL[figure row 13]` (`waves` → `gates` in the keeper) reds **two** arms —
`row-present :1861` **and** `row-unique :1868`. `TABLE-UNIQ[figure row 13]` (the same phrase pasted into
`undefined_table_report.py`'s module docstring, one line, line count preserved) reds `row-unique :1868`
alone, with `row-present` still PASS — the two arms are independent and neither subsumes the other.

### F-103 — closed: the inert claim is cut, and the real property has a control

The "`It is read **first**`" sentence is **deleted**, with the refutation recorded in its place (swapping
the read order leaves the test passing at exit 0; first-versus-last give byte-identical evidence). The
property that actually carries the uninstrumented reading is now named: **each arm's message interpolates
the failing text's own `label`** — now `path:lineno qualname`, so a plain run names the file *and* the
line. Its control is
`TestEngineLifecycle_TheResetIsAPublishedSeam::test_each_arm_of_the_agreement_names_the_text_it_failed_on`,
which reads the agreement's own AST and reds if an arm's message stops interpolating `label`.

**Mutants** — `LABEL-DEL[names arm]` and `LABEL-DEL[heads arm]`, each turning that arm's f-string message
into a plain string (line count preserved): plain `pytest` **exit 1**, `AssertionError: the arm at :1121
[resp. :1128] does not interpolate the text's own label into its message`, reported at the control's
own assert `:1193`. **Domain: plain run only** —
the instrument *refuses* both, because they alter the text of an assert **in its own target file** and its
topology check reads what each assertion says (`MutantRefused: … moved the target's assert topology …
Substitute what the assertion reads, not the assertion`). That refusal is correct and is a structural
limit on measuring a control whose subject is its own file's assert text.

**The class — every "because X" clause in the new prose.** Swept each new causal claim for a state that
makes it red, and **two of my own were wrong and are corrected**:
1. *"Measured: **zero** extending occurrences in any derived text"* (the F-108 bound) — **false.** There
   is exactly **one**: the illustrative ```.SessionLocalFactory``` in that very docstring. Re-measured and
   reworded to what is true: zero in the **three** texts the heads arm holds, one in the derived set, in a
   text that enumerates no global and so is not held to that arm.
2. *"each failure green on a re-run of the same commit"* — that is wave 45's wording in CARD-252's table,
   not all four rows'. Narrowed to the record's own phrase, "each failure reproducing on no second run".

Claims that survived the sweep, each with the state that reds it: the keeper-is-live-docstring claim
(`DERIVE-DEL[keeper-signature]`), the role predicate (`DERIVE-DEL[names-threshold]`), the word boundary on
the names arm (`NAMES-WB-DEL` → `partial!=all :1797` FAIL), the right boundary on the dotted spelling head
(`HEAD-BOUND-DEL` → `head-bound :1890` FAIL), the deny-default itself (`DENY-MECH-DEL` → **two** arms,
`plant-named :1739` and `extending :1777`, FAIL), the "`(` cannot continue an identifier" claim about
`setattr(` (the `head-call :1894` arm), and the unparseable-file deny (`PARSE-DENY-DEL`, below).

### F-104 — closed (medium)

The "nine mutants" sentence is narrowed to what is committed and what is not: one mutant per name per text
over the texts the names arm holds (three names over three texts today, so nine), of which the **six** on
`src/nonogram/db/session.py` and on `tests/test_db_engine_lifecycle.py` are held by
`tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces`, and the **three** on
`tests/conftest.py` are held by **no** committed control and structurally cannot be — the instrument
refuses an edit landing on that path **by identity** because it carries the database guard, and G-3 forbids
widening that refusal. The sentence says so, says those three are a card-time plain-`pytest` reading, and
says they are asserted nowhere. The three cells' **domain** is stated in the docstring, not only here.

**The three conftest cells, re-measured at this HEAD** (plain `pytest`, `cp -p` backup in
`tempfile.mkdtemp()`, restore in `finally`, equality asserted byte-for-byte, SHIPPED re-run exit 0 after
each): `DOC-NAME-DEL[SessionLocal@conftest]` 2 occurrences replaced, `DOC-NAME-DEL[_engine_url@conftest]`
1, `DOC-NAME-DEL[engine@conftest]` 6 whole-word occurrences inside that docstring's span. All three:
exit **1** at `:1121` (the names arm), message naming
`…/tests/conftest.py:463 _rebuild_public_schema`. **Honest bound, unchanged from cycle 1:** a plain run
gives one first-failing assert, not a per-arm matrix, so these three cells are attributed by the arm's own
`label` — which is now the property the prose credits, and which has its own control.

### F-105 — closed (medium): the figure was the merge-base's, and the mutant kills

Re-measured in one script over three revisions (word-bounded regex over `ast.get_docstring`, per text):

| text | `27ca88c7` | `d85b48b0` | this HEAD |
| --- | --- | --- | --- |
| prod — whole-word `engine` (of which backticked) | 12 (2) | 12 (2) | **13 (2)** |
| guard — whole-word `engine` (of which backticked) | 2 (1) | **1 (1)** | **1 (1)** |
| conftest — whole-word `engine` (of which backticked) | 7 (1) | 6 (2) | 6 (2) |
| prod / guard / conftest — `setattr(` | 6 / 4 / 0 | 6 / 4 / 1 | 6 / 4 / 1 |

So cycle 1 is right: **2 of which 1 is the merge-base reading**, and the guard text has held **1 of 1**
since `d85b48b0` — the bare occurrence went with the sentence that diff reworded. **L-1's guard half is
therefore CLOSED**, not surviving: deleting the single backticked ```engine``` leaves **zero** and the
names arm reds. The record said the opposite and is corrected. **L-1's prod half genuinely survives**
(13 whole-word, 2 backticked → 11 left), and that is the reason it stays declared. The prod figure moved
12 → 13 in this fix round (my keeper edit added one occurrence) — recorded because a figure is a claim.

**The class — every figure in the implementer's notes, re-measured at this HEAD with the revision named.**
L-1 above. L-2: `setattr(` 6 prod / 4 guard / **1** conftest, so deleting the first leaves 5/3 and the
heads arm stays PASS for the two docstrings while a single deletion in the conftest text *does* red —
unchanged, still declared. L-3: **0** identifiers extending the dotted pointer path anywhere under `src/`
or `tests/`, bound reproduced, and the two-sided lookahead is retained and now also has a committed plant
(`test_a_text_that_extends_the_pointer_does_not_satisfy_it`). AC-4's AST digests: below. The four arm
addresses and `NAMES_BLIND_OCCURRENCES`: re-derived twice in this round from a fresh parse, below.

### F-106 — closed (low)

`tests/README.md` now says the four addresses "are **re-derived by hand and re-committed** at each card
that moves that file — nothing in the suite re-derives them, because the anchor's only check on them is
`set(arms) <= linenos`", and carries the third move with its overlap measurement.

### F-107 — fixed by the orchestrator; `Touches` lists five files. One more is added by this round:
`tests/helpers/undefined_table_report.py` (**`SCOPE+`**) — its module docstring names CARD-252 and had no
pointer, so the derived deny-default fails on it. One sentence added, no mechanism; it is the cheapest
remedy and the alternative (a named ADR-0039/R3 exemption with its own control) costs more than the
sentence it would excuse.

### F-108 — closed in the half that was closable, and the other half declared

The dotted spelling head is now matched with a **right word boundary**, derived from the head rather than
decided per head (`_head_shown_in`: a boundary iff the head ends in an identifier character), so
`.SessionLocalFactory` no longer satisfies `.SessionLocal`; `setattr(` gets none, because `(` cannot
continue an identifier. Both directions have arms (`head-bound :1890`, `head-call :1894`) and
`HEAD-BOUND-DEL` kills the first. **Declared, not closed:** `heads` is still built from
`sorted(names)[0]` alone, so no text is asked to show a `.<other name> =` spelling. Building it from every
name is a different control and a different card.

### AC-3 / AC-4 — re-verified at this HEAD, nothing trusted from the previous round

**AC-4, derived.** `git merge-base HEAD main` = `27ca88c7`. Docstring-stripped AST (`ast.parse` → drop the
leading string `Expr` of every `Module`/`ClassDef`/`FunctionDef`/`AsyncFunctionDef`, `Pass` for a body
that empties → `ast.dump` → SHA-256), implemented independently of any committed helper:

| file | merge-base `27ca88c7` | this worktree | equal |
| --- | --- | --- | --- |
| `src/nonogram/db/session.py` | 9487 / `49978874aa80a43a851d2146473dcf342b18c8884d8b854fb2366ba1477fbf49` | 9487 / `49978874…` | **yes** |
| `tests/conftest.py` | 33624 / `4cfa0b4bf43b12fa1f071aca340e1e0aecf950f9a34bdb9bf53902f4c03535a4` | 33624 / `4cfa0b4b…` | **yes** |

Both reproduce the two values the orchestrator verified independently, so both files' edits in this round
are **docstring-only**, proved rather than asserted. `tests/conftest.py` was in fact not edited at all in
this round. The declared bound stands: a merge-base comparison is inert after merge, so this is a
card-time guard and the standing half is the tree sweep.

**AC-3, with the addresses re-derived twice.** The agreement's four arms moved twice in this round (once
when the control was rewritten, once when two false bound claims were corrected inside its docstring), and
were re-derived from a fresh `ast.parse` **both** times, never adjusted by arithmetic:

| arm | `b441ba00` | `d85b48b0` | this HEAD |
| --- | --- | --- | --- |
| preamble | `:859` | `:877` | **`:1077`** |
| names | `:878` | `:897` | **`:1121`** |
| heads | `:889` | `:908` | **`:1128`** |
| pointer | `:897` | `:916` | **`:1134`** |

`NAMES_BLIND_OCCURRENCES` `(818, 877, 935, 981, 1108)` → **`(961, 1077, 1207, 1253, 1380)`**;
`NAMES_BLIND_ARM_OCCURRENCE` unchanged at **2** (→ `:1077`); the message count **5** and the whole-source-line
count **4** both unchanged; the `:1070`-era literal in `test_ac5_an_explicit_occurrence_hits_exactly_that_lineno`
updated with them. `test_ac7_the_four_arm_grid_of_card_257_reproduces` **passes**: 14 mutants, six
`DOC-NAME-DEL` RED at the names arm, four `DOC-HEAD-DEL` RED at the heads arm, `NAMES-BLIND` RED at the
preamble with the three arms below it NOT-REACHED, `POINTER-ROT` and `POINTER-DEL-WORD` RED at the pointer
arm, `CONTROLS-RENAME-ONLY` PASS, SHIPPED all-PASS. **The grid reproduces cell for cell; only the
addresses moved.**

**The overlap, measured at this HEAD rather than assumed:** of the four `d85b48b0` addresses, `:877`,
`:897` and `:908` are **not** assert linenos here (a stale constant reads loudly) but **`:916` is** — an
unrelated assert in `test_reset_engine_is_public_and_says_who_calls_it`. So a quarter of a stale reading
would have been a silent **misattribution**, which is the seventh shape standing inside the anchor's own
membership precondition. Recorded in the anchor's docstring and in `tests/README.md`, not routed around.

### Kill matrix over my OWN additions — the pass and the domain of every figure

**Domain A — CARD-260's committed instrument**, `Pass.RECORDING`, ANY-RED, child instrumentation **off**,
denominator **76 `ast.Assert` nodes** (not a collected-test count), SHIPPED re-run between mutants, every
file restored and verified with `shasum -a 256` **and** `diff -q`:

- selection = the agreement test (7 arms): SHIPPED **0 FAIL of 7 reached**, pytest exit 0. Eight mutants,
  each killing exactly the arm named in the F-101 table above; one declared survivor
  (`POINTER-DEL[lifecycle module docstring]`, single-occurrence), superseded by `POINTER-DEL-ALL`.
- selection = five of the six AC-5 tests (16 arms): SHIPPED **0 FAIL of 19 reached**, pytest exit 0. Five
  mutants, `DENY-MECH-DEL` 2 FAIL / exit 1, `HEAD-BOUND-DEL` 1 FAIL, `NAMES-WB-DEL` 1 FAIL,
  `TABLE-DEL` 2 FAIL, `TABLE-UNIQ` 1 FAIL.

**Why five of six.** `test_a_file_the_derivation_cannot_analyse_is_a_failure` deliberately drives
`_card_252_record_texts` into its own `assert Path(root).is_dir()` and into its `SyntaxError` branch, so a
matrix over the whole class reads a `FAIL` cell at `:439` in **SHIPPED** and the instrument refuses the run
outright (`LeakedPatch: SHIPPED is not FAIL-free before any mutant`). That refusal is correct — a test
whose subject is a raised `AssertionError` cannot be inside an instrumented SHIPPED baseline — and it is a
**structural limit**, recorded rather than worked around.

**Domain B — plain `pytest`, no instrument** (what the instrument refuses, by identity or by topology).
`cp -p` backup in `tempfile.mkdtemp()`, restore in `finally`, restore asserted byte-for-byte, SHIPPED
re-run exit 0 after each: the three `DOC-NAME-DEL[…@conftest]` cells (refused by identity), both
`LABEL-DEL` mutants (refused by topology), `PLANT-FIFTH-TEXT` (also measured in domain A), and
`PARSE-DENY-DEL`.

**`PARSE-DENY-DEL`, reported as measured and not as intended.** Deleting the `raise AssertionError(…)
from exc` from the `SyntaxError` branch line-count-preservingly leaves `tree` unbound at the next
statement, so the committed test reds with `UnboundLocalError` at `:454` rather than with the silent-pass
it was aimed at: plain `pytest` **exit 1**. It is not a demonstration that a silent skip would be
caught, and it is not reported as one.

**Rule 2 applied, and what it cost:** every mutant above deletes a mechanism the new prose names, not
something the diff added for the mutant's benefit. Two of them (`POINTER-DEL` single-occurrence,
`PARSE-DENY-DEL`) did not land the way the claim predicted, and both readings are above rather than
rewritten.

### Guardrails

- **G-1 no mechanism change.** `session.py`: docstrings only, proved by the AST equality above.
  `conftest.py`: untouched this round (AST equality re-verified anyway). `test_db_engine_lifecycle.py`:
  docstrings, plus **the one control** — now carrying the derivation AC-5 requires, which the amendment
  explicitly widened G-1 to include, plus `TestCard259_TheDerivedSetOfTextsDeniesByDefault` (that
  derivation's own plant) and the survival table AC-1 orders shipped. `test_kill_matrix.py`: five
  literals, one selection string and prose. `tests/helpers/undefined_table_report.py` and
  `tests/README.md`: prose only. **Declared reading of G-1:** AC-1's "ship the survival table" and AC-5's
  derivation are both new test-side mechanism. I read G-1's "one extended control" as the amendment reads
  it — the ACs the owner wrote are what G-1 is widened by — and state it here rather than widening it
  silently. Nothing in `src/` changed except docstring text.
- **G-2 no clause retired without a named surviving statement.** 21 rows, named homes, a committed check,
  a demonstrated failing state, and a floor so the table cannot shrink. 44/44 withdrawn as
  unreproducible.
- **G-3.** `nonogram_poc` is not named anywhere in this diff and was never created, dropped, connected to
  or truncated. `_refuse_unless_test_database` is untouched. The instrument's own refusal to edit
  `tests/conftest.py` is untouched, and is **why** three cells and two mutants are plain-run readings.
- **G-4.** stdlib only (`ast`, `re`, `pathlib`, `shutil`, `subprocess`, `tempfile`). No new dependency; no
  scratch script is committed.
- **G-5 ADR-0036/R4.** Independent AST scan of every `ast.Constant` `str` under `src/nonogram/**`,
  docstrings included, against `set(range(0x25A0, 0x2600)) | {0x2022, 0x2219}`: **3** hits, all
  `src/nonogram/admin/pdf_generator.py:321`, all U+2022 — the declared exemption, unchanged. A clean-scan
  claim over the whole tree would be false and is not made.

### Green set — impact-scoped, not the full suite (CARD-206 is live)

`NONOGRAM_FULL_SUITE_LOCK` was exported to `/tmp/card259-fix.lock` for **every** pytest run in this round;
`meta/kanban/.full-suite.lock` was never read, created, modified or deleted.

### Honest bounds, collected

1. The signature is one hand-written token. A restatement that never names `CARD-252` is invisible,
   and unbounded in principle.
2. The derivation reads **docstrings** under **two roots** only. Comments, running code, Markdown and any
   `*.py` elsewhere are out of reach; measured at zero today.
3. The arms hold **parameters**, never meaning. Two texts can satisfy every arm and still disagree; the
   `figure`/`bound` rows' exactly-one-text check is the only thing that bites on a drifted measurement,
   and it bites only on the phrases the table names.
4. The survival table's clause column is **a mechanical split of the diff's removed lines**, stated so it
   can be recomputed. A different split gives a different row count; **21** is this method's count, and
   44 is withdrawn rather than reconciled.
5. The three `conftest` cells and the two `LABEL-DEL` mutants are **plain-run** readings: one
   first-failing assert, not a per-arm matrix. The arm's own `label` is what attributes them, and that
   property now has a control.
6. `test_a_file_the_derivation_cannot_analyse_is_a_failure` cannot be inside an instrumented SHIPPED
   baseline at all (its subject is a raised `AssertionError`), so its arms are measured only by a plain
   run.
7. `heads` is still derived from `sorted(names)[0]` only (F-108's other half).
8. L-1's **prod** half and L-2 remain open, each with a measured reason.
9. AC-4's AST half is a card-time proof, inert as a committed test; the standing half is the tree sweep.
10. The two `db_required` tests in the edited file did not run (no reachable test database); they skip
    green, so `TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema`'s AC-1/AC-2 are **not**
    evidence from this round.
11. `reset_engine()`'s docstring is **longer** after this round, not shorter. The card's declared residue
    ("135 lines for a 6-line body") is untouched and the amendment says so explicitly.
12. No timing measurement was taken and none is reported anywhere above.

### Every mutant above was re-measured at the FINAL HEAD, not re-labelled

The two false bound claims F-103's class sweep caught were corrected **inside the agreement's own
docstring**, which moved all four arms by **+7** (preamble `:1070` → `:1077`, names `:1114` → `:1121`,
heads `:1121` → `:1128`, pointer `:1127` → `:1134`) and the AC-5 class's arms with them. The first
reading of every mutant was taken at the pre-correction addresses. Rather than add 7 to each cell — which
is the misattribution this board gates on — **the whole matrix was re-run against the final file**, with
every arm lineno re-derived from a fresh `ast.parse` by matching the assertion's own source segment
instead of being written down (`km_final.py`). The cells above are that second reading; the first is
discarded. `NAMES_BLIND_OCCURRENCES` and the four `test_kill_matrix.py` literals were likewise re-derived
after the correction, not adjusted.

### [Build gate — fix round 1, impact-scoped] 945 passed, 16 skipped, 0 failed, EXIT=0

Eleven files: the card's six, plus `tests/test_full_suite_lock.py` (the guard, because `tests/README.md`
changed), `tests/test_cli.py` (the structural import guard, because `src/` changed),
`tests/test_db_url_driver.py`, `tests/test_db_connect_timeout.py`, `tests/test_guard_integrity.py`,
`tests/test_suite_profile.py` (the structural censuses over the whole test tree, because this round adds a
class and a module-level constant), `tests/test_admin_binding.py` (because
`tests/helpers/undefined_table_report.py` changed), `tests/test_card_156_db_fixture.py` and
`tests/test_db_isolation.py`. The 16 skips are `db_required` and browser tests with no reachable test
database; they skip **green**.

**Not the full suite, and the reason is unchanged from the previous gate:** CARD-206 is being implemented
concurrently in its own worktree and was observed running a ~110-file selection during this round. A full
run here takes `meta/kanban/.full-suite.lock` and CARD-255's guard would raise `pytest.UsageError` in that
agent's every run. The owner decision owed on `review.test_scope` (wave-26 `full` versus the practice) is
recorded on the previous gate and is not re-opened here.

### Findings — one line each, with the mutant that proves it. Commit `84fd9ded`.

- **F-101** (high, fixed) — the "only statement" claim narrowed to every *measured figure and declared
  bound* and moved from assertion to **enforcement** by a derived, deny-by-default set; the
  waves-vs-gates drift resolved from `CARD-252.md`'s own cost table and stated once in the keeper —
  `DERIVE-DEL[signature]`, `DERIVE-DEL[enumeration]`, `DERIVE-DEL[keeper-signature]` each red the keeper
  arm `:1090`; `POINTER-DEL[undefined_table_report]`, `POINTER-DEL-ALL[lifecycle module docstring]`,
  `POINTER-DEL[test_ac7]` and `PLANT-FIFTH-TEXT[tests/db_name.py]` each red the deny arm `:1145`.
- **F-102** (high, fixed) — 44/44 withdrawn as unreproducible; a committed 21-row survival table with
  named homes, a stated split method and a shrink floor, plus an exactly-one-text check on every figure
  and bound row — `TABLE-DEL[figure row 13]` reds `row-present :1861` **and** `row-unique :1868`;
  `TABLE-UNIQ[figure row 13]` reds `row-unique :1868` alone.
- **F-103** (high, fixed) — the inert "read **first**" sentence deleted, the per-text `label` named as the
  property that carries the uninstrumented reading, and that property given an AST-reading control —
  `LABEL-DEL[names arm]` and `LABEL-DEL[heads arm]`, plain `pytest` exit 1 at `:1193` naming `:1121` and
  `:1128` respectively (plain domain only: the instrument refuses both by its topology check).
- **F-104** (medium, fixed) — "nine mutants" narrowed to six held by `test_ac7` and three held by nothing
  and structurally unholdable, with the reason and the domain in the docstring — the three re-measured at
  this HEAD by plain `pytest`: exit 1 at `:1121` naming `tests/conftest.py:463 _rebuild_public_schema`,
  with 2 / 1 / 6 occurrences deleted.
- **F-105** (medium, fixed) — confirmed: 2-of-which-1 was the merge-base reading; **L-1's guard half is
  CLOSED** (1 of 1 at HEAD, the mutant kills) and the record is corrected; L-1's prod half survives and
  its figure moved 12 → **13** in this round — re-measured over `27ca88c7`, `d85b48b0` and this HEAD in
  one script.
- **F-106** (low, fixed) — `tests/README.md` now says the four addresses are re-derived **by hand and
  re-committed**, with the third move and its measured overlap (`:916` is still an assert lineno; `:877`,
  `:897`, `:908` are not).
- **F-107** (low, fixed) — closed by the orchestrator; this round adds the sixth file,
  `tests/helpers/undefined_table_report.py` (`SCOPE+`, one prose sentence, because the derived
  deny-default fails on it).
- **F-108** (low, fixed in the closable half, declared in the other) — a right word boundary on the dotted
  spelling head, derived from the head rather than chosen per head — `HEAD-BOUND-DEL` reds `head-bound
  :1890`, with `head-call :1894` holding the other direction; `heads` is still built from
  `sorted(names)[0]` alone and that stays declared.

**None dismissed.** `meta/review/20261021T231000Z-CARD-259-cycle1.yml` carries `status: fixed`,
`fixed_in: '84fd9ded (fix round 1)'` and a `fix_note` for all eight, plus a `fix_rounds:` block; it
validates under `yaml.safe_load`.

---

### [Fix 1] All eight findings fixed. The derivation found texts five through eleven

Commit `84fd9ded` (parent `d85b48b0`), 5 files, +833/−106. Build gate the agent ran: 945 passed,
16 skipped, 0 failed over 11 files. The orchestrator's own re-gate is separate, below.

**The owner's choice to derive rather than extend is now measured, and the margin is large.** The card
was titled *three* places. Cycle 1 found a **fourth**. The derived set finds **eleven**
signature-carrying texts at HEAD — three held to the mechanism's parameters (the same three the
hand-written tuple held, now *arrived at* rather than listed), the rest required to carry a pointer.
Extending the hand-list to four would have missed seven.

One of those is the clearest possible demonstration: **`tests/helpers/undefined_table_report.py` is
CARD-258's file**, its module docstring names CARD-252 twice (`:10-11`), and nothing in this card's
scope, cycle 1's review or the orchestrator's reading had enumerated it. The deny-default failed on it
and the fix added one sentence — *"CARD-252's own record … is kept on `reset_engine()`; this module
restates none of it."* A sixth text, found by the mechanism rather than by a reader.

**AC-5 verified independently by the orchestrator, not accepted on report.** The agent's plant was
`tests/db_name.py`; I planted a different file under the *other* authority root —
`src/nonogram/limits.py`, whose module docstring is unrelated to the database — adding `CARD-252` to
it line-count-preservingly. Result: `test_every_text_that_names_card_252_points_here_and_agrees_on_the_parameters`
**FAILED, naming `limits.py:1 <module>`** by path, lineno and qualname. Restored byte-identical,
`shasum -a 256` equal and `diff -q` clean. The derivation is measured, not declared.

**The resolved figure, and both shipped sentences were wrong.** Derived from `CARD-252.md:30-39` and
its four-row table, corroborated by `CARD-251.md:612-651` and `CARD-248.md:359`: *one failing run in
each of four consecutive waves — 45, 46, 47, 48 — each reproducing on no second run; **three** were
build gates and the fourth was wave 46's **smoke test** on its first run.* So `session.py`'s "four
consecutive **waves** of build gates" over-attributed all four runs, and the module docstring's "four
consecutive **build gates**" had the unit wrong. Stated once now, in the keeper, with the derivation
named. Class swept: every number token in all 11 derived texts was AST-enumerated and grouped, and
this is the **only** token denoting one measurement in two texts.

**G-1 declared rather than widened silently.** AC-1 orders a survival table and AC-5 a derivation; both
are new test-side mechanism. The agent read G-1's "the one extended control" as the amendment reads it
— the owner's ACs are what widened it — and said so on the card instead of quietly broadening the
guardrail. `src/` changed by docstring text only, proved by AST equality (9487 / `49978874…`), and
`tests/conftest.py` was not touched at all this round (33624 / `4cfa0b4b…`). Both re-verified by the
orchestrator against the merge-base.

**Three honest readings reported unrewritten**, which is the standard this card exists to raise:
`POINTER-DEL-ONE` on the module docstring **survives**, correctly, because that text carries the
pointer twice (the L-2 shape) — `POINTER-DEL-ALL` is the mutant that measures the mechanism, and it
kills; `PARSE-DENY-DEL` kills by `UnboundLocalError` rather than by the silent pass it aimed at; and
`test_a_file_the_derivation_cannot_analyse_is_a_failure` **cannot** sit in an instrumented SHIPPED
baseline at all, since its subject is a raised `AssertionError` — a structural limit of the instrument,
recorded rather than worked around.

**The agent corrected two of its own new claims** under F-103's class sweep: "zero extending
occurrences in any derived text" was false (there is exactly one, the illustrative
```.SessionLocalFactory``` in that very docstring), and "each failure green on a re-run of the same
commit" was wave 45's wording only, narrowed to the record's own phrase.

**Every mutant was re-measured at the final HEAD rather than re-labelled.** The two prose corrections
moved all four anchor arms by +7, and instead of adding 7 to each cell the whole matrix was re-run with
each arm's lineno re-derived from a fresh parse by matching the assertion's own source segment. The
anchors moved `:877/:897/:908/:916` → `:1077/:1121/:1128/:1134`, and **`:916` is still an assert
lineno at this HEAD** (an unrelated one in `test_reset_engine_is_public_and_says_who_calls_it`) — so a
quarter of a stale reading would have been a silent misattribution, which is CARD-260's seventh shape
appearing for the second time in two days.

**Still open, each with a measured reason:** L-1's prod half (**10** occurrences left after the backticked
deletion) and L-2 (`setattr(` 6 prod / 4 guard); F-108's other half (`heads` is still built from
`sorted(names)[0]` alone — a different control and a different card); `reset_engine()`'s docstring is
**longer** after this round, and the amendment says explicitly that the residue is not this card's;
and the two `db_required` tests in the edited file did not run, so that AC is not evidenced here.

**One ownership crossing, recorded.** The agent edited the `Touches` header field — orchestrator-owned
— to add `tests/helpers/undefined_table_report.py` with its reason. The content is right and it
declared it, so it is kept rather than reverted; noted because the two-writer rule is what keeps a
card's fields from being overwritten by a stale worktree copy.

---

### [Build gate — fix 1] PASSED, and the selector's fail-closed verdict was overridden on derived evidence

**3326 passed, 16 skipped, 0 failed, EXIT=0** over a 35-file selection at `84fd9ded`. The 16 skips are
`db_required`/browser, green. Run independently of the agent's own 11-file run (945 passed) and
strictly broader than it.

**The selector said `FULL`, and it was right to.** `scripts/impact_set.py --base 27ca88c7` returns
`FULL` for this card, because `tests/conftest.py` is in its `UNANALYSABLE` set and *is* changed against
the merge-base — fix round 0 edited its docstrings. Every test in the suite depends on `conftest.py`,
so the selector refuses to narrow. That is the designed fail-closed behaviour and it fired correctly.

**Why it was narrowed anyway, and on what.** A full suite takes `meta/kanban/.full-suite.lock`, and
CARD-255's guard raises `pytest.UsageError` on a foreign holder — CARD-206's gate and review were live
in another worktree, so a full run here would have red them. The narrowing rests on evidence the
selector cannot see and does not try to: **`tests/conftest.py`'s change is docstring-only, proved by
AST digest equality against the merge-base — 33624 bytes, `4cfa0b4b…`, both sides.** A docstring-only
change to `conftest.py` cannot alter any test's behaviour. So the six remaining changed paths were
handed to the selector instead, and it chose 35 files.

**This is an override of a fail-closed gate and is recorded as one, not smoothed over.** What makes it
legitimate is that the premise is *derived* rather than judged: the AST digests are recomputed, not
asserted. What it costs is that the selector's own refusal no longer appears in this card's evidence
chain — hence this note. The full suite still runs at the merge gate, which is the backstop that makes
any narrowing safe, and `conftest.py` will be inside it.

---

### [Review 2/3] Score: 7.0 — converging by the minimum, and **[Family] FIRES**

Report: `meta/review/20261022T001501Z-CARD-259-cycle2.yml`. 7 findings: 2 high (gating), 1 medium,
4 low. **Every one attributed pre-existing vs fix-induced**, which is what the detector runs on.
6.5 → 7.0 meets `min_improvement: 0.5` **exactly**; the threshold is 8.

**Both gating findings are fix-induced and both are ADR-0039/R1** — the same family as all three of
cycle 1's gating findings. One of them stands *inside the control fix 1 itself wrote*. That is the
"six consecutive gating findings created by the previous fix, two of them inside a control the fix had
just written" pattern, verbatim, in the same file and function family. `review.family_regression: on`
therefore escalates rather than granting a third automatic cycle.

**F-202 (high) — the derivation is WEAKER than the hand-list it replaced, and this is the result of the
round.** Reproduced independently by the orchestrator on `tests/conftest.py`, plain-run domain, the
instrument's `conftest.py` refusal left untouched, Z-fills length-preserving, file restored
byte-identical (`13152427f87e…`, `diff -q` clean):

| mutant | outcome |
|---|---|
| SHIPPED | exit 0 |
| `SessionLocal` Z-filled (one name) | **exit 1 — killed** |
| `SessionLocal` **and** `_engine_url` Z-filled (two names) | **exit 0 — SURVIVED** |

**Deleting more makes the mutant survive.** The role predicate holds a text to the names/heads arms
only when it names **more than one** of `_init_engine`'s globals, so rewording two of the three away
drops the text out of the held set entirely and the arms never see it. At `d85b48b0` the hand-written
tuple held those three texts unconditionally and the same mutant would have killed. The shipped AC-2
matrix is **one name per text**, so every cell sits on the side of the threshold where the arm still
applies — the escape is invisible to it. And `:851-853` tells the reader "reword one of the three away
and that control reds, per name": true for one, silently false for two.

**This is the honest counterweight to the amendment, and it bears on the owner's decision.** Deriving
the set found **seven texts a hand-list of four would have missed** — a real and large win, including
CARD-258's `undefined_table_report.py`, which no reader had enumerated. Deriving it also introduced an
escape the hand-list did not have. Both are true. "Derived beats hand-written" is not unconditional:
a derived set is only as strong as its predicate, and this predicate is gameable by the very edit the
control exists to catch. ADR-0039/R2 says the set must be derived from an authority the runtime can
enumerate — it does not say the *role* assignment may be a threshold over that set.

**F-201 (high) — fix 1 closed a false uniqueness claim by writing two more.** `session.py:294-297` now
says every other docstring "carries a pointer back here rather than restating one", and
`test_db_engine_lifecycle.py:710-713` says the record is "restated in no docstring, this one included".
Both false on disk: the lifecycle **module docstring** still restates four of the five items cycle-1
F-101 itemised — the defect mechanism, **both gate signatures**, AC-3's withdrawal and the
precondition-not-the-race bound. Fix 1 removed only the waves/gates figure. Nothing reds, because the
deny-default asks for pointer **presence** and that docstring carries the pointer twice; the number-token
class sweep is structurally blind to a doubled signature string or a reworded bound.

**F-203 (medium) — the declared residue bound is wrong.** "Zero today by inspection" was re-measured as
**five** marker-carrying docstrings with no `CARD-252` token, one of them a real counterexample:
`TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema` (`:522`, pre-existing and
byte-identical at the merge-base) restates the precondition bound and two `bound` rows. So the bound
this round calls single-sourced stands in **three** texts.

**The root cause is one sentence, and it is the whole escalation:** *the mechanism enforces
pointer-presence while every sentence around it claims non-restatement.*

**What held under attack**, recorded because a review that lists only failures is not a measurement:
the role **split** is exactly as claimed (11 texts, 3 held to the parameters arms, 2 naming one global,
re-derived independently — "the 3 are the 3"); the **survival table is sound** (16 conftest + 5 guard =
21, every clause has a row, no bound-carrying clause dropped, and all 21 rows pass the exactly-one-text
check under an independent re-implementation); the **resolved figure is right** and both retired
sentences were wrong exactly as claimed; `POINTER-DEL-ONE` surviving is a **real reading** (that text
carries the pointer exactly twice); and six of cycle 1's eight findings are **genuinely closed**, each
re-derived.

**The reviewer also corrected fix 1's own honest bound, in the conservative direction.** Fix 1 reported
that `PARSE-DENY-DEL` "kills by `UnboundLocalError`, not by the silent pass it aimed at — the
deny-default has no silent-pass path to delete". Wrong: replacing the raise with a padded `continue`
(1898 lines both sides) reds the committed test with its own message, *"an unparseable file passed
silently, which is the whole shape ADR-0039/R2 forbids"*. The deny-default **does** have a two-sided
control and a deletable silent-pass path; fix 1's mutant was mis-shaped — CARD-260's trap 5 landing on
the card that imports CARD-260's instrument.

**Step 8f's certification half is `deferred(cost)` for the second cycle running.** Cycle 1 deferred it
on gating findings and so did cycle 2, so **the passing cycle still owes it** and this card cannot
merge on a deferred certification.

---

## Worktree notes (fix round 2, 2026-10-22 — answering review cycle 2, the escalated round)

### The route, and what it forbade

`family_regression` fired: both of cycle 2's gating findings were fix-induced and both were
ADR-0039/R1, one of them standing inside the control fix 1 wrote. The owner's chosen route for this
round is mechanical rather than stylistic: **for every claim, comment, docstring sentence and card
note, DELETE or NARROW only — no new claim sentence anywhere**, with one authorised exception, F-202's
mechanism. A fix that adds no claim cannot add a claim with no control, which is the only shape that
has gated this card. Every entry below is a deletion, a narrowing, table data, a corrected number, or
F-202's mechanism.

`NONOGRAM_FULL_SUITE_LOCK` was exported to `/tmp/card259-fix2.lock` for **every** pytest run in this
round; `meta/kanban/.full-suite.lock` was never read, created, modified or deleted. No full suite was
run. No timing measurement was taken and none is reported anywhere below.

### Findings — one line each, with the mutant or the measurement that proves it

- **F-201** (high, fixed) — both false uniqueness sentences narrowed to **pointer presence**, which is
  what the mechanism enforces: `session.py:294-297` drops *"every measured figure and declared bound of
  them is stated here"* and *"rather than restating one"*; `test_db_engine_lifecycle.py:710-713` drops
  *"and restated in no docstring, this one included"*. Then the whole class was swept by grep over the
  HEAD files and over `git diff 27ca88c7..84fd9ded` — see the sweep below — **11 of 12 sites narrowed or
  deleted**, no replacement sentence written. Proof is negative by construction and is reported as such:
  nothing new reds, the pointer each narrowed text must carry is retained in every one of them, and the
  deny arm stays green. The restatements themselves (the module docstring's defect mechanism, both gate
  signatures, AC-3's withdrawal, the precondition bound) are **left on disk** — the route was to bring
  the claims down to the enforcement, not to cut a reader's explanation of the defect out of the file
  that tests it.
- **F-202** (high, fixed) — **the role is no longer read off the text under test.** `stated_in` is
  derived by identity: the keeper off the function object, the `conftest.py` text off conftest's own AST
  call to `session.reset_engine` through a receiver conftest itself binds, and the guard off the class
  that owns the agreement; `texts` is that set **union** the old `>1` sweep, and a floor assert reds if
  the derivation does not reach a text in `stated_in` at all. Three mutants, all plain-run domain
  (the instrument refuses `tests/conftest.py` by identity; **that refusal was not widened** — G-3):
  one-name **KILLED**, **two-name KILLED** (the finding; it survived at exit 0 before), three-name
  **KILLED**, each at the names arm `:1136` naming `tests/conftest.py:463 _rebuild_public_schema`.
  Counterfactual `ROLE-IDENTITY-DEL`: delete the identity half line-count-preservingly and SHIPPED
  stays green while the two-name mutant **SURVIVES again** — caught WITH, missed WITHOUT. The floor has
  its own mutant: `SIG-DEL[conftest]` reds at `:1107`.
- **F-203** (medium, fixed) — the residue **figure is deleted** and the bound left qualitative, because
  re-measurement shows the figure is a function of the marker set and not of the tree: **2** marker
  hits under fix 1's two phrases, **7** under the reviewer's ten markers as the reviewer read them,
  **20** under the same ten with `precondition` as a bare word, **61** with `load-bearing` as a bare
  phrase. The reviewer's substantive half is confirmed, not disputed, and is recorded as what the next
  card takes: `TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema` (`:522`) names CARD-252
  nowhere, carries no pointer, and restates the precondition bound and rows 12 and 14's `bound` clauses
  in its own words.
- **F-204** (low, fixed) — corrected to the recomputation in both places: **9** `bound` / **3** `figure`
  / **9** `narration`, **12** figure-or-bound, on the card and in the cycle-1 YAML's `fix_note`.
  Re-derived by `ast.literal_eval` of the shipped constant at `84fd9ded`; bound rows 1, 2, 3, 7, 11, 12,
  14, 18, 20.
- **F-205** (low, fixed) — **honest bound 7 deleted** and the list renumbered; the `PARSE-DENY-DEL`
  paragraph loses its wrong conclusion and keeps only the measurement it took; the `[Fix 1]` summary
  loses *"because the deny-default has no silent-pass path to delete"*. No replacement describing the
  control was written — the reviewer's `PARSE-DENY-CONTINUE` reading already stands in the cycle-2
  report and in the `[Review 2/3]` note.
- **F-206** (low, fixed) — the false clause **deleted** from `_WORD_BOUNDED`'s comment rather than the
  regex changed, because the regex is defensible and changing it is mechanism. Measured: `CARD-252` is
  followed by a letter or underscore **zero** times and by a digit **zero** times in every `*.py` in
  this worktree, and the derived set is **identical** (the same 11 texts by `(path, qualname)`) under
  either boundary.
- **F-207** (low, fixed) — table data only. The reword-in-place rows now say so in the data
  (`retired_from` reads `conftest-reworded` / `guard-reworded`); there are **six**, not five — row 16 is
  a sixth the report did not name. `retired_from` carries the reword rather than a fourth `kind`,
  deliberately: two of the six are typed `bound` and a `reworded` kind would have taken the
  exactly-one-text check off them. Row **22** is added for the clause fix 1 actually retired from the
  lifecycle module docstring (home `reset_engine`, kind `figure`), the shrink floor moves **21 → 22**,
  and the constant's comment is **narrowed** — *"the removed docstring lines of those two texts"* loses
  *"of those two texts"*, so the stated method reaches every removed docstring line of the two files it
  already names, the third text included.

### The non-restatement claim sweep — enumerated, not remembered

Derived by `grep -nEi "restat|only statement|only place|stated \*{0,2}once|appears once|does not
repeat|no docstring|single source|nowhere"` over the five HEAD files and over
`git diff 27ca88c7..84fd9ded -- src tests`. **12 sites**:

| # | site | claim | disposition |
| --- | --- | --- | --- |
| 1 | `src/nonogram/db/session.py` keeper | "every measured figure and declared bound of them is stated here … rather than restating one" | **narrowed** to pointer presence |
| 2 | `tests/test_db_engine_lifecycle.py` DbCoverage | "restated in no docstring, this one included" | **deleted** |
| 3 | `tests/helpers/undefined_table_report.py` module | "this module restates none of it" | **deleted** |
| 4 | `tests/test_db_engine_lifecycle.py` module, cost | "stated once … This docstring does not restate it" | **narrowed** to a pointer |
| 5 | `tests/test_db_engine_lifecycle.py` module, convention | "is stated **once**, on" | **narrowed** to "is on" |
| 6 | `tests/conftest.py` step 3 | "stated **once** … this docstring does not repeat them" | **narrowed** to "They are on" |
| 7 | `tests/test_db_engine_lifecycle.py` guard | "written **once** … **This class does not repeat it**, and neither does `conftest.py`'s step 3" | **narrowed** to "this class and `conftest.py`'s step 3 … point there" |
| 8 | `tests/test_db_engine_lifecycle.py` guard | "That sentence is the only place this docstring names all three globals" | **kept** — a claim about that docstring's own text, not about the record; measured true (exactly one sentence of it names all three), and it is survival row 20's own surviving phrase |
| 9 | `test_conftest_names_the_seam_at_its_call_site` | "nothing of CARD-252's record is" | **narrowed** |
| 10 | `test_each_arm_of_the_agreement_names_the_text_it_failed_on` | "CARD-252's record itself is not restated here" | **narrowed** |
| 11 | `tests/test_kill_matrix.py` anchor | "CARD-252's record is not restated here" | **narrowed** |
| 12 | `_CARD_252_SIGNATURE`'s comment | "neither restates a figure or a bound of it … the residue is zero today" | **deleted** (F-203) |

Two further sites were read and left because they are the control's own text rather than a claim
about the tree: the survival check's *"must additionally occur in exactly one text of the derived
set"* and its assert's *"a measurement or a bound is stated once"* — both fail when false, which is
what takes them out of this class.

### F-202's three mutants, the counterfactual, and the role split

Whole-word Z-fill of equal length inside `_rebuild_public_schema`'s docstring span, by explicit span
rather than by first occurrence, **line count preserved**; `cp -p` backup in a `tempfile.mkdtemp()`,
restore in a `finally`, restore verified by `shasum -a 256` **and** `diff -q`; SHIPPED (18 passed,
2 skipped, exit 0) re-run **between** every mutant and after the last.

| mutant | names Z-filled (occurrences) | outcome | domain |
| --- | --- | --- | --- |
| SHIPPED | — | exit 0 | plain `pytest`, `tests/test_db_engine_lifecycle.py` |
| `ROLE-SLIP-ONE` | `SessionLocal` (1) | **exit 1, KILLED** at `:1136` | plain run |
| `ROLE-SLIP-TWO` | `SessionLocal`, `_engine_url` (1 + 1) | **exit 1, KILLED** at `:1136` | plain run |
| `ROLE-SLIP-THREE` | all three (1 + 1 + 6) | **exit 1, KILLED** at `:1136` | plain run |
| `SIG-DEL[conftest]` | `CARD-252` (2) | **exit 1, KILLED** at `:1107` (the floor) | plain run |
| `ROLE-IDENTITY-DEL` alone | — | exit 0 (SHIPPED stays green) | plain run |
| `ROLE-IDENTITY-DEL` + `ROLE-SLIP-TWO` | `SessionLocal`, `_engine_url` | **exit 0, SURVIVED** | plain run |

The last two rows are the point: the identity half is **load-bearing**, measured — caught with it,
missed without it. Every failure names `tests/conftest.py:463 _rebuild_public_schema` by path, line and
qualname, which a plain run can read because each arm interpolates the text's own `label`.

**The role split, before and after, by an independent `ast` walk (not the committed helper):**

| | texts | held to the parameters arms | naming exactly one global | pointer-only |
| --- | --- | --- | --- | --- |
| before (`84fd9ded`) | 11 | 3 | 2 | 6 |
| after | 11 | **3** | 2 | 6 |

**No text changes role, so the new predicate reds nothing new.** The identity set is exactly the three
texts the `>1` predicate held today — the keeper, `tests/conftest.py:463 _rebuild_public_schema` and
`TestEngineLifecycle_TheResetIsAPublishedSeam` — which is why the fix buys a kill without buying a red.

**`>= 1` was measured and rejected.** It pulls both module docstrings
(`tests/helpers/undefined_table_report.py:1` and `tests/test_db_engine_lifecycle.py:1`) into the names
**and** heads arms, and each reds on both: they name `engine` once in ordinary prose and show neither
spelling head. That is the "reds something legitimately" case the brief asked to check before adopting
it, so it was not adopted and the arms were not relaxed to accommodate it.

### The prose ledger — docstring line counts, before → after

| text | before | after | Δ |
| --- | --- | --- | --- |
| `src/nonogram/db/session.py::reset_engine` | 159 | 155 | **−4** |
| `tests/conftest.py::_rebuild_public_schema` | 39 | 38 | **−1** |
| `tests/helpers/undefined_table_report.py::<module>` | 73 | 72 | **−1** |
| `tests/test_db_engine_lifecycle.py::<module>` | 61 | 58 | **−3** |
| `…::TestEngineLifecycle_TheDbCoverageDoesNotQuietlyVanish` | 39 | 38 | **−1** |
| `…::TestEngineLifecycle_TheResetIsAPublishedSeam` | 70 | 69 | **−1** |
| `…::test_conftest_names_the_seam_at_its_call_site` | 18 | 18 | 0 |
| `…::test_every_text_…_agrees_on_the_parameters` | 104 | 98 | **−6** |
| `…::test_each_arm_of_the_agreement_names_the_text_it_failed_on` | 13 | 13 | 0 |
| `…::test_a_planted_partial_enumeration_fails_the_names_arm` | 8 | 6 | **−2** |
| `tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces` | 42 | 35 | **−7** |
| **total** | **626** | **600** | **−26** |

Counted separately because they are not docstrings: the `#:` comment blocks lose **6** lines in
`test_db_engine_lifecycle.py` (`_CARD_252_SIGNATURE` 8 → 2; `_WORD_BOUNDED`, the `retired_from`
bullet and the split method all 2 → 2) and **3** in `test_kill_matrix.py` (the `NAMES_BLIND`
move history), and `tests/README.md` loses **6** (5 added, 11 removed).
**Net prose change: −41 lines.** It shrinks, as the route requires. The five code files are
+101/−97 in all, so the +32 of F-202's mechanism and the +8 of survival row 22 are more than paid
for by the prose that came out.

### The anchors, re-derived from a fresh parse rather than adjusted

This round's edits moved `tests/test_db_engine_lifecycle.py`'s arms, so CARD-260's two anchors moved
with them and are updated **in the same commit as the file they index**, as literals only:

| | at `84fd9ded` | at this HEAD |
| --- | --- | --- |
| preamble / names / heads / pointer | `:1077` / `:1121` / `:1128` / `:1134` | **`:1060`** / **`:1136`** / **`:1143`** / **`:1149`** |
| `NAMES_BLIND_OCCURRENCES` | `(961, 1077, 1207, 1253, 1380)` | **`(950, 1060, 1222, 1268, 1395)`** |
| `NAMES_BLIND_ARM_OCCURRENCE` | 2 | 2 (→ `:1060`) |
| message count / whole-source-line count | 5 / 4 | 5 / 4 |

Re-derived by matching each assertion's own source segment in a fresh `ast.parse`, never by arithmetic.
**The overlap, measured at this HEAD rather than assumed:** **none** of the four previous addresses
(`:1077`, `:1121`, `:1128`, `:1134`) is an assert lineno here, so a stale constant would have read
loudly rather than misattributing — the opposite of the third move, where `:916` still was one. That
figure is corrected in the anchor's own docstring and in `tests/README.md`, which recited the old
addresses; the stale `:818` / `:877` figures in two `test_kill_matrix.py` docstrings are corrected to
`:950` / `:1060` with them.

### Guardrails

- **G-1 no mechanism change, beyond the one control.** `session.py`: **docstrings only**, re-verified by
  AST equality — docstring-stripped `ast.dump` is **9487** bytes /
  `49978874aa80a43a851d2146473dcf342b18c8884d8b854fb2366ba1477fbf49`, **equal to the merge-base
  `27ca88c7`** and to the value the orchestrator verified. `tests/conftest.py`: **docstring only** —
  **33624** / `4cfa0b4bf43b12fa1f071aca340e1e0aecf950f9a34bdb9bf53902f4c03535a4`, equal to the
  merge-base. Both recomputed after every edit in this round rather than carried over.
  `test_db_engine_lifecycle.py`: docstrings, the survival table's data, and the one control — F-202's
  role derivation, which this round's route authorises explicitly. `test_kill_matrix.py`: literals and
  prose. `undefined_table_report.py` and `tests/README.md`: prose only.
- **G-2 no clause retired without a named surviving statement.** 22 rows, named homes, the committed
  check green, the floor raised with the table. This round retires no clause of its own: every prose
  edit is a narrowing of a claim, and the only clause-bearing text it touches is covered by row 22,
  which it **adds** rather than removes.
- **G-3.** `nonogram_poc` was never created, dropped, connected to or truncated and is not named in this
  diff. `_refuse_unless_test_database` is untouched. The instrument's own refusal to edit
  `tests/conftest.py` is untouched — which is **why** F-202's five conftest mutants are plain-run
  readings.
- **G-4.** stdlib only (`ast`, `re`, `pathlib`, `shutil`, `subprocess`, `tempfile`, `hashlib`); no
  dependency added, no scratch script committed.
- **G-5 ADR-0036/R4.** Nothing in `src/nonogram/**` changed but docstring text, and no codepoint in
  U+25A0..U+25FF, U+2022 or U+2219 was written; `pdf_generator.py:321`'s three U+2022 remain the
  declared exemption.

### What I wanted to write in the code and did not, because of the rule

1. **A sentence beside `stated_in` saying what it is and why the role is no longer read off the text
   under test.** It is the single most useful thing a next reader could have, and under this round's
   route it is exactly the shape that is forbidden — a new claim sentence. The mechanism is therefore
   readable only from the code and from this note. If a later card is allowed to add prose again, that
   sentence is the first thing to write, together with the `ROLE-IDENTITY-DEL` counterfactual as its
   control.
2. **A pointer sentence in
   `TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema`'s docstring** (`:522`), which is
   F-203's real counterexample: it restates two `bound` clauses and names the card nowhere, so the
   derivation cannot see it. One sentence naming `reset_engine` would have brought it inside. Not
   written: it is a new sentence. Not fixed by widening the signature predicate either, which is a
   mechanism change outside the one this round authorises.
3. **A note in `_CARD_252_SIGNATURE`'s comment recording that the residue figure is marker-set
   dependent** (2 / 7 / 20 / 61 under four readings of the same ten markers). Deleted the figure
   instead and left the bound qualitative; the measurement is above.

### Still open, each with a measured reason, unchanged by this round

L-1's **prod** half (11 whole-word `engine` left after the backticked deletion) and L-2 (`setattr(`
6 prod / 4 guard); F-108's other half (`heads` is still built from `sorted(names)[0]` alone);
`reset_engine()`'s docstring is **155 lines for a 6-line body** — four shorter than fix 1 left it and
still the residue the amendment says is a different card; the two `db_required` tests in the edited
file did not run (no reachable test database, they skip green), so
`TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema`'s AC-1/AC-2 are **not** evidenced by
this round; and F-203's `:522` residue text, recorded above.

---

### [Build gate — fix round 2, impact-scoped] PASSED

`beb3a527` in the worktree. Eleven files — the card's six, plus `tests/test_full_suite_lock.py`
(the guard, because `tests/README.md` changed), `tests/test_cli.py` (the structural import guard,
because `src/` changed), `tests/test_guard_integrity.py` and `tests/test_suite_profile.py` (the
structural censuses over the whole test tree), `tests/test_db_url_driver.py`,
`tests/test_db_connect_timeout.py`, `tests/test_admin_binding.py` (because
`tests/helpers/undefined_table_report.py` changed), `tests/test_card_156_db_fixture.py` and
`tests/test_db_isolation.py`:

**945 passed, 16 skipped, 0 failed, EXIT=0.**

The skips are `db_required`/browser with no reachable test database; they skip **green**, so
`TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema`'s AC-1/AC-2 are **not** evidenced
by this gate. `NONOGRAM_FULL_SUITE_LOCK` pointed at `/tmp/card259-fix2.lock` for every run;
`meta/kanban/.full-suite.lock` was never read, created, modified or deleted; no full suite was run,
for the reason recorded on the two previous gates (CARD-206 is live in its own worktree with its own
review). The counts are read off the progress block rather than off a summary line, and no duration
is recorded.

**Commits:** `3502ecaa` (the seven findings) and `beb3a527` (the sixth reword-in-place row, which
`3502ecaa` relabelled five of).

---

### [Fix 2 — the owner's deletions-only route] All seven closed, none dismissed, and the prose shrank

Commits `3502ecaa` + `beb3a527` (the second adding a **sixth** reword-in-place survival row the first
relabelled only five of). 6 files. Agent's own gate: 945 passed, 16 skipped, 0 failed over 11 files.

**The escalation's root finding is closed, verified by the orchestrator with the same script that found
it, unchanged:**

| | before fix 2 | after |
|---|---|---|
| SHIPPED | exit 0 | exit 0 |
| `SessionLocal` Z-filled (one name) | exit 1 | exit 1 |
| **`SessionLocal` + `_engine_url` (two names)** | **exit 0 — survived** | **exit 1 — killed** |

Restored byte-identical, `diff -q` clean. The role is no longer read off the text under test: `stated_in`
is derived **by identity** — the keeper off the function object, the `conftest.py` text off conftest's
own AST call to `session.reset_engine` through a receiver conftest itself binds, the guard off the class
owning the agreement — and `texts` is that set **∪** the old `>1` sweep, with a floor assert that reds if
the derivation stops reaching one of them.

**The two rows that make the fix load-bearing rather than merely present:** `ROLE-IDENTITY-DEL` alone
leaves SHIPPED green, and `ROLE-IDENTITY-DEL` **+** the two-name slip **survives**. So the defect is
caught *with* the identity half and missed *without* it — the ADR-0039/R1 shape the old predicate
lacked. Every failure names `tests/conftest.py:463 _rebuild_public_schema` by path, line and qualname.
All plain-run domain; the instrument's `conftest.py` refusal was **not** widened (G-3).

**The role split is unchanged — 11 texts / 3 held / 2 naming one global / 6 pointer-only — so the new
predicate reds nothing new.** `>= 1` was measured and **rejected** with its reason: it pulls both module
docstrings into the names *and* heads arms and each reds on both, because they name `engine` once in
ordinary prose and show neither spelling head. Two legitimately pointer-only texts would have red, and
the arms were not relaxed to accommodate it. That is the right way to decline a cheaper fix.

**The deletions-only rule held, and the ledger proves it.** Docstrings **626 → 600 (−26)**, `#:`
comments −9, `tests/README.md` −6 — **net prose −41 lines**, against +32 of F-202 mechanism and +8 for
the new survival row. The non-restatement claim sweep enumerated **12 sites** by grep over HEAD and the
fix-1 diff: 8 narrowed, 3 deleted, **1 kept with a reason** — the guard's *"That sentence is the only
place this docstring names all three globals"*, which is a claim about that docstring's own text rather
than about the record, is measured true, and is survival row 20's own surviving phrase, so deleting it
would have red G-2. Two further sites were read and left because they are the control's own assert text,
which fails when false and so is not in the class.

**F-203 was closed by deleting the figure rather than correcting it, and the reason is the best kind.**
The agent re-measured and found the count is entirely a function of the marker set — **2** under fix 1's
two phrases, **7** under the reviewer's ten markers, **20** with `precondition` as a bare word, **61**
with `load-bearing` as a bare phrase. No figure is reproducible, so no figure is stated; the bound is
left qualitative. The reviewer's substantive half is **confirmed**: `:522` names the card nowhere,
carries no pointer, and restates the precondition bound and rows 12/14's `bound` clauses in its own
words. That text remains the declared residue.

**F-207 found more than the review did:** six reword-in-place rows, not five — row 16 was a sixth the
report had not named — and `retired_from` carries the reword rather than a fourth `kind`, *deliberately*,
because two of the six are typed `bound` and a `reworded` kind would have taken the exactly-one-text
check off them. Row 22 was added for the clause fix 1 actually retired from the lifecycle module
docstring, and the table comment was **narrowed** to reach the third text rather than extended.

**F-206's blast radius was measured before the cheap fix was taken:** `CARD-252` is followed by a letter
or underscore **zero** times and by a digit **zero** times across every `*.py` here, and the derived set
is identical under either boundary — so deleting the false comment clause rather than changing the regex
changes nothing observable, and that was established rather than assumed.

**Anchors re-derived from a fresh parse, and the overlap hazard is gone this time:** arms
`:1077/:1121/:1128/:1134` → `:1060/:1136/:1143/:1149`, `NAMES_BLIND_OCCURRENCES` →
`(950, 1060, 1222, 1268, 1395)`, arm occurrence and both counts unchanged. **None of the four previous
addresses is an assert lineno at this HEAD**, so a stale constant would read loudly rather than
misattribute — the opposite of the shift two rounds ago, and measured rather than hoped.

**Three things the agent wanted to write in the code and did not, because of the rule** — all recorded
here, which is where the rule says they go: a sentence beside `stated_in` explaining why the role is no
longer read off the text under test (*"the most useful thing a next reader could have, and exactly the
forbidden shape"*); a pointer sentence in `:522`'s docstring, which would bring F-203's counterexample
inside the derivation in one line; and a note that the residue figure is marker-set dependent. The first
is the honest cost of the route, and the owner should know the rule bought convergence at the price of
that sentence.

**Owed to cycle 3:** Step 8f's certification half, `deferred(cost)` for two cycles running. The agent
declares nothing half-fixed, and names what a certifying reviewer should still find open: F-203's `:522`
residue text and the three sentences above.

---

### [Build gate — fix 2] PASSED: 3326 passed, 16 skipped, 0 failed, EXIT=0

35-file selection at `beb3a527`, derived by `scripts/impact_set.py` and run independently of the
agent's own 11-file run (945 passed). Same declared override as the fix-1 gate and for the same
reason: the selector returns `FULL` because `tests/conftest.py` is changed against the merge-base, and
the narrowing rests on the recomputed AST-digest equality (33624 / `4cfa0b4b…`) proving that change is
docstring-only. CARD-206's fix round was live in the sibling worktree, so a lock-taking full run would
have red it. The full suite comes at the merge gate.

---

### [Review 3/3] Score: 8.5 — ✓ passes. 0 Critical, 0 Important, 0 Medium, 3 Low. **Certification ran.**

Report: `meta/review/20261022T012116Z-CARD-259-cycle3.yml` (590 lines, `yaml.safe_load` validated).
7.0 → **8.5**, an improvement of 1.5 against `min_improvement: 0.5`, and no gating findings. The loop's
success condition — score ≥ 8 **and** zero surviving critical/important — is met.

**[Family] It does NOT fire, and this is the answer to the question the escalation asked.** The
reviewer enumerated **every added line** of `git diff 84fd9ded..beb3a527` across `src/` and `tests/`
and classified each: the authorised F-202 mechanism, survival-table data, re-derived anchor literals,
narrowings, and **exactly three claim-shaped sentences — each traced to an enforcement the reviewer
then certified** (`:1160`'s deny arm, `:1136`'s names arm, and a planted control in the test's own
body). Not one added sentence is a claim without a control that can fail.

So: two fix rounds out of two each created the next cycle's gating finding **by adding a claim**, and
the round forbidden from adding one created **none**. The owner's deletions-only route worked
mechanically and for exactly the stated reason. That is worth recording as a method, not just as this
card's outcome.

**Certification — complete, after two deferrals.** 20 mutants (15 instrumented across two selections,
5 plain-run), plus the committed anchor's own 14. *Domain A: the committed instrument, `Pass.RECORDING`,
child instrumentation off, ANY-RED, denominator **78 `ast.Assert` nodes** — an assert-node count, not a
collected-test count, each selection collecting one test; SHIPPED all-PASS and re-run between every
mutant, all line-count-preserving, repeated targets addressed by explicit `occurrence`. Domain B: plain
`pytest`, the only domain available for anything landing on `tests/conftest.py`.* Highlights:

| target | mutant | outcome |
|---|---|---|
| the signature | `CARD-252` → `CARD-999` | keeper `:1073` **and** floor `:1107` FAIL |
| the enumeration | `rglob("*.py")` → `"*.qy"` | `:1073` + `:1107` FAIL |
| `stated_in`'s guard leg | stale `type(self).__name__` | **floor `:1107` alone** |
| `stated_in`'s conftest leg | `receivers` → `set()` | **`:1096` alone** |
| the deny-default (AC-5) | plant a fifth text | `:1160` FAIL; **paired with the mechanism deleted → PASS** |
| the identity half (F-202) | two-name slip | **exit 1 killed**, and identity-del + slip **survives** |

**Two-sided (caught-with / missed-without) established for the deny-default and the identity half** —
which is the ADR-0039/R1 shape, not merely a red.

**The reviewer reported a mis-shaped mutant of its own rather than rewriting it:** its first
`NAME-DEL[SessionLocal@prod]` deleted 1 of 2 occurrences and **survived** — CARD-260's trap 5, its own
error, declared; the properly shaped mutant kills. That is the standard this board asks for and rarely
gets.

**All seven of cycle 2's findings are genuinely closed**, each re-derived from the code at `beb3a527`
rather than accepted on report — including F-203's `:522`, verified **byte-identical to the merge-base**
and restating the bound *in its own words*, which is precisely why a verbatim exactly-one-text check
cannot see it. The reviewer also noted the declaration **softens in the card's favour**: `:522` points
at the module docstring, which points at the keeper — a two-hop pointer.

**The one attack that landed, and it is a measurement rather than a defect.** F-302: the union
`identity ∪ >1-sweep` is **redundant** — deleting the sweep half leaves all nine arms PASS, and so does
deleting the identity half, because the two select the same three texts. It is **not** ADR-0039/R1,
because fix 2 deleted the claim that rode on the threshold and no shipped sentence attributes a catch
to it. It is dead weight, not an uncontrolled claim. The cost is real though: a reader cannot tell that
`:1116` carries the kill and `:1117` carries nothing, **so the line most likely to be tidied away is
the load-bearing one.** That is the sharpest consequence of the forbidden sentence.

**Two stale figures in the record, both found by the reviewer and both corrected here** — the same class
as the bookkeeping errors CARD-260 left behind:
- Fix 2's own "still open" note read L-1's prod half as **11**. Recomputed by the orchestrator
  independently: the keeper's docstring holds **12** whole-word `engine` of which **2** are backticked,
  so the figure is **10**. Fix 2's own −4-line keeper trim took one `engine` with it, so the figure
  moved *in the round that declared it unchanged*. The latent itself is genuinely unchanged (10 > 0,
  names arm still PASS) and no shipped text carries the figure. Corrected on the card.
- The cycle-1 YAML's F-102 `fix_note` still said `21` rows, a `>= 21` floor and arms `:1854/:1861`,
  where HEAD is 22, `>= 22` and `:1881/:1888`. Reconciled in place, with both readings kept so the note
  still says what was true when it was written.

**The honest answer on comprehensibility, which the owner should weigh:** the reviewer judges the
mechanism comprehensible without the three forbidden sentences — each of `stated_in`'s three legs is
explained by the assert that guards it — but the **decision** is not. Why the role is no longer read
off the text under test exists only on this card and in the cycle-2 report. F-302 is exactly where that
bites. The route bought convergence; this is its price, and it is one sentence.

**Declared not certified:** the two `db_required` tests skip (no reachable test database), so that
class's AC-1/AC-2 are unevidenced by this cycle as by every previous one; the shrink floor is not
line-count-preservingly mutable and was read-and-verified instead; and the three conftest name cells
have no per-arm matrix in any domain and structurally cannot, because the instrument refuses that file
by identity and G-3 forbids widening the refusal. **The reviewer's own mutant tripped that refusal and
it complied.**

The reviewer independently reproduced G-1's digests and **agrees with the fail-closed narrowing
override**: the premise is recomputed rather than judged, and the merge gate's full suite remains the
backstop. Scope gate PASS — the changed files are exactly the six in `Touches`.
