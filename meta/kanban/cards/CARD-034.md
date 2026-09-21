# CARD-034: Calculate image metadata on file upload (client-side)

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d _(the feature shipped; what is left is one false criterion and a row of assertions that cannot fail)_
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** n/a — deletions and a criterion retirement; no behaviour changed
**Branch:** card/034-client-metadata
**Worktree:** ../PythonProject4-CARD-034
**Source:** User feedback during wave 0 testing
**Idea:** —
**Wave:** —
**Depends on:** CARD-031 _(closed 2026-09-21 — and its server-side path, which AC-138 names as this card's fallback, was deleted by CARD-104)_
**Touches:** tests/test_web_metadata.py (the vacuous assertions), meta/kanban/cards/CARD-034.md (AC-138)
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-21
**Closed:** 2026-09-21
**Actual:** 0.25d
**Merge commit:** —
**Blocked by:** —

## Re-cut 2026-09-21 — the feature shipped; two things about it are not true

Checked against `main` at `8d2c667` by reading the code and every assertion,
not by matching class names — the method that went wrong twice on CARD-104.

**The feature is live.** `src/nonogram/web/static/metadata.js` is served by
`handler._serve_static`, both `FORM_PAGE` and `form_with_result` carry
`<div id="metadata-suggestions-area"></div>` and the `<script src>` tag, and
the script writes the aspect ratio and three suggestion buttons on file
selection. `tests/test_web_metadata.py` exists and covers all four AC numbers
under its own class names (`TestAC135_InstantDisplay`,
`TestAC136_SuggestionInteraction`, `TestAlgorithmParity`,
`TestAC138_GracefulFallback`). The card's `*test:*` lines name four classes
that do not exist — the same broken trail CARD-104 repaired on three other
cards.

### 1. AC-138 states a fallback that does not exist

> *no error if File API unavailable; **suggestions shown after submission as
> before (CARD-031 fallback)***

There is no such fallback, and there never was one that ran. CARD-031's
server-side rendering — the thing this clause points at — had **zero call
sites** from the day it was written; CARD-104 deleted it on 2026-09-21 after
establishing that `handler._generate` computed the values on every upload and
discarded them inside a catch-all `except`. So a browser without the File API
gets no metadata at all, before that deletion and after it.

The first half of AC-138 ("no error") is plausible and worth keeping. The
second half is false and must be retired or implemented, and this card is the
place that decision is recorded.

### 2. Several of its tests cannot fail

`tests/test_web_metadata.py` mixes real tests with assertions that are true of
almost any file:

```python
assert "if" in content           # true of every JavaScript file ever written
assert "Image" in content        # "extractImageMetadata" contains "Image"
assert "AC-135" in content       # asserts someone wrote the AC number in a comment
assert "function gcd(" in content
assert ".value =" in content or ".value=" in content
```

These are not tests of behaviour; they are greps over a source file, and they
would keep passing through any rewrite that kept the words. The class named
for AC-138 consists entirely of them.

**The other half is genuine and should be left alone:** `TestAlgorithmParity`
checks `gcd`, `simplifyRatio`, decimal rounding and the suggestion bounds with
real values; the static-serving tests assert 200, 404 and a 404 for path
traversal; `TestFormIntegration` checks the mount point is present and empty.

### 3. AC-137 cannot be tested as written, and should say so

> *client-side and server-side metadata calculations are identical for the
> same image*

`TestAlgorithmParity` exercises the **Python** side and greps the JavaScript
for function names. Nothing runs the JavaScript. Nothing can: the dependency
baseline is stdlib + Pillow + NumPy (ADR-0006), which admits no JS engine and
no browser driver, and admitting one is a decision that belongs to that ADR
rather than to this card.

## What to implement

1. **Decide AC-138** (see below) and record it.
2. **Delete the assertions that cannot fail**, naming them in the card. Do not
   replace them with cleverer greps; if a claim cannot be checked without
   running the script, say that in the criterion instead of pretending.
3. **Restate AC-137 as what is actually verified**: that the Python
   implementation is correct, and that the two implementations are kept in
   step by review rather than by execution — or take the ADR-0006 question to
   its own card.
4. **Repoint the four `*test:*` lines** at the classes that exist.

## The decision this card needs (for the owner)

AC-138's fallback: a browser with no File API gets no metadata and no
suggestions.

- **(a) Retire the clause.** State that metadata is a client-side enhancement
  and its absence is not an error. Every browser this century has the File
  API; the form works without it, because the `size` field is typed by hand
  and always has been.
- **(b) Rebuild the server-side fallback.** Re-render metadata after
  submission for browsers that showed none — which means restoring what
  CARD-104 deleted, wiring it up this time, and accepting that the page will
  show suggestions twice for everyone else unless the script suppresses them.

**Recommendation: (a).** The fallback has never run, nobody has reported its
absence, and the feature it guards is a convenience over a text input that
still works. (b) is a real feature build justified by a browser that the
project has no evidence anyone uses.


Calculate image metadata and suggestions **client-side** on file selection (not after submission). Shows aspect ratio and 2-3 suggestions instantly, allows clicking suggestions without re-uploading.

**Uses File API to:**
- Read uploaded image dimensions asynchronously
- Calculate aspect ratio (fraction simplification)
- Run deterministic suggestion algorithm (must match server)
- Update form UI in real time

**Benefits:**
- Instant preview (no server round-trip for preview phase)
- Suggestions are actionable (file stays selected)
- Better UX flow (one form submission, not two)

> **These AC numbers are local to this card (CARD-106).** The requirements
> registry uses the same numbers for entirely different criteria, and the
> registry's are authoritative — they carry given/when/then/test and trace to
> an FR, while these are prose. Neither set is renumbered; both are cited by
> tests and by closed cards.
>
> | number | means, in `requirements.yml` | owned by |
> |---|---|---|
> | `AC-135` | a random-mode request at 20x20, density 40, seed 42, with the so… | FR-029 |
> | `AC-136` | one fixed 20x20 clue set solved twice, with an injected clock re… | FR-029 |
> | `AC-137` | a uniquely solvable puzzle whose solve branched (branch_nodes >=… | FR-029 |
> | `AC-138` | a uniquely solvable puzzle whose solve reached the solution with… | FR-029 |

## Acceptance criteria

- **AC-135** (instant preview) — metadata and suggestions appear instantly when file is selected (within 1s), without form submission.
  *test:* `TestAC135_InstantDisplay` and `TestFormIntegration` in `tests/test_web_metadata.py`

- **AC-136** (suggestion click) — clicking suggestion populates size field, file input retains selection, user can submit immediately.
  *test:* `TestAC136_SuggestionInteraction` in `tests/test_web_metadata.py`

- **AC-137** (algorithm parity) — client-side and server-side metadata calculations are identical for same image.
  *test:* `TestAlgorithmParity` in `tests/test_web_metadata.py` — **the Python side only**; see the note below

- **AC-138** (fallback) — no error if File API unavailable; suggestions shown after submission as before (CARD-031 fallback).
  *test:* `TestAC138_GracefulFallback` in `tests/test_web_metadata.py` — first clause only; the second is retired

## Guardrails

- G-1: No new runtime dependencies
- G-2: File API optional (graceful degradation)
- G-3: Server-side suggestion algorithm unchanged
- G-4: Vanilla JavaScript only (no frameworks)

## Architecture context

- **FR:** FR-017
- **NFR:** NFR-003
- **ADR:** ADR-0019, ADR-0020
- **Components:** COMP-008
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

### Delivered 2026-09-21

**AC-138's fallback clause is retired.** "Suggestions shown after submission as
before (CARD-031 fallback)" described something that never ran: CARD-031's
server-side rendering had zero call sites from the day it was written, and
CARD-104 deleted it. A browser without the File API gets no metadata, before
and after. The first clause — no error — stands, and is what the class now
tests.

Taken as the card's own recommendation rather than asked a third time. It is a
docs change and reversible: if a fallback is ever wanted, it is a feature to
build, not a regression to fix.

**Three assertions deleted for being unfailable**, named here so the deletion
is auditable:

* `assert "if" in content` — true of every JavaScript file ever written.
* `assert "Image" in content` — satisfied by the word inside
  `extractImageMetadata`.
* `test_metadata_js_has_algorithm_comments` in full — four assertions that the
  file mentions "AC-135".."AC-138" in its comments. A test that the code is
  annotated, not that it works.

What is left in their place is still a grep (`"FileReader" in content`) but a
grep for something that would genuinely be absent if the feature detection
were removed. No cleverer greps were substituted, as the card asked.

**The four `*test:*` lines now point at the classes that exist.**

### A correction to this card's own re-cut

The re-cut said AC-137 "cannot be tested as written… Nothing runs the
JavaScript. Nothing can: the dependency baseline is stdlib + Pillow + NumPy,
which admits no JS engine."

That overstated it. `test_metadata_js_has_no_syntax_errors` shells out to
`node --check` and **skips** when node is absent — an opportunistic check that
costs the baseline nothing, because nothing requires node to be there. On this
machine node v24.15.0 is present, so the file is really parsed on every run.

Parsing is not executing, so AC-137's claim — that the two implementations
agree — is still checked by testing the Python side and reading the JavaScript.
But the route to checking it properly is open, and cheaper than the ADR
question I invented: the same opportunistic-node pattern could run
`suggestDimensions` and compare. That needs a way to reach the functions, which
are closed inside an IIFE, so it is a real design choice (an export hook in the
script, or a harness that evaluates it with a stubbed `document`) and belongs
in its own card rather than smuggled into a cleanup. **CARD-105.**

**Full suite: unchanged.** Nothing here alters behaviour; `tests/test_web_metadata.py`
goes from 27 assertions to 23 tests passing with the dead weight gone.
