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
| guard file, after | **568** | **465** | **1.22 : 1** |
| `session.py`, before | 275 | 64 | 4.30 : 1 |
| `session.py`, after | 284 | 63 ‡ | 4.51 : 1 ‡ |

‡ **The method, not just the number, was wrong** — corrected at review cycle 1 / fix 1. `code = total − prose − blank`
**double-subtracts blank lines that sit inside a docstring** (22 on main, 23 here), and the docstring grew by 9 lines,
one of them blank, which is where the original "64 both sides" came from. Under set arithmetic —
`code = total − |docstring lines ∪ comment lines ∪ blank lines|` — `session.py` has **86 code lines before and 86
after, unchanged**, which is what *docstring-only* means and agrees with the byte-identical docstring-stripped AST
(dump 9154, sha256 `bdb10905…`). The same artifact inflates the guard file's code column (set-based: 494 → 521).

**85 lines of prose were cut; AC-2's control put 69 back as mechanism** —
`_spelling_heads` (13), the control (53), `_NAME_PLACEHOLDER` (3). That is the
same arithmetic CARD-254 recorded, with one difference worth keeping: this
time what came back is 25 lines of *code* and a docstring that names the
mutants reddening each of its asserts, not prose about a control. The guard
class's docstring is **116 → 59**; `reset_engine()`'s is **126 → 135**,
because single-sourcing moves text *into* the source of truth (the pointer
paragraph, plus the two clauses only the guard's copy carried).

Element by element: class docstring 116 → 59; control A 125 → 107 (docstring
37 → 30, arm 2 gone); control B 171 → 158 (docstring 63 → 47, +9 for AC-4's
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

> **⚠ SUPERSEDED — two of these four rows were wrong, and the table is kept as the record of what
> `245bc898` actually measured, not as a current claim.** `DOC-NAME-DEL` was refuted at review cycle 1
> (true only for a name choice the matrix never stated — `engine` is a substring of `reset_engine`,
> `_init_engine`, `_engine_url`), and `DOC-POINTER-DEL` at review cycle 2 (true only under a
> substring-wide deletion that also removes a control's own method name). **The current state is the
> table below.** Both arms shifted twice; every line number in this table is stale.

| assert | what it is | GLOBAL-ADD | DOC-NAME-DEL | DOC-NAME-DEL-GUARD | SPELL-HEAD-RENAME | ASSIGN-HEAD-RENAME | DOC-POINTER-DEL | NAMES-BLIND |
|---|---|---|---|---|---|---|---|---|
| `:845` | preamble (names non-empty) | PASS | PASS | PASS | PASS | PASS | PASS | **RED** |
| `:857` | the globals, per text | **RED** | **RED** † | **RED** † | PASS | PASS | PASS | n/r |
| `:863` | the spellings, per text | PASS | PASS | PASS | **RED** | **RED** | PASS | n/r |
| `:869` | the pointer to the single source | PASS | PASS | PASS | PASS | PASS | **RED** † | n/r |

† refuted; see the superseding table.

**The current AC-2 matrix, at `daa721ae`** — per assert, ANY-RED aggregated over every execution
(the names and heads arms run **twice**, once per text), line-count-preserving mutants, domain =
one `ast.Assert` node's verdict:

| assert | what it is | SHIPPED | DOC-NAME-DEL ×3 names ×2 texts | GLOBAL-ADD | DOC-HEAD-DEL ×2 heads ×2 texts | SPELL/ASSIGN-HEAD-RENAME | POINTER-ROT | POINTER-DEL-WORD | CONTROLS-RENAME-ONLY | NAMES-BLIND |
|---|---|---|---|---|---|---|---|---|---|---|
| `:859` | preamble (names non-empty) | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **RED** |
| `:878` | the globals, per text, **whole word** | PASS | **RED** (all 6) | **RED** | PASS | PASS | PASS | PASS | PASS | n/r |
| `:889` | the spellings, per text | PASS | PASS | PASS | **RED** (all 4) | **RED** | PASS | PASS | PASS | n/r |
| `:897` | the **derived dotted path** to the single source | PASS | PASS | PASS | PASS | PASS | **RED** | **RED** | PASS | n/r |

The pointer arm is now `target = f"{pointer.__module__}.{pointer.__name__}"` with `pointer =
app_session.reset_engine` — **both** halves derived, so no hand-written literal remains (ADR-0039/R2).
`CONTROLS-RENAME-ONLY` passing is the point: renaming a control's own method is **not** a lost pointer,
so the arm is better *targeted*, not merely stricter. Two extra kills the `__module__`-plus-literal form
would not have: **CODE-RENAME** (function renamed in code, docstrings stale) and **MODULE-MOVE**.

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
  still long, and **two** of its three sections (`Who calls it and why`, `What is
  pinned, and what is not`) are CARD-252's record rather than this card's
  scope — the third, `The convention, and what little enforces it`, is the single source **this card
  created**. (Corrected at review cycle 1 / fix 1: the original sentence said "three" and named two,
  wrong in both count and attribution.) A later card can take them; this one only trimmed two sentences there
  ("the older reading of it here was wrong", "re-measured as review mutant R7").
- The AC-2 control holds the guard's text to each of the three *names*
  **as a word-bounded bare name, anywhere in the text** — the double backticks
  the paragraph happens to use are irrelevant to it, and the scan does not count
  them either way. *(Corrected at review cycle 3, F-008: the original sentence
  said the control holds the text to the names "in double backticks", which read
  as what the control enforces is false and was measured so —
  `AUDIT NAME-DEL-BACKTICKED[engine]` leaves the names arm PASS with backticked
  occurrences at 0.)* It is still load-bearing for the class docstring's opening
  paragraph: that paragraph is the only place all three globals are written out,
  so it has to keep naming them.

- **[Orchestrator] the new rule caught a defect in the agent's own addition before hand-back, which
  is exactly what it was promoted for.** Its first version of AC-2's control substituted the name
  placeholder **before** the name check, re-injecting `names[0]` into any text carrying a placeholder
  — so `DOC-NAME-DEL-GUARD` came back **PASS** on a text that no longer named the globals. The
  instrument found it; the agent fixed it and reported it. **One wave after six consecutive gating
  findings were created by the previous fix, the first card to carry the rule caught its own.**
- **[Orchestrator] it reproduced CARD-254's 52 % phenomenon, measured it, and named the difference.**
  85 lines of prose cut, **69 put back by AC-2's control** — raw net **−6**. But the composition is
  not the same: what came back is **25 lines of code** plus a docstring naming the mutant per assert,
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
  cuts. And the AC-2 control holds the guard text to each name **as a word-bounded bare name anywhere in
  the text** (not to the double backticks, which it never reads) — so the class docstring's opening
  paragraph, the only place all three are written out, is now load-bearing. *(Wording corrected at review
  cycle 3, F-008.)*
- **[Build gate 1 — PASSED]** `245bc898`, solo: **8623 passed**, 1 skipped, 16:34, EXIT=0. Reconciles
  exactly: main 8622 + the one test AC-2's control adds. The guard said nothing during the run, which
  is correct for a gate holding its own lock.

### [Review 1/3] Score: 8.5 — FAILS the severity gate (one open Important)

Report: `meta/review/CARD-257-cycle1.yml` (5 findings, all `status: open`). Score 8.5 ≥ min_score 8, but
**one open Important fails the card regardless of score.**

- **F-001 — Important, gating — ADR-0039/R1 — `tests/test_db_engine_lifecycle.py:857`.** AC-2's
  name-agreement arm **cannot fail for the global `engine`**. The assert is a substring test —
  `{name for name in names if name in text} == set(names)` — and `engine` is a substring of
  `reset_engine`, `_init_engine`, `_engine_url` and `create_engine`, so `'engine' in text` is satisfied
  by any text that merely mentions one of those functions. For the guard text it is **provably**
  unfalsifiable: the same test's `:869` requires `"reset_engine" in guard`. Measured per assert:

  | mutant | `:857` |
  | --- | --- |
  | `DOC-NAME-DEL-PROD[SessionLocal]` / `[_engine_url]` | **RED** |
  | `DOC-NAME-DEL-GUARD[SessionLocal]` / `[_engine_url]` | **RED** |
  | `DOC-NAME-DEL-PROD[engine]` | **PASS** |
  | `DOC-NAME-DEL-GUARD[engine]` | **PASS** |

  So one of three set members is narrative, not coverage — and AC-2's claim ("the three global names …
  this one reds") and the matrix row `DOC-NAME-DEL → :857 RED` are both **wider than the mechanism**:
  the row is true only for a name choice the matrix never states. Restated at `:304-308` and in the
  assert's own failure message at `:858-860`. Failure direction is safe (a missed red, not a false red),
  hence Important and not Critical.
- **F-002** (medium) the residue says "**three** of its sections … are CARD-252's record" and names
  **two**; `reset_engine()` has exactly three, and the third — *The convention, and what little enforces
  it* — is **this card's own scope**, the opposite of what the sentence claims.
- **F-003** (low) three line-split figures are off by one on recomputation: after-prose **568** not 567;
  code delta **+25** not "24 lines of code"; control B's docstring **63 → 47** not 63 → 48.
- **F-004** (low) the class docstring's **opening paragraph is now load-bearing** — it is the only place
  all three globals are written out, and the control holds the text to each name as a **word-bounded bare
  name anywhere in the text** (the double backticks are not what it reads — wording corrected at cycle 3,
  F-008). The class docstring says so nowhere, and that paragraph reads as pure
  CARD-252 history, i.e. the exact prose cut 3 targets. The next prose cut deletes what a control needs.
- **F-005** (low) a **second** "same words in two places" doubling survives at `tests/conftest.py:469-479`
  — the step-3-position / "re-measured as review mutant R7" narration this card cut from `session.py`,
  still there verbatim in substance, uncontrolled, and absent from the residue list. **Outside
  `Touches:`, so not an AC failure** — carded rather than fixed.

Root causes: **RC-1** card figures not recomputed at the final revision (F-002 + F-003); **RC-2** the
retired pattern's second instance and its successor's new bound both undeclared (F-004 + F-005).

**What held, recomputed independently.** `1177 → 1162`, `384 → 393`; prose/code `616/440 → 1.40:1` and
**1.22:1**; docstrings `116 → 59`, `126 → 135`, `125 → 107`, `171 → 158`, `33 → 31`; the 69-put-back
decomposition 13 + 53 + 3; tree sweep **9 sites, 6 pairs, dict-equal True, zero matches outside the two
exempt files**, identical on main and HEAD; **12 `setattr(` / 9 counted / 3 stopped by their own `)`**
out of 375 occurrences; `13 passed` and `409 passed`.

**AC-5 / G-1 — the AST sha256 held to the byte** and, better than declared: dump length **9154**, sha256
`bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c`, and **byte-identical to main's** —
which proves independently that the `session.py` edit is docstring-only rather than asserting it.

**AC-1 — clause survival held substantively, and tree-wide.** The reviewer built its own coarser split
(25 clauses) and token-checked each against all **seven** surviving texts: 23 above 80 % content-token
coverage, the 2 below both review narration cut 3 declares as deliberately dropped. Single-sourcing
verified across the whole tree, not just the two files: `globals()`, `importlib`, `delattr`, list
unpacking, dotted-path, *convention, enforced at review*, *recorded exceptions* each occur **0** times in
the guard file and once in `session.py`, and no third file restates the list, the rule or the bound. Both
gained clauses **narrow**, and the dotted-path one was verified *true of the mechanism* — the pattern
requires a quote immediately before the name, and a dotted path puts a dot there. **No clause widened.**

**AC-3 holds, AC-4 certified, G-2 holds**, all reproduced with the reviewer's own instrument (the
implementation's is not in the worktree): both of CARD-254's cycle-3 matrices reproduced **cell for cell
on main** and the card's after-column cell for cell on HEAD; over 7 mutants + SHIPPED the deleted arm
`:956` reds only under `SPELL-SETATTR-DEL` and `SPELL-HEAD-RENAME` while arm 1 reds under both — a strict
subset, so no mutant kills arm 2 while arm 1 survives; `PROBE-ONE-CALL` (3 lines for 3 lines) reds
`:1117` while `:1122` stays **PASS**.

**AC-2's "derived from the code, not a string comparison" — SATISFIED.** Names from `session.py`'s AST,
heads from the two compiled patterns' leading literal runs; no assert compares the two docstrings. The
card's self-caught placeholder defect is **really fixed and complete** — names are read from the text as
it ships, the substitution runs afterwards and feeds only the heads check, and it is load-bearing
(`SUBST-DEL` and `PLACEHOLDER-RENAME` each red `:863`). F-001 is the one defect, inside the names arm.

**Seven adversarial false positives dropped** before filing; no fourteenth entry added to the ledger.
System contract: 10 checked — 3 ✓, 6 ⚠ `no_eligible_fact`, 1 ✗ (ADR-0039/R1 via F-001). **ADR-0036/R4 ✓**
by a full codepoint scan of `src/nonogram/**`: 3 hits, all U+2022 in `pdf_generator.py` (the declared
exemption), **0** banned codepoints among this diff's added lines.

**[Two instrument traps paid for again, in new forms]** The reviewer's first instrument aggregated
**last-write-wins** and lost a RED from an assert inside a `for` loop — a *third* distinct form of
"a surviving mutant and a never-reached assert look identical", after wave 49's line-numbering trap and
CARD-256's domain trap. And `PROBE-ONE-CALL` must target the occurrence **inside arm 2b's probe**: the
same three lines appear earlier in the file, and a first-occurrence replacement silently mutates the
wrong arm and returns a false all-green. Both are now recorded for the fix station.

**[Orchestrator defect, mine]** Both cycle-1 dispatch briefs told the reviewers the derived test database
"does not exist on this host, so DB-mode tests skip". It **does** exist — `gate.sh` creates it — and the
guard file reports 13 passed / **0 skipped** under `-rs`. No verdict depended on it, but I stated as fact
something I had not checked for this worktree.

### [Fix 1] `df23bf64` — F-001 and F-004 closed; the card's measurement *method* was also wrong

Commit `df23bf64` on `card/257-cut-the-guards-prose`, pathspecs `tests/test_db_engine_lifecycle.py`
`src/nonogram/db/session.py` (the card's `Touches`, exactly). `session.py` contributed nothing — it is
unchanged — so the commit is **1 file, +25/−7**. Nothing under `meta/` in it.

**F-001 — fixed.** The names arm is now word-bounded,
`re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text)` (stdlib; `re` already imported).
The claim in the control's docstring and the assert's own failure message were both narrowed to say
*whole word*, and a six-line inline comment states the mechanism — which identifiers contain `engine`,
and that the pointer assert forces `reset_engine` into the guard text. Asserts shifted:
`:845→:851`, `:857→:870`, `:863→:881`, `:869→:887`.

Grid, re-derived per assert with **any-RED aggregation** and mutants installed as module attributes
(line-count-preserving by construction). Fidelity first: before the edit the instrument reproduced
cycle 1's F-001 table cell for cell **and** the card's AC-2 columns for `GLOBAL-ADD` and `NAMES-BLIND`.

| mutant | `:851` preamble | `:870` names | `:881` heads | `:887` pointer |
| --- | --- | --- | --- | --- |
| SHIPPED | PASS | PASS | PASS | PASS |
| `DOC-NAME-DEL-PROD[SessionLocal]` / `[_engine_url]` / `[engine]` | PASS | **RED** | PASS | PASS |
| `DOC-NAME-DEL-GUARD[SessionLocal]` / `[_engine_url]` / `[engine]` | PASS | **RED** | PASS | PASS |
| `GLOBAL-ADD` | PASS | **RED** | PASS | PASS |
| `NAMES-BLIND` | **RED** | n/r | n/r | n/r |

All six name×text cells red where two were PASS before. `:887` stays PASS under the `[engine]` cells,
which is the point: `reset_engine` survives that mutant, so the pointer assert no longer props the names
arm up.

**The sibling `:881` was deliberately left a substring test, and the reasoning is load-bearing.**
Word-bounding it would be **wrong, not merely stricter**: the dotted head `.SessionLocal` begins with `.`,
so a left lookbehind tests the character *before* the dot and would reject a legitimate receiver spelling
such as `app.SessionLocal =` — exactly the shape the scan's pattern 2 counts. Census, measured rather
than reasoned: `setattr(` prod 6 total / 6 standalone, guard 4/4; `.SessionLocal` prod 1/1, guard 1/1 —
**zero occurrences embedded in a larger identifier in either text**, so substring and word-bounded are
*equivalent* on both texts as they ship. Contrast with `engine`, which had **23 substring vs 12
standalone** occurrences in the prod text and **8 vs 2** in the guard text, the surplus being the four
identifiers both texts must mention anyway. Declared latent, not fixed: a hypothetical `.SessionLocalX`
or `_setattr(` would satisfy it; both are 0 today. Each of the four `DOC-HEAD-DEL` cells reds `:881`.

**F-004 — fixed.** One clause beside the three names in the class docstring's opening paragraph, saying
that this is the only place the docstring names all three and that the control holds it to naming each as
a whole word. Two properties the fix was deliberate about: the clause **names no global itself**, so it
cannot substitute for the paragraph and defeat the mutant (`DOC-NAME-DEL-GUARD[*]` still reds all three
after the edit — had the clause repeated the names, that cell would have come back PASS), and the "only
place" claim is measured (guard standalone counts `SessionLocal` 1, `_engine_url` 1, `engine` 2, the
second being *"something retires its engine"* in the same paragraph).

**F-002 confirmed by AST.** `reset_engine()` has **exactly three** underline-style sections —
`Who calls it and why` (docstring line 9), `What is pinned, and what is not` (27), `The convention, and
what little enforces it` (65). The first two are CARD-252's record; **the third is the single source this
card created.** So the residue's "three of its sections … are CARD-252's record" is wrong in both count
and attribution, exactly as cycle 1 said.

**F-003 — all three corrections confirmed, and a fourth defect found in the card's METHOD.**
The split method was reproduced exactly (prose = docstring physical lines ∪ comment lines;
`code = total − prose − blank`) and it hits both of the card's main-revision anchors to the line
(guard 616/440, session 275/64), so the method is the card's, not a different one.

| | prose | code | ratio | card said |
| --- | --- | --- | --- | --- |
| guard file, main | 616 | 440 | 1.40 : 1 | held |
| guard file, `245bc898` | **568** | **465** | 1.22 : 1 | 567 — **wrong, 568** |
| `session.py`, main | 275 | 64 | 4.30 : 1 | held |
| `session.py`, `245bc898` | 284 | **63** | **4.51 : 1** | 64 / 4.44 : 1 — **wrong**, and cycle 1 called it held |

Also confirmed: code delta **+25**, not "24 lines of code"; control B's docstring **63 → 47**, not 63 → 48.
Re-confirmed as held: control A 125 → 107 (docstring 37 → 30), class docstring 116 → 59,
`reset_engine()` 126 → 135, `_hand_set_spellings` docstring 33 → 31.

**The method defect, which neither the card nor cycle 1 caught:** `code = total − prose − blank`
**double-subtracts blank lines that sit inside a docstring** (22 such on main, 23 at `245bc898`). The
docstring grew by 9 lines, one of them blank, so the artifact shifted by one and produced the false
"64 both sides". Under set arithmetic — `code = total − |prose ∪ blank|` — `session.py` has **86 code
lines before and 86 after, unchanged**, which is what *docstring-only* means and agrees with the
byte-identical AST. The same artifact inflates the guard file's code figures (set-based 494 → 521 → 526).
**This is the figures rule biting its own instrument:** recomputation caught three stale numbers, and
reproducing the *method* caught the one that was never computable.

**Line-reference correction to cycle 1's report.** The DOC-NAME-DEL claim is at `:838-842` on
`245bc898` (now `:843-849`), **not** `:304-308` — that range is inside `_hand_set_spellings`' docstring
and says nothing about DOC-NAME-DEL. `meta/review/CARD-257-cycle1.yml` is left as the reviewer filed it;
the correction lives here.

**New figures created by the fix**, same method as the card: guard file **1162 → 1180** (+18), prose
**568 → 581**, code **465 → 470**, ratio **1.22 : 1 → 1.24 : 1**; class docstring **59 → 63**; the AC-2
control **53 → 67** lines (docstring 23 → 25); `session.py` unchanged at **393**. Every assert in
controls A and B shifts by exactly **+18**, so the card's AC-3/AC-4 "after" columns renumber:
`:929→:947, :931→:949, :955→:973, :972→:990, :976→:994, :982→:1000, :990→:1008, :999→:1017` and
`:1056→:1074, :1058→:1076, :1074→:1092, :1092→:1110, :1117→:1135, :1122→:1140, :1137→:1155, :1156→:1174`.

**G-1 / AC-5 re-derived**: `session.py` never left the tree (`git diff HEAD -- src/nonogram/db/session.py`
empty); docstring-stripped AST dump length **9154**, sha256
`bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c` — the declared value, to the byte.
**ADR-0036/R4**: 0 banned codepoints among the 25 added lines; tree-wide 3 hits, all U+2022 in
`pdf_generator.py`, the declared exemption. **G-4**: no dependency added.

**F-005 not fixed, as instructed — carded as CARD-259, now with its measured extent.** The duplicated
statement is `tests/conftest.py` **lines 472-478**, inside `_rebuild_public_schema`'s docstring (its
step-3 item spans 469-478). **Nothing controls it**: no test anywhere reads
`_rebuild_public_schema.__doc__` (a `.__doc__` grep over `tests/` returns only `reset_engine`, the guard
class, `round_ink`, `web`, `pages`, `pdf`); the only cross-references are an *import of the function* and
prose mentions. `tests/conftest.py` was neither edited nor committed.

**[The fix ran the instrument over its own additions, which is what the rule is for.]** Both touched
assertions were measured per assert with a named mutant that reds them, and the kill attempt against
F-004's new clause is the *same* mutant as F-001's fix — `DOC-NAME-DEL-GUARD[engine]` would have come back
PASS if the clause had repeated the names. It reds. No defect found in its own additions this time, one
wave after the rule was promoted because six consecutive gating findings had been created by the previous
fix.

### [Review 2/3] Score: 8.5 — a NEW open Important. The fix closed what it claimed and left the identical defect one assert down

Report: `meta/review/CARD-257-cycle2.yml`. **F-001 fixed** (`df23bf64`), **F-004 fixed** (`df23bf64`),
**F-005 wontfix** — resolved as carded (CARD-259). **F-006 is new, Important, gating.** Not a confirmation
delta, so cycle 3 runs in full mode.

**F-001's fix verified independently.** The reviewer wrote a second instrument from scratch — every
`ast.Assert` wrapped on its **own** source lineno, the tree handed straight to `compile()` and never
re-unparsed so no line can shift, every mutant an in-memory attribute patch, **any-RED** aggregation — and
reproduced the fix's grid **cell for cell**. All three deciding readings hold: SHIPPED all-PASS; all six
`DOC-NAME-DEL` cells RED at `:870`; `:887` **PASS** under both `[engine]` cells. Worth recording: the raw
outcome lists show each RED landing on the mutated text's own iteration, so **any-RED aggregation is doing
real work here — last-write-wins would have lost three of the six.** A sub-mechanism cross product adds the
two mutants the comment needs: `LOOKBEHIND-DEL` **reproduces cycle 1's defect exactly** (both `[engine]`
cells go PASS) as the inside-the-region mutant, and `LOOKAHEAD-DEL` survives all 16 cells as the
claim's-edge mutant.

**The heads arm's deliberate exception survived the check.** The census reproduced exactly (prod `setattr(`
6/6, guard 4/4, `.SessionLocal` 1/1 and 1/1, **0 embedded in a larger identifier**), and a word-bounded
variant stays green on all four cells — so word-bounding would not break today's text, but it *would* be
wrong rather than merely stricter: `app.SessionLocal = None` and `x.SessionLocal = None` are genuinely
matched by scan pattern 2 `\.SessionLocal\s*=(?!=)` and a left lookbehind rejects them. Today's texts write
`` ``.SessionLocal =`` `` after a backtick, which is *why* the two are currently equivalent — and the fix
stated that equivalence rather than hiding behind it.

**F-004 is not self-defeating, verified by the right mutant.** "Delete every whole-word name" cannot
distinguish the clause from the paragraph, so the reviewer ran **ENUM-DEL-KEEP-CLAUSE**: remove only the
enumeration sentence, keep the appended clause. The clause alone holds **0** whole-word occurrences of each
of the three names; the guard's counts go 1→0, 1→0, 2→0 and `:870` **REDs**. The clause is a signpost, not a
second copy.

---

**F-006 — Important, gating — `tests/test_db_engine_lifecycle.py:887` — ADR-0039/R1.**
`assert "reset_engine" in guard` is a bare substring test. The guard docstring carries `reset_engine`
**4×**: twice as the real pointer (``:func:`nonogram.db.session.reset_engine` ``), once in Control 1's
prose, and **once embedded in a method name in the `Controls` list** —
``:meth:`test_reset_engine_is_public_and_says_who_calls_it` ``. That fourth occurrence is not a pointer, and
it alone keeps the assert green:

| mutant | `:887` |
| --- | --- |
| SHIPPED | PASS |
| **POINTER-ROT** (both `:func:` references renamed to a function that does not exist; `Controls` untouched) | **PASS** |
| **POINTER-DEL-WORD** (every whole-word `reset_engine` gone; `Controls` untouched) | **PASS** |
| POINTER-DEL-WORD + `Controls` entry renamed | RED |

POINTER-ROT is the likeliest real drift — rename the function, miss the two references — and it is
**literally the failure the assert's own message names**, *"a pointer that rots"*. Re-derived a second time
with no instrument at all, by compiling the assert's own test expression out of the AST and evaluating it
against mutated guard strings, so the finding does not rest on instrumentation.

**Word-bounding is not the fix, and the measurement says so**: a word bound still passes POINTER-ROT,
because Control 1's prose carries `reset_engine` as a whole word. What discriminates is the **dotted path,
derived rather than quoted** — `f"{app_session.reset_engine.__module__}.reset_engine"` — which reds under
**both** POINTER-ROT and POINTER-DEL-WORD, passes on SHIPPED, and correctly **passes when only the
`Controls` entry is renamed**: better *targeted*, not merely stricter, the same distinction the fix drew
for the heads arm.

**Provenance matters here.** This assert does not exist on main — it is this card's own new control from
`245bc898`, untouched by fix 1. So cycle 1's "DOC-POINTER-DEL reds `:869`" reproduces only under a
substring-wide deletion that removes the method name too, which is the **identical epistemic error** as
cycle 1's `DOC-NAME-DEL → RED`: true only for a mutant shape the matrix never stated.

- **F-007** (Minor) the comment fix 1 added says `engine` sits inside `reset_engine`, `_init_engine`,
  `_engine_url` and `create_engine`, "which both texts mention anyway". Counted: `create_engine` **0/0**
  (neither text), `reset_engine` **0/4** (guard only), `_init_engine` 4/1, `_engine_url` 2/1. The conclusion
  is sound and measured; **the supporting list is wider than the texts** — this rule, inside a comment added
  to satisfy this rule.

**F-002 and F-003 corrected in the card body in this commit**, not only in the review sections: after-prose
**567 → 568**; "24 lines of code" → **25** (both sites); control B's docstring `63 → 48` → **`63 → 47`**;
the `session.py` row **64 / 4.44 → 63 / 4.51** with a footnote carrying the method correction and the
set-based statement (**86 code lines before and 86 after, unchanged**); and the residue's "three of its
sections" → **two of its three**, naming the third as the single source this card created. The cycle-2
reviewer's preferred wording is the footnote's.

**System contract: 10 checked — 3 ✓, 6 ⚠ `no_eligible_fact`, 1 ✗** (ADR-0039/R1 via F-006), all re-derived
rather than carried: ADR-0036/R4 (0 banned codepoints added; 3 tree-wide, all the declared U+2022 in
`pdf_generator.py`), R2, R3 (**9 sites / 6 pairs / dict-equal True / zero outside**). AC-5 re-derived: AST
dump **9154**, sha256 `bdb10905…`, identical on HEAD and main; `session.py` blob sha `a32bae5b` identical
across `HEAD~1..HEAD`, **0 files under `src/` in the fix delta**. **Seven more adversarial false positives
dropped**; the ledger stays at 13.

**[Family note — recorded, not escalated]** Cycles 1 and 2 both gated on **ADR-0039/R1**, in **the same test
function**, in **the same defect class**: a bare substring membership test whose claim some *other*
occurrence of the string satisfies. By `review.family_regression: on` that is one family. The detector's
other precondition is not met — F-006 is **not** attributed to the previous fix; it predates it
(`245bc898`) and fix 1 never touched `:887`. So this is not the loop feeding on itself, and escalating to
the decompose station would cost more than the remedy, which is known, small and already measured. Recorded
as a family because the shape is what matters: **this card's new control has a systematic defect across its
arms, and it is being found one arm at a time.**

**[Orchestrator defect, mine, and it is the reason the second arm survived]** My fix-1 brief named **one**
sibling to check — the heads arm at `:863` — and the fix checked exactly that one, correctly and
thoroughly. I never named the pointer arm. **A brief that enumerates one sibling gets one sibling checked;
a brief that names the defect class gets every arm checked.** Fix 2's brief asks for an arm-by-arm audit of
every membership test the card added, including the ones that turn out to be fine. That is the durable
form, and it is a rule for the fix station, not a note about this card.

**[Cycle budget]** Cycle 3 is the last (`max_cycles: 3`) and it certifies fix 2 — so the final edit does
**not** ship uncertified this time, which is what the wave-48 rule asks for. The cost is that a new
Important in cycle 3 leaves no cycle to fix it and escalates.

### [Fix 2] `daa721ae` — the pointer arm, and an arm-by-arm audit that enumerated the card's additions by AST

Commit `daa721ae` on `card/257-cut-the-guards-prose` (third commit, after `245bc898` and `df23bf64`),
pathspec `tests/test_db_engine_lifecycle.py` only — **1 file, +23/−10**, 1180 → **1193** lines.
`src/nonogram/db/session.py` is byte-unchanged (0 files under `src/` in the delta) so it was not passed.
Nothing under `meta/` in the commit.

**F-006 — fixed.** The pointer arm is now `pointer = app_session.reset_engine` /
`target = f"{pointer.__module__}.{pointer.__name__}"`. The fix derived **both** halves rather than quoting
`reset_engine`, which removes the last hand-written literal (**ADR-0039/R2**) and is strictly more
discriminating — it adds two kills the `__module__`-plus-literal form does not have, and changes none of
the four required readings.

| mutant | `:897` | post-condition |
| --- | --- | --- |
| **SHIPPED** | **PASS** | — |
| **POINTER-ROT** (both `:func:` references → a function that does not exist; `Controls` untouched) | **RED** | dotted-path occurrences 0, bare substrings **2** |
| **POINTER-DEL-WORD** (every whole-word `reset_engine` gone; `Controls` untouched) | **RED** | whole-word 0, substrings **1** — exactly the `Controls` method name |
| **CONTROLS-RENAME-ONLY** | **PASS** | dotted-path occurrences 2 |
| POINTER-DEL-WORD + CONTROLS-RENAME (cycle 2's 4th row) | RED | substrings 0 |
| *extra, from deriving `__name__`* — CODE-RENAME | **RED** | — |
| *extra, from deriving `__module__`* — MODULE-MOVE | **RED** | — |

**The arm-by-arm audit, and the part I want kept: the card's additions were enumerated by AST, not by
reading.** Parsing the file at `main` and at HEAD and collecting every `ast.Assert` containing an
`ast.Compare` with `In`/`NotIn` gives **main 2, HEAD 4** — so this card added exactly **two** membership
tests, the heads arm and the pointer arm. The other two are pre-existing. That is a derived answer to
"which membership tests did this card add", where my own brief had been guessing at siblings by name.

| arm | added here? | mutant | verdict |
| --- | --- | --- | --- |
| preamble `:859` `assert names` | no | NAMES-BLIND → **RED** | **fine** — not a membership test at all; a non-emptiness check on a derived set, so no "other occurrence" can satisfy it |
| names `:878` (word-bounded) | re-spelled by `df23bf64` | 6 `DOC-NAME-DEL` cells → **RED**; GLOBAL-ADD → **RED** | **fine as claimed** — the docstring says *"as a whole word"*, which is exactly what reds |
| heads `:889` | **yes** | 4 `DOC-HEAD-DEL` cells, SPELL/ASSIGN-HEAD-RENAME → **RED** | **fine, and cycle 2's conclusion re-verified rather than assumed** — the claim is *"this text shows the spelling"*, and any occurrence of `setattr(` literally is showing it, so no occurrence is "other" in a falsifying way |
| pointer `:897` | **yes** | POINTER-ROT, POINTER-DEL-WORD | **was the defect; fixed** |
| `:773` `"conftest" in doc` | no (on main, byte-identical) | occurrence count | **fine** — `conftest` appears exactly once in that docstring |
| `:994` exempt-site membership | no (on main) | — | **fine** — membership in a derived dict, not a "names X" claim |

**Two latents measured and deliberately declared rather than fixed**, both pre-existing with identical
verdicts before and after:

- **`AUDIT NAME-DEL-BACKTICKED[engine]`** — replace only the backticked ```engine``` and keep the bare
  English prose. Names arm **PASS** on both texts (backticked left 0; whole-word `engine` left 10 prod /
  1 guard, the latter being *"something retires its engine"*). So a **partial reword** of the enumeration
  would not red for `engine`, while `SessionLocal`/`_engine_url` would.
- **`AUDIT HEAD-DEL-FIRST[setattr(]`** — delete only the first, mechanism-describing occurrence. Heads arm
  **PASS**; `setattr(` left 5 prod / 3 guard.

Its stated reasons: neither over-states a **shipped** sentence, and cycle 2's certification instruction
requires the other three arms' rows be unchanged, so moving either arm on the last fix would ship
uncertified. Cycle 3 has been asked to judge this independently, with the consequence named: a gating
verdict there means escalation, not a fourth cycle.

**F-007 — fixed.** Recounted in the two texts the assert actually scans: `reset_engine` **0 prod / 4
guard**, `_init_engine` 4/1, `_engine_url` 2/1, `create_engine` **0/0**. `create_engine` appears **7×** in
`session.py`'s *source* and **0×** in either scanned docstring — so naming it invited the reader to believe
the scan sees something it cannot. The comment now names only `_init_engine` and `_engine_url` as *"both
texts mention"*, plus `reset_engine` as forced into the guard text by the pointer assert. The conclusion is
unchanged and still measured: prod 23 substring / 12 whole-word (**11 embedded**), guard 8 / 2 (**6
embedded**).

**Claims narrowed, including one the agent had introduced itself.** The control docstring's mutant row
`DOC-POINTER-DEL` becomes `POINTER-ROT` **or** `POINTER-DEL-WORD`, with a paragraph stating that the arm
tests the derived dotted path, that the class docstring carries `reset_engine` inside a control's own
method name which alone satisfied a bare substring test, and that renaming that method is therefore **not**
a lost pointer and does not red. The assert's message no longer says *"this class no longer points at the
convention's single source"* — true only under a mutant that deletes the method name too. And on its first
pass the agent wrote "this docstring" where the arm reads the **class** docstring; it caught and corrected
that in the same fix.

**A fourth form of the board's instrument trap, caught by the agent in its own work.** Its first post-fix
run showed `GLOBAL-ADD` and all four audit mutants reddening the heads arm — a surprising red. Re-run solo:
its `run()` restored `_global_names_assigned_by` and `_spelling_heads` but **not** `_hand_set_spellings`,
so an earlier patch **leaked into every later mutant**. **A leaked patch and a real kill look identical.**
The remedy is to verify SHIPPED comes back all-PASS *between* mutants, not only at the start.

**Guardrails re-derived:** `session.py` AST dump **9154**, sha256 `bdb10905…` unchanged; **0** banned
codepoints among the 23 added lines and **3** tree-wide, all U+2022 in `pdf_generator.py` (the declared
exemption); AC-5 tree sweep **9 sites / 6 pairs / dict-equal True / 0 outside** the two exempt files, and
`_EXEMPT_HAND_SET_SITES` appears **0** times in the diff; G-1 the two regexes, counter, dict and equality
untouched; G-2 13 tests before and after; G-4 stdlib only, no new import.

**My corrections to the card, done:** the AC-2 matrix is **superseded in place** — the `245bc898` table is
kept as the record of what was actually measured then, annotated with the two rows later refuted
(`DOC-NAME-DEL` at cycle 1, `DOC-POINTER-DEL` at cycle 2), and the current table at `daa721ae` is written
beneath it with all four arm line numbers restated (`:859 / :878 / :889 / :897`). F-002 and F-003 were
corrected in the card body earlier.

**[Three independent instruments on one card]** fix 1's, cycle 2's, and fix 2's — each written from
scratch, none re-using another's, and **each found a different defect the others' shape would have hidden.**
That is now the strongest argument on the board for *commit the instrument once, as its own card*: not
because writing it is expensive, but because four distinct ways to get it wrong have been discovered in one
wave, and nothing in the tree remembers any of them.

### [Review 3/3] Score: 9.0 — ✓ threshold reached, 0 Critical, 0 Important. Clear for the merge gate

Report: `meta/review/CARD-257-cycle3.yml`. Every prior finding carried forward with a real `fixed_in:` —
F-001/F-004 → `df23bf64`, F-006/F-007 → `daa721ae`, **F-002/F-003 → `a05d88db`** (the reviewer located my
card-body correction commit rather than leaving a null), F-005 `wontfix`, carded to CARD-259. One new
**Minor**, F-008, corrected in this commit. **ADR-0039/R1 moves from ✗ to ✓**; contract 10 checked, 4 ✓,
6 ⚠ `no_eligible_fact`, **0 ✗**.

**Arm line numbers derived from the unmodified parse, nothing reused:** `:859 / :878 / :889 / :897`. And a
correction to my own trap warning — the NAMES-BLIND assert source line occurs **five** times in the file
(`:816, :859, :914, :960, :1087`), not four; the extra is `:816` in
`test_it_resets_exactly_the_globals_the_builder_creates`. Every assert was keyed on its own `lineno` lifted
as a literal, so no by-text or first-occurrence targeting was used anywhere.

**The pointer arm: all four required readings plus both extras.** SHIPPED **PASS**; POINTER-ROT **RED**;
POINTER-DEL-WORD **RED**; CONTROLS-RENAME-ONLY **PASS**; CODE-RENAME **RED**; MODULE-MOVE **RED**. All three
post-conditions exact (ROT → dotted 0 / bare substrings 2; DEL-WORD → whole-word 0 / substrings 1, precisely
the `Controls` method name; CONTROLS-RENAME-ONLY → dotted 2). **Re-derived a second time with no instrument
at all**, by compiling `target in guard` straight out of the AST at `:897` and evaluating against mutated
guard strings — identical. And the one-mutant-is-not-enough point reproduced on a candidate: a word bound
`\breset_engine\b` **passes** POINTER-ROT and reds only POINTER-DEL-WORD, where the derived dotted path reds
both.

**The other three arms' rows are unchanged**, with the raw pre-aggregation lists recorded: the PROD name
cells are `['RED','PASS']` and the GUARD cells `['PASS','RED']` — **ANY-RED is doing real work**, again.

**ADR-0039/R2 holds and the derivation is load-bearing, not relocated** — measured: CODE-RENAME and
MODULE-MOVE both red, and neither would have been caught by the `__module__`-plus-quoted-literal form. One
domain note the reviewer added rather than glossed: a bare rename makes `app_session.reset_engine` raise
`AttributeError` one line earlier, so the *realisable* form of CODE-RENAME is a rename **with an alias or
re-export left behind** — which is exactly the stale-docstring drift the claim is about. Fail-closed either
way, never a silent pass.

**The two declared latents: the declaration is honest, neither gates.** L-1 (`AUDIT
NAME-DEL-BACKTICKED[engine]`) leaves the names arm PASS with backticked occurrences 0 and whole-word
`engine` at 10 prod / 1 guard — **the PASS is the claim being true, not a control failing to fire**, since
the text still names the global as a whole word, which is exactly what the row asserts. L-2 (`AUDIT
HEAD-DEL-FIRST`) leaves `setattr(` at 5 prod / 3 guard, and a text with 5 occurrences still *shows* the
spelling; nothing shipped claims an occurrence count. The reviewer adversarially tested the one strained
reading that could make L-1 gating — F-004's clause *"reword one of the three away and that control reds,
per name"* — and refuted it on the clause's own scope. Both go to CARD-259, which already takes these texts.

**A third latent found and recorded, not filed (L-3):** `target in guard` is still a substring test, so an
identifier strictly *extending* the dotted path (`…reset_engine_pool`) would satisfy it without being a
pointer. Measured: **0** such occurrences in the guard text, 0 in the production text, **0 anywhere under
`src/` or `tests/`**. F-006's defect had a live carrier; this one has none, so it is a measured bound rather
than a finding. A right lookahead closes it and stays PASS on SHIPPED — cheap, added to CARD-259.

**F-008 (Minor, corrected in this commit)** — `CARD-257.md:388` said *"the AC-2 control holds the guard's
text to the names **in double backticks**, which the scan does not count"*. Read descriptively that is a
true compression of the control's docstring; read as what the control **enforces** it is false, and measured
so: `AUDIT NAME-DEL-BACKTICKED[engine]` leaves the names arm PASS with backticked occurrences at 0. The arm
reads a **word-bounded bare name anywhere in the text**; the backticks are irrelevant to it. **I had written
that compression at three sites and all three are now corrected** — same class as F-002/F-003, and the same
lesson: a sentence I wrote to summarise a control became a claim about the control.

**My card-body corrections: none is wrong.** All five re-derived with the reviewer's own `ast`+`tokenize`
split, computing **both** methods side by side rather than re-running the card's defective formula —
after-prose 568 ✓; `+25` ✓; control B docstring 63→47 ✓ (and control A 125→107 / 37→30, class docstring
116→59 also hold); the `session.py` row 63 / 4.51 ✓ (the card's own formula gives 393−284−46 = 63, and
284/63 = 4.51), with the footnote's set-based **86 before and 86 after** ✓ and the guard file's 494 → 521 ✓;
the residue's "two of its three" with the third named correctly ✓. The restated AC-2 matrix and the four arm
line numbers match the reviewer's grid cell for cell.

**Guardrails, all re-derived:** `session.py` byte-unchanged (0 files under `src/`, blob `a32bae5b` identical
across `daa721ae^..daa721ae`); AST dump **9154**, sha256 `bdb10905…`, identical on HEAD and main; tree sweep
**9 / 6 / True / 0**; **0** banned codepoints among the 23 added lines and **3** tree-wide, all U+2022 in
`pdf_generator.py`; G-4 `pyproject.toml` untouched, no import added. **G-2 with its domain stated, which is
the habit this wave built:** no `def test_` added or removed in the delta, **13 passed / 0 skipped** at both
shas — and *13 is a pytest collection count*, where the file holds **15** `def test_` occurrences, two of
them inside embedded probe strings, the same 15 at both shas.

**[A fifth form of the instrument trap, caught by the reviewer in its own work]** Its first head-deletion
mutant deleted the literal `.SessionLocal` and returned only **2 of 4** cells RED. Re-run solo: **neither
raw text contains that literal** — both write `.<name>` once and the arm substitutes the placeholder before
scanning. So the faithful mutant must delete the head **as the text shows it**, placeholder form included;
with that, all four cells red, each carrying a post-condition that the substituted text genuinely no longer
shows the head. **A no-op mutant and a surviving mutant look identical** — exactly like a leaked patch and a
real kill. The leak hazard itself was handled: a fixed snapshot of all six patched attributes restored after
every mutant, and SHIPPED re-run all-PASS **between** mutants, all 22 times.

**Eight adversarial false positives dropped**; the board's ledger stays at 13.
