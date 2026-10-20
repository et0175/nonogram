# CARD-254: Shrink CARD-252's private-globals guard to the part that has authority

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/254-shrink-the-private-globals-guard
**Worktree:** ../PythonProject4-card-254
**Source:** CARD-252 review cycle 3's direct answer to "is this guard worth keeping at all?" — *"No, not at this size. I'd keep about a fifth of it."*
**Idea:** —
**Wave:** 49
**Depends on:** — (CARD-252 is merged; this card edits what it shipped)
**Touches:** tests/test_db_engine_lifecycle.py, src/nonogram/db/session.py (docstring only), meta/architecture/ — no
**Review score:** —
**Started:** 2026-10-20T05:15:11Z · **Closed:** — · **Actual:** — · **Merge commit:** —
**Blocked by:** —

## Why

CARD-252's AC-5 guard — "no test reaches into `session.py`'s private globals" — cost **three review
cycles, nine helpers, ~180 lines of AST machinery, ~220 lines of docstring claims and eleven
controls**, and caught **zero real violations**: the nine sites it reports are the nine it was
written around, and a full-tree triage found nothing new (0 unanalysable, 2 declared residual, 328
correctly out of scope). Every gating finding on that card was the guard's description of itself.

The final reviewer's reason is the one to carry: **a convention enforced at review is honest about
being a convention; an AST deny-default is a *proof* claim, and a proof claim in a dynamic language
always has one more axis.** That card paid three cycles to learn it at one axis per cycle —
spellings, then argument binding, then (measured at zero sites) computed targets.

This card is not a retraction of CARD-252. The engine fix merged with zero production delta and is
not in question. What shrinks is the guard around it.

## What to implement

**Keep (~55 lines — the part with real authority):**
1. `_global_names_assigned_by` + `test_it_resets_exactly_the_globals_the_builder_creates` — the one
   genuinely *derived* authority in the file, so a fourth global added to `_init_engine` tomorrow is
   inside the check that day. Cycle-1 mutant R4 killed it; keep that control.
2. The AST call-site test and the public-seam test (M1/M1b kill them).
3. The exemption **equality**, reduced to a cheap per-file **textual** count of the three literal
   global names. It still reds on a new file, a new name or a tenth site — and it makes **no claim
   about reach**, so there is nothing left to probe.

**Retire (~400 lines of code and prose):** `_is_setattr_call`, `_string_target_tail`,
`_string_target_module`, the arity dispatch, the binding-frontier helpers and the five shape
controls — replaced by a declared convention in `session.py`'s docstring and one line in the
engineering standards: *tests do not hand-set `session.py`'s engine globals;
`test_db_url_driver.py` and `test_db_connect_timeout.py` are the recorded exceptions; a new one is a
card, not a commit.*

## Acceptance criteria

- **AC-1** *Given* the reduced guard, *when* a test in a new file hand-sets one of the three engine
  globals, *then* the guard reds and names the file. (test: the kept exemption-equality test)
- **AC-2** (the control) *Given* the kept derived check, *when* a fourth global is added to
  `_init_engine`, *then* `test_it_resets_exactly_the_globals_the_builder_creates` reds with the name.
  (test: the same, under the R4 mutant — recorded on the card)
- **AC-3** *Given* the retirement, *then* **every** retired test is named with its survivor or
  recorded as deliberately unreplaced with the reason. A reach the new guard cannot see is stated in
  the convention, not left implicit. (test: the card's own retirement table + G-6)
- **AC-4** *Given* the new convention text, *then* it says what it does **not** enforce. The failure
  this card exists to end is a guard whose claim is wider than its mechanism; a convention that
  claims to be a guarantee repeats it in prose.

## Guardrails

- G-1: `src/nonogram/db/session.py` keeps `reset_engine()` and its call site unchanged — **docstring
  edits only**. Prove it the way CARD-252's cycles did: docstring-stripped AST identical.
- G-2: No test is made to skip. The suite's skip profile is unchanged (1 on this machine).
- G-3: No test retired without a named survivor **or** an explicit "deliberately unreplaced, because
  …" line on the card.
- G-4: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-5: No new runtime dependency (ADR-0006/R1).

## Worktree notes

- **[Do not take timing measurements]** other cards share this machine.
- **[The trap]** This card *removes* a control. The failure mode is removing the part that had
  authority and keeping the part that was decorative. The kept list above is not a suggestion: it is
  what cycle 3 measured as load-bearing (R4 kills the derived check; M1/M1b kill the call-site test;
  the exemption equality reds on a tenth site). Anything you keep beyond it needs its own killing
  mutant, and anything you drop from it needs an argument.
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`.

## System contract

Curated to **10 of 29** in-scope rules under `meta/kanban/curation.md`: every rule whose
enforcement does not reach this card's new code is kept; the rest are dropped because the suite runs them
on every gate. **19 dropped.**

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
