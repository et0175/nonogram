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
