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
**Touches:** tests/conftest.py, src/nonogram/db/session.py, tests/test_db_engine_lifecycle.py, tests/test_kill_matrix.py, tests/README.md  _(corrected 2026-10-22 from three files — cycle-1 F-107; the last two were declared `SCOPE+` by the implementer)_
**Review score:** 6.5 (cycle 1/3 — below the threshold of 8)
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
