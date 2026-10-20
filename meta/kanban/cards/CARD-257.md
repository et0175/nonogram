# CARD-257: Cut the guard's prose to what its 22 lines actually claim

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Complexity:** trivial
**Estimate:** 0.25d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/257-cut-the-guards-prose
**Worktree:** ../PythonProject4-card-257
**Source:** CARD-254 review cycle 3's closing answer — "the mechanism: yes, emphatically. The prose around it: no — and here is what I'd cut."
**Idea:** —
**Wave:** 50
**Depends on:** CARD-254 (merged `9e8aad6d`)
**Touches:** tests/test_db_engine_lifecycle.py, src/nonogram/db/session.py (docstring only)
**Review score:** —
**Started:** 2026-10-20T08:41:42Z · **Closed:** — · **Actual:** — · **Merge commit:** —
**Blocked by:** —

## Why — the arithmetic, which is the whole case

CARD-254 set out to retire ~400 lines and keep ~55. Measured at its merge:

```
tests/test_db_engine_lifecycle.py  1415 → 919 → 1062 → 1177
src/nonogram/db/session.py          327 → 368 →  376 →  384
                                   base  shrink  cyc1   cyc2
```

**The shrink removed 496 lines; the two review cycles put 258 back — 52 %** — as controls and as
prose *about* controls. Net **−181 (−10.4 %)**. The part that catches things is **~22 executable
lines**: two regexes, a 6-line counter, a 6-entry dict, a 14-line tree-wide equality. Prose to
mechanism in what survives is **1.69 : 1**, and `reset_engine()`'s docstring is **126 lines for a
6-line body — 21 : 1**.

Nothing here is wrong. That is what makes it worth a card: every one of those lines was added to
satisfy a legitimate finding, and the sum is still a file nobody will read.

## What to cut — three cuts, ~135 lines, no measured property lost

1. **Single-source the convention (~100 lines).** It is currently written twice "in the same words" —
   the guard class's docstring and `reset_engine()`'s. Keep `reset_engine()`'s (it is what a
   maintainer of the production module opens) and replace the class's copy with a cross-reference
   plus its `Controls:` list. **This is the cut that retires a rule with no control**: *"the same
   words in two places" is itself a claim, and nothing reds if they drift* — a doubling already paid
   three times (cycle 1 edited both, cycle 2 edited both, and two of cycle 3's Minors live in text
   that would need correcting in both).
2. **Delete control A's arm 2 (~10 lines, zero coverage).** It is a strict duplicate of arm 1's
   `setattr` iteration: the two probes differ only in the probe *function's name*, which a text scan
   cannot see. Measured: identical `Counter` under every mutant, and **no mutant kills one without
   the other**.
3. **Stop narrating review history in shipped docstrings (~25 lines).** Both of cycle 3's prose
   Minors are wrong about *cycles*, not about the mechanism — "those comparisons were true for every
   possible probe value" (one of them reds under SETATTR-DEL) and "two generations of this control"
   (there was one; two of the **family**). The mutant-per-arm table belongs on the card; a docstring
   needs the property and the mutant that reds it. This closes the surface where this family kept
   reappearing — **three cycles running, and in cycle 3 it shipped inside the code rather than on the
   card.**

**Also fix while there** (cycle 3's remaining Minor): arm 2b's position assertion lacks the
two-`setattr(` precondition. `rindex` returns the *last* occurrence, so on a one-call probe the
assertion is trivially green. It discriminates today — the probe has two, at offsets 49 and 122 — but
the same file asserts every other probe precondition explicitly.

## Acceptance criteria

- **AC-1** *Given* the single-sourced convention, *then* the blind-to list, the counting rule and the
  bound appear **once**, and the other site carries a pointer. No sentence is lost: diff the two
  copies before cutting and show every clause survives somewhere.
- **AC-2** (the control that replaces the duplication rule) *Given* the convention text, *then* a
  test holds that the production docstring and the guard agree on the **mechanism's own parameters**
  — the three global names and the two spellings — derived from the code rather than quoted. The old
  rule relied on two humans editing in step; this one reds.
- **AC-3** *Given* arm 2's deletion, *then* the per-assert kill matrix is unchanged for every
  remaining arm, measured with the line-count-preserving instrument CARD-254's cycle 3 used.
- **AC-4** *Given* arm 2b, *then* its probe's two-`setattr(` precondition is asserted, as the file's
  other probes assert theirs.
- **AC-5** (guard) *Given* all cuts, *then* the tree sweep is unchanged — **9 sites, 6 pairs,
  dict-equal, zero matches elsewhere** — and `session.py`'s docstring-stripped AST still hashes to
  `bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c`.

## Guardrails

- G-1: **No mechanism change.** The two regexes, the counter, the dict and the equality are untouched;
  this card moves and deletes prose and one duplicate arm.
- G-2: No test retired without a named survivor; arm 2's survivor is arm 1 and the measurement above
  is the evidence.
- G-3: `nonogram_poc` is never created, dropped, connected to or truncated.
- G-4: No new runtime dependency.

## Worktree notes

- **[Do not take timing measurements]** other cards may share this machine.
- **[The trap]** This card deletes prose that was each added to close a real finding. The failure mode
  is cutting a sentence that is the *only* statement of a bound — the blind-to list especially, which
  is the card's declared limit and not decoration. Diff before and after and show every clause
  survives somewhere, which is what AC-1 is for.
- **[The second trap]** Do not replace the duplication rule with a *new* claim about the two texts
  agreeing. AC-2 asks for an equality over the mechanism's parameters, derived from the code — not a
  string comparison of two docstrings, which would be the same uncontrolled rule with a test attached.
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`, reading the ADR
  files **case-insensitively** for the reach-limit idiom — this card is entirely about ADR-0039/R1.

## System contract

Curated to **10 of 29** in-scope rules under `meta/kanban/curation.md`: every rule whose
enforcement does not reach this card's new code is kept; the rest are dropped because the suite runs them on
every gate. **19 dropped.** ADR-0039 present, as the sanity check requires for a card
touching `tests/**`.

- **ADR-0022/R1** — _review-lens — nothing executes it_
  Grid extent crosses module boundaries as a (width, height) pair. No public function signature,
  request field, or export field reduces a grid's extent to a single scalar "size", and no source
  mode constructs a grid from one integer.
- **ADR-0036/R3** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect
  whatever Pillow call it is written with: four cards print the same difficulty glyph, and four
  slightly different dots cannot be fixed once a book is on paper.
- **ADR-0036/R4** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in
  U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: the cheapest way to print
  a difficulty dot is to append a bullet to a header string, and that route bypasses the one
  drawing site and CON-020's type floor at once.
- **ADR-0038/R6** — _review-lens — nothing executes it_
  Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution
  grid to the browser. A public or reader-facing player must not send the solution before the
  puzzle is solved, and any public phase reopens this ADR (CON-021).
- **ADR-0038/R7** — _review-lens — nothing executes it_
  Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in
  pyproject.toml. It is never added to project.dependencies or to the admin extra.
- **ADR-0038/R8** — _review-lens — nothing executes it_
  Browser tests run locally, against Chromium installed by `playwright install chromium`. When
  Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible
  in the run summary. They never pass silently. Once a CI pipeline exists, it installs Chromium
  (playwright install chromium) before running them; until then there is no CI, and that is a
  known gap, not a met clause.
- **ADR-0039/R1** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  A set a guard consults needs a completeness test written before the set, and any claim the guard
  makes about what it catches needs a control that can fail: caught WITH the set member present,
  missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage, and must be
  narrowed to what is measured or deleted.
- **ADR-0039/R2** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where no
  such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE, never
  a silent pass, and the unanalysable sites become named exemptions under ADR-0039/R3.
- **ADR-0039/R3** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT
  absorb — caught with the exemption removed, missed with it in place — is held to an equality
  against the sites that exist today, and records whatever it still cannot see as a measured bound
  with its own failing control.
- **CON-021** — _review-lens — nothing executes it_
  Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served
  behind the door that guards every other admin page (CON-015, CON-016). No other surface — the
  CLI, the web UI, or any public or hosted page — offers an interactive or playable puzzle. Play
  state is never persisted on the server: no progress, marks, error count, score or solve time is
  written to a database, file or server, no network request is made per mark, and no user account
  exists for playing (CON-017). The one place play state may be kept is the browser's own
  localStorage, per puzzle, so that a puzzle reopened in that browser resumes where it was; it
  never leaves that browser. The admin player ships the puzzle's solution grid to the browser to
  compute the error count and the solved state; this is permitted for the admin panel only, and a
  public or reader-facing player must not send a puzzle's solution to the browser before the
  puzzle is solved.


## Worktree notes — implementation (CARD-257)

### Line counts, against CARD-254's figures

```
tests/test_db_engine_lifecycle.py  1415 → 919 → 1062 → 1177 → 1162
src/nonogram/db/session.py          327 → 368 →  376 →  384 →  393
                                   base  shrink  cyc1   cyc2   CARD-257
```

Raw: **−15 / +9 = −6** over both files. The useful split, measured with
`ast` + `tokenize` (docstring lines ∪ comment lines vs. code lines):

| | prose | code | prose:code |
|---|---|---|---|
| guard file, before | 616 | 440 | 1.40 : 1 |
| guard file, after | **567** | **465** | **1.22 : 1** |
| `session.py`, before | 275 | 64 | 4.30 : 1 |
| `session.py`, after | 284 | 64 | 4.44 : 1 |

**85 lines of prose were cut; AC-2's control put 69 back as mechanism** —
`_spelling_heads` (13), the control (53), `_NAME_PLACEHOLDER` (3). That is the
same arithmetic CARD-254 recorded, with one difference worth keeping: this
time what came back is 24 lines of *code* and a docstring that names the
mutants reddening each of its asserts, not prose about a control. The guard
class's docstring is **116 → 59**; `reset_engine()`'s is **126 → 135**,
because single-sourcing moves text *into* the source of truth (the pointer
paragraph, plus the two clauses only the guard's copy carried).

Element by element: class docstring 116 → 59; control A 125 → 107 (docstring
37 → 30, arm 2 gone); control B 171 → 158 (docstring 63 → 48, +9 for AC-4's
precondition); `_hand_set_spellings` docstring 33 → 31.

### AC-1 — the clause-survival diff: 41 clauses checked, 0 lost

The retired copy was split into 41 clauses and each checked, by token, against
the final `reset_engine()` docstring, the final guard-class docstring and the
control docstrings (`scratchpad .../c257/ac1.py`). Every clause survives, and
each bound survives in exactly **one** place:

- the **blind-to list** lives only in `reset_engine()`: `globals()`,
  `importlib`, `delattr`, `list unpacking`, `dotted-path` each occur **0** times
  in the guard file and once in `session.py`. It gained the two clauses only the
  guard's copy had (*every element but the last of a tuple unpacking*) or that
  CARD-254's retirement table declared without either docstring enumerating (*a
  target passed as one whole dotted-path string*) — both narrow the guard's
  claim, never widen it.
- the **counting rule** and *convention, enforced at review* / *a card, not a
  commit*: once, in `session.py`. The equality's failure message no longer
  repeats the exempt-file list either — it points at the single source, since
  the dict above it is the authority.
- the **tree measurement** (12 `setattr(` with a quoted global downstream, 9
  counted, 3 stopped by their own `)`, i.e. arm 2b's property in the real tree)
  and *why this file is not itself an exemption*: once, in the guard class,
  where the tree they describe is.

**No bound lost its only statement.** Three *incidents* were dropped with their
claims kept (cut 3): M3c's narration, the "33 characters downstream / an
editorial parenthesis" F-002 story, and the two sentences cycle 3 flagged as
wrong about cycles ("those comparisons were true for every possible probe
value", "two generations of this control").

### AC-2 — the control that replaced "the same words in two places"

`test_both_convention_texts_agree_on_the_mechanisms_parameters`: an equality
over the mechanism's parameters, both sides symmetric — the globals
`_global_names_assigned_by("_init_engine")` finds, and the two spelling heads
read off `_hand_set_spellings`' compiled patterns (`_spelling_heads`: each
pattern's leading literal run, unescaped). Not a string comparison of the two
docstrings.

**Measured before handing back** (per-assert, mutants installed as module
attributes so they are line-count-preserving by construction):

| assert | what it is | GLOBAL-ADD | DOC-NAME-DEL | DOC-NAME-DEL-GUARD | SPELL-HEAD-RENAME | ASSIGN-HEAD-RENAME | DOC-POINTER-DEL | NAMES-BLIND |
|---|---|---|---|---|---|---|---|---|
| `:845` | preamble (names non-empty) | PASS | PASS | PASS | PASS | PASS | PASS | **RED** |
| `:857` | the globals, per text | **RED** | **RED** | **RED** | PASS | PASS | PASS | n/r |
| `:863` | the spellings, per text | PASS | PASS | PASS | **RED** | **RED** | PASS | n/r |
| `:869` | the pointer to the single source | PASS | PASS | PASS | PASS | PASS | **RED** | n/r |

Every assert reds under a mutant that deletes what its own sentence names, and
both *sides* are live: `DOC-NAME-DEL` (production text) and
`DOC-NAME-DEL-GUARD` (class text) each red `:857` on their own. The six helper
mutants of the old matrices (`SPELL-*-DEL`, `COUNT-COLLAPSE`, `NORM-DEL`,
`PAREN-DEL`) leave all four green — it is a text control, not a scan control.

**A defect the instrument caught in my own addition, before hand-back:** the
first version substituted `_NAME_PLACEHOLDER` *before* the name check, which
put `names[0]` back into every text that has a placeholder — so
`DOC-NAME-DEL-GUARD` returned PASS. The names are now read from the text as it
ships, and the substitution is used only for the spelling heads.

### AC-3 — per-assert kill matrix, before and after deleting arm 2

Instrument: every `ast.Assert` at any depth rewritten into a recording
try/except keyed on the node's own `lineno`; mutants installed as module
attributes, so no deletion mutant can shift a line number. It reproduces both
of CARD-254's cycle-3 matrices **cell for cell** before any edit of mine.

`test_the_count_reds_on_a_new_file_a_new_name_and_a_tenth_site`:

| assert (before → after) | what it is | SHIPPED | SPELL-SETATTR-DEL | SPELL-ASSIGN-DEL | COUNT-COLLAPSE |
|---|---|---|---|---|---|
| `:920` → `:929` | preamble | PASS | PASS | PASS | PASS |
| `:922` → `:931` | preamble | PASS | PASS | PASS | PASS |
| `:945` → `:955` | **arm 1** (nested in the `for`) | PASS | **RED** | **RED** | PASS |
| `:956` → *deleted* | **arm 2, "a new file"** | PASS | **RED** | PASS | PASS |
| `:974` → `:972` | arm 2 now, a new name | PASS | **RED** | PASS | PASS |
| `:978` → `:976` | precondition | PASS | PASS | PASS | PASS |
| `:984` → `:982` | precondition | PASS | PASS | PASS | PASS |
| `:992` → `:990` | precondition (real file's count) | PASS | **RED** | PASS | PASS |
| `:1001` → `:999` | arm 3 now, a tenth site | PASS | **RED** | PASS | **RED** |

**Every remaining arm's row is unchanged.** The deleted arm's row is a strict
subset of arm 1's, across **nine** mutants (the four above plus `NORM-DEL`,
`PAREN-DEL`, `GLOBAL-ADD`, `SPELL-HEAD-RENAME`, `ASSIGN-HEAD-RENAME`): it reds
only under `SPELL-SETATTR-DEL` and `SPELL-HEAD-RENAME`, and arm 1 reds under
both. **No mutant kills arm 2 while arm 1 survives** — zero marginal coverage,
which is G-2's evidence; its named survivor is arm 1, whose probe file
(`test_not_exempt.py`) is no exemption's, so the test's name stays true and its
docstring now says which arm carries the *new file* direction.

`test_a_wrapped_call_is_counted_and_a_parenthesised_receiver_is_not` — also
unchanged, arm for arm:

| assert (before → after) | arm | SHIPPED | NORM-DEL | PAREN-DEL |
|---|---|---|---|---|
| `:1092` → `:1074` | arm 1 | PASS | **RED** | PASS |
| `:1110` → `:1092` | arm 2a | PASS | PASS | **RED** |
| — → `:1117` | **AC-4's new precondition** | PASS | PASS | PASS |
| `:1136` → `:1122` | arm 2b | PASS | **RED** | **RED** |
| `:1151` → `:1137` | arm 3 | PASS | PASS | **RED** |
| `:1171` → `:1156` | arm 4 | PASS | **RED** | PASS |

### AC-4 — arm 2b's precondition, and the mutant that reds it

`assert two_calls_source.count("setattr(") == 2` before the position assert.
Certified with a **real-file, line-count-preserving** mutant,
**PROBE-ONE-CALL** (the probe's first call replaced by three `"\n"` strings):
the precondition reds (`:1116` in that run) while the position assert stays
**PASS** — exactly the card's point, that `rindex` finds the last call and a
one-call probe makes the position trivially green. Applied from a `cp -p`
backup and restored from it: `diff -q` clean, `shasum -a 256` identical
(`447c5be5…`). Never `git checkout --`.

### AC-5 / G-1 — re-derived, unchanged

Names derived from `session.py`'s AST, never from the test:
`['SessionLocal', '_engine_url', 'engine']`.

- Tree sweep over `tests/**/*.py`: **9 sites, 6 pairs**, dict-equal to
  `_EXEMPT_HAND_SET_SITES` **True**, **zero** matches outside the two exempt
  files. Identical before and after the cuts.
- `session.py` with every module/class/function docstring stripped,
  round-tripped through `ast.unparse`, re-parsed and `ast.dump`ed: dump length
  **9154**, sha256
  **`bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c`** — the
  declared value, to the byte. The `session.py` edit is docstring-only; the two
  regexes, the counter, the dict and the equality are untouched (G-1).

### Test selections (no full suite, no timings)

`meta/kanban/.full-suite.lock` checked absent before **every** run. Database
`nonogram_pythonproject4_card_257_01bc64b6d28b_test` (derived by
`tests/db_name.py` for this worktree), passed as both `DATABASE_URL` and
`TEST_DATABASE_URL` as literals. `nonogram_poc` was never named, created,
dropped, connected to or truncated.

- `tests/test_db_engine_lifecycle.py` — **13 passed, 0 skipped** (`-rs` reports
  none; was 12 — the new control is the thirteenth)
- touched-adjacent: `test_db_engine_lifecycle`, `test_db_url_driver`,
  `test_db_connect_timeout`, `test_db_isolation`, `test_cli` (the structural
  import guard), `test_card_156_db_fixture`, `test_db_e2e_smoke`,
  `test_card_109_database_guard`, `test_book_difficulty_dots` —
  **409 passed, 0 skipped, 0 failed** (CARD-254's 407 for the same selection +
  the file's 12th and 13th tests)

### Residue

- `reset_engine()`'s docstring is **135 lines for a 6-line body**. The
  duplication is gone and the pointer is controlled, but the single source is
  still long, and three of its sections (`Who calls it and why`, `What is
  pinned, and what is not`) are CARD-252's record rather than this card's
  scope. A later card can take them; this one only trimmed two sentences there
  ("the older reading of it here was wrong", "re-measured as review mutant R7").
- The AC-2 control holds the guard's text to the *names* in double backticks,
  which the scan does not count. That is load-bearing for the class docstring's
  opening paragraph: it now has to keep naming the three globals.

- **[Orchestrator] the new rule caught a defect in the agent's own addition before hand-back, which
  is exactly what it was promoted for.** Its first version of AC-2's control substituted the name
  placeholder **before** the name check, re-injecting `names[0]` into any text carrying a placeholder
  — so `DOC-NAME-DEL-GUARD` came back **PASS** on a text that no longer named the globals. The
  instrument found it; the agent fixed it and reported it. **One wave after six consecutive gating
  findings were created by the previous fix, the first card to carry the rule caught its own.**
- **[Orchestrator] it reproduced CARD-254's 52 % phenomenon, measured it, and named the difference.**
  85 lines of prose cut, **69 put back by AC-2's control** — raw net **−6**. But the composition is
  not the same: what came back is **24 lines of code** plus a docstring naming the mutant per assert,
  where CARD-254's cycles put back prose *about* controls. The ratio moved where it matters: the
  guard file's prose:code goes **1.40 : 1 → 1.22 : 1**, and the duplicated class docstring **116 →
  59**. This is the honest shape of the trade: a control that replaces an uncontrolled rule costs
  lines, and those lines are a different thing from the lines it retired.
- **[Orchestrator] AC-1's clause-survival diff is the part I would have most expected to go wrong:
  41 clauses, 0 lost.** Each clause of the retired copy token-checked against all three surviving
  texts. The blind-to list now lives only in `reset_engine()` — `globals()`, `importlib`, `delattr`,
  list unpacking and dotted-path each occur **zero** times in the guard file — and it *gained* two
  clauses: the one only the guard's copy carried, and one CARD-254's retirement table declared while
  neither docstring enumerated it. **Both narrow the claim; neither widens it.** Three *incidents*
  were dropped with their claims kept, which is cut 3 doing precisely its job.
- **[Orchestrator] AC-3 reproduced CARD-254's cycle-3 matrices cell for cell before any edit**, and
  every remaining arm's row is unchanged after the deletion. Over nine mutants the deleted arm's row
  is a **strict subset** of arm 1's — no mutant kills arm 2 while arm 1 survives — which is what
  "zero coverage lost" has to mean to be worth saying.
- **[Orchestrator] AC-4's precondition is certified by the mutant that makes it matter**: with the
  probe reduced to one `setattr(` call, the precondition **reds** while the position assert stays
  **PASS**. That is the card's point made executable — `rindex` on a one-call probe makes the position
  assertion trivially true.
- **[Residue, flagged for the reviewer]** `reset_engine()`'s docstring is still 135 lines for a 6-line
  body. The duplication is gone and the pointer is controlled, but its `Who calls it and why` and
  `What is pinned, and what is not` sections are **CARD-252's** record, outside this card's three
  cuts. And the AC-2 control holds the guard text to names in double backticks, which the scan does
  not count — so the class docstring's opening paragraph is now load-bearing.
- **[Build gate 1 — PASSED]** `245bc898`, solo: **8623 passed**, 1 skipped, 16:34, EXIT=0. Reconciles
  exactly: main 8622 + the one test AC-2's control adds. The guard said nothing during the run, which
  is correct for a gate holding its own lock.
