# CARD-319: The dead-ref detector asks "is this name mentioned?" where it means "is this defined?" — and never asks it of ADR rules at all

**Status:** blocked
**Priority:** P1
**Category:** tech-debt
**Estimate:** — (not estimable from this repository; see "Why this is blocked")
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-307's fourth premise re-measurement, 2026-10-29, plus seven measured instances of the mention-resolves-as-definition hazard accumulated across CARD-218, CARD-284, CARD-285, CARD-291, CARD-298, CARD-308 and the orchestrator's own sync. CARD-307 was cut; this is the successor carrying its item 5. Cut by the orchestrator on owner decision.
**Idea:** —
**Wave:** —
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** —
**Touches:** /Users/omelnikova/MyProjects/forge_1/forge/skills/architect-validate/ — **outside this repository**
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** owner decision — the code to change is in `forge_1`, not in this repo, and this board has a standing rule never to edit anything under it.

## Why this is blocked, and why it is still worth a card

The repair is two changes to the architecture validator. That validator lives in
`/Users/omelnikova/MyProjects/forge_1/forge/skills/architect-validate/`, which **this
board does not edit**. The card exists so the defect is *recorded with its evidence*
rather than rediscovered a ninth time, and so the owner can decide where the fix
belongs: upstream in `forge_1`, as a project-local override, or not at all.

**Six cards have already paid for this defect one route at a time.** That is the
signal: six measured routes and a seventh latent one are not seven problems — they
are one predicate with seven doors.

## Defect 1 — a text search standing in for a definition check

`symbol_exists()` resolves a check ref with
`git grep -lw <ref> -- . ':(exclude)meta/architecture' ':(exclude)*.md'`.
A ref is "alive" if the name is **mentioned anywhere outside the model and the docs**.
It is supposed to mean **defined**.

Every instance below was measured on this board. Each was closed individually, by a
different card, by excluding or rewording one resolver:

1. A **synced review YAML** silencing a live warning (108 → 107).
2. A reviewer who **knew the rule**, split a token to avoid it, and tripped anyway.
3. **`meta/kanban/dispatcher.state`** — no `.md` extension, so inside the search domain.
4. A **round's own report** resolving the ref it was reporting dead.
5. The orchestrator's sync, which **checked the file for the wrong hazard** and never
   checked it for dead refs.
6. **`player/assemble.py`** and sibling *code* files resolving a ref defined in neither.
**And one LATENT route, measured as a shape rather than as an instance:**

7. A **test written to track not-yet-written tests**. `tests/test_public_player_pages.py`
   spelled three test names inside a `card_285` set whose assertion was
   `refs - defined == card_285` — a set existing in order to record that those tests
   were *not* defined. Had the model declared those refs as **bare names**, that set
   would have made the validator read all three as checked.
   **It did not, and the distinction is the point**: the model declares them as
   **node ids** (`requirements.yml:5233/:5239/:5245`), and `git grep -lw` on a
   `path::name` string cannot match a bare name. Measured per ref on `main`, each has
   **exactly one** resolver — the synced CARD-285 cycle-1 review YAML — and no
   definition anywhere.
   So route 7 is **inoperative here, and that is an argument for the node-id
   migration**, not against it. It is recorded because the shape is real and nothing
   prevents the next instance: a legitimate tracked test file, doing a legitimate
   thing, that no exclusion list would catch.

**The repair is small and local:** resolve a ref by parsing for a `def`/`class` of that
name, and keep the text search only as a fallback for refs that are not Python
symbols. This project already does exactly that —
`tests/test_public_player_pages.py` walks `ast.parse(source)` for `FunctionDef` — so
the technique is proven in-tree. It would retire all seven routes at once and make
most of the exclusion pathspecs unnecessary.

## Defect 2 — ADR rule check refs are never checked

Measured on the validator of record at `main` (`0 error(s), 100 warning(s)`): **not one
warning concerns an ADR rule's `check: {kind: test, ref: …}`.**
`TestDependencyBaseline_IsExactlyPillowAndNumpy` — ADR-0006/R1's ref, with **zero**
definitions in this repository — appears **nowhere** in the output. Neither does any
other ADR rule ref. The dead-ref check covers AC/EC `test:` keys in
`requirements.yml` and stops there.

**This is why twelve cards carry a hand-written `**DEAD REF**` note** in their System
contract sections — CARD-285, 291, 298, 306, 308, 309, 310, 311, 312, 313, 314, 315.
Humans have been doing a gate's job by hand, card after card, and a card that forgets
simply ships with a phantom pointer.

Note the two defects compound: ADR-0006/R1's phantom name is **text-present in two
tracked test files**, so even if ADR rule refs *were* checked, defect 1 would resolve
it falsely. Fixing either alone leaves this ref reading alive.

## What to implement — once the owner decides where

1. **Decide the venue and record it**: upstream `forge_1`, a project-local validator
   override, or accept-and-document. **A shim that is never labelled becomes the end
   state by default** — that was CARD-307's item 5, and it is restated here because
   its card was cut before answering it.
2. **Defect 1**: resolve `kind: test` refs against a parsed definition; fall back to
   the text search only for non-Python refs, and say in the output which mode resolved
   each ref so a fallback is visible rather than silent.
3. **Defect 2**: extend the dead-ref check to ADR rule `check:` entries, with the same
   warning text and the same `review-lens` escape hatch.
4. **Re-measure the board afterwards.** Expect the count to **rise** before it falls:
   refs currently resolving on a mention would become honest dead refs. **That rise is
   the point** and must not be read as a regression — it is the first honest number
   this board has had.
5. **Retire what the fix obsoletes**: the per-module docstring node-id tables
   (CARD-291's and CARD-294's shape) exist only to give a text search something to
   find. They were always a shim. Say whether they stay or go.

## Acceptance criteria

*(Provisional — this card cannot be built until step 1 resolves the venue, and the ACs
below assume the repair lands somewhere this board can verify.)*

- **AC-1** (a mention no longer resolves): *Given* a ref whose name appears in a
  tracked file but is defined nowhere, *then* the validator reports it dead. Verified
  against **all seven routes above**, each as its own case — an exclusion list that
  happens to cover six is not a fix.
- **AC-2** (ADR rules are checked): *Given* an ADR rule check ref with no definition,
  *then* the validator warns, with the same text and the same `review-lens` escape as
  an AC ref.
- **AC-3** (the fallback is visible): *Given* any ref resolved by text rather than by
  definition, *then* the output says so, so a silent fallback cannot be mistaken for a
  definition.
- **AC-4** (the honest number is recorded): *Given* before and after, *then* both
  counts are reported with the **sets** diffed line by line, and the rise is explained
  ref by ref rather than summarised.
- **AC-5** (the twelve notes are resolved): *Given* the fix, *then* the hand-written
  `**DEAD REF**` notes on the twelve cards are either true or removed, and no card
  carries a note describing a check the gate now performs.

## Guardrails

- **G-1: never edit anything under `/Users/omelnikova/MyProjects/forge_1/`** without
  the owner's explicit instruction. This is a standing rule on this board and it is
  the reason this card is blocked rather than ready.
- **G-2: do not "fix" defect 1 by lengthening the exclusion list.** Six cards have
  tried one exclusion each; route 7 shows the approach does not terminate, because the
  next resolver is an ordinary tracked test file doing an ordinary thing.
- **G-3: do not suppress the post-fix rise.** A number that gets worse for an honest
  reason is the deliverable, not a problem to tune away.
- **G-4: name the validator binary beside every figure.** The plugin-cache copy
  reports a phantom `[ERROR] ADR-0025 circular supersession` from a regex bug counting
  "supersedes" and "superseded by" as two edges; the two copies' `validate.py` are
  byte-identical and `validators/adr_integrity.py` is the only differing source file.
  The copy of record is the `forge_1` one named in `meta/kanban/config.yml`.
- **G-5: `\b` is undefined in POSIX ERE and silently matches nothing**; `_` is a word
  character, so `git grep -w PropertyTest_Foo` misses `def test_PropertyTest_Foo`. Any
  instrument written for this card must be proven in both directions first — it finds
  a name known to exist and rejects a nonsense one. Both traps were hit while
  measuring this card's own evidence, and both produced clean-looking results.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0006/R1 — the dependency baseline (check: **the ref is a phantom pointer AND an instance of defect 1 — text-present in two tracked test files, so it would resolve falsely even under defect 2's fix**; the RULE is tested at `tests/test_export_pdf.py:1249`, and the in-repo pointer repair is **CARD-317's**)

## Architecture context

- **ADR:** ADR-0039/R2 (derived sets), and the `adr-check-refs-must-be-honest`
  principle this board has been applying by hand.
- **Components:** none in `src/` — the subject is the validator, which is not part of
  this repository.
- **Trace:** nothing is re-stamped by this card. Its effect on `trace.yml` is indirect
  and arrives as a changed warning set.
