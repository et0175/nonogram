# CARD-032: Restrict web form to image-only mode

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.25d _(the feature shipped outside the board; what is left is two tests and a naming repair)_
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/032-image-only-mode
**Worktree:** —
**Source:** User feedback post-CARD-021
**Idea:** —
**Wave:** —
**Depends on:** CARD-021
**Touches:** tests/test_web_server.py (the two missing tests), tests/test_export_pdf.py (the citation repair), meta/kanban/cards/CARD-032.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Re-cut 2026-09-21 — the feature is on main; the card never closed

Checked against `main` at `2a8f5c7` before re-opening, the way CARD-067 and
CARD-068 had to be. **The form is already image-only.** `web/pages.py` says so
in three places — *"CARD-032 restricted the form to image mode only: no source
dropdown, no …"* — and `tests/test_web_server.py` carries
`TestWebForm_OnlyOffersImageMode`, the class this card names for AC-128, with
four tests: no source dropdown, no library-key field, no density field, and
the image and size fields present.

So **AC-128 is delivered and covered**. What is actually left is smaller and
less interesting than the card, and one item is not about the web form at all.

### AC-129 holds, but nothing tests it

Measured today. A submission with no file builds a request with `image=None`
and fails inward:

```
submission.read("size=20").request     -> image=None, mode='image'
orchestrator.generate(that)            -> UnreadableImage:
        image mode needs an --image PATH pointing at the picture to convert
```

Which is the right answer and the documented design — the adapter carries no
domain validation (ADR-0019/R1), so "no file chosen" fails where every other
bad request fails. But `TestWebForm_RequiresImageForSubmission` does not
exist, and no web-level test covers it. The behaviour is one refactor away
from silently changing.

### AC-130 has no test either

`TestWebForm_GeneratesIdenticallyToMultiMode` does not exist. The parity it
describes is largely structural — the adapter builds the same
`GenerationRequest` it always did, and G-1 forbade touching the domain — so
the honest version of this criterion is a test that the *request built from a
form submission* is the one the CLI would build from the same arguments, not
a second end-to-end generation.

### The card number is ambiguous, which is the real finding

`tests/test_export_pdf.py` attributes a **bundled font face** and a Cyrillic
PDF header to CARD-032, in four places, including a section header:

```
# CARD-032 / ADR-0006 revision — the header sets a non-ASCII name
#   TestPdfHeader_RendersCyrillicName
```

That is a different body of work from this card, which is about a web form and
touches no PDF code. ADR-0006 is the dependency baseline. Git history cannot
disambiguate them — the card file arrived in one bulk commit (`7e4ad0a`) and
the PDF comments in another (`96da6ac`) — so one number names two things and
the board documents only one of them.

**Also:** this card's AC-128 / AC-129 / AC-130 collide with FR-028's AC-128
and AC-130, which CARD-078 implemented on 2026-09-21 and which mean entirely
different criteria. Two numbering schemes are in use and they have met.

## What to implement

1. **Write the AC-129 test.** A form submission with no file chosen is
   refused through the domain's own error, and the failure page carries that
   message (EC-003's shaping is unchanged). Name it
   `TestWebForm_RequiresImageForSubmission`, as the card always said.
2. **Write the AC-130 test, as parity of the request rather than of a
   generation.** The request built from a form submission matches the one the
   CLI builds from the same arguments. A second end-to-end generation would
   test the solver, which is not what this criterion is about and is covered
   many times over.
3. **Resolve the number.** Decide which body of work CARD-032 names, and fix
   the citations in `tests/test_export_pdf.py` so the PDF font work points at
   whatever card actually authorised it — or, if none did, say so there rather
   than crediting a card that did not.
4. **Record the AC-number collision** in the card, so the next person to read
   "AC-128" knows to ask which one.

### Superseded statement of intent, kept as the record

The web UI form currently offers three sourcing modes: random, library, and image. However, the image upload feature (CARD-021) is the unique value proposition of the web UI — the CLI already covers random and library. Simplify the form to offer **image mode only**, removing the random and library options.

This reduces cognitive load and signals to users what the web UI is for. The CLI remains the way to generate via random or library sourcing.

## Acceptance criteria

- **AC-128** (scope) — given the form page, when it loads, then the "Source" dropdown is gone and the form assumes image mode implicitly (file upload required, image metadata displayed, no size/density/library-key fields relevant to random/library).
  *test:* `TestWebForm_OnlyOffersImageMode`

- **AC-129** (validation) — given a form submission with no file uploaded, when the form is submitted, then the handler returns an error (missing image file) with the same path as if mode validation had failed in the domain.
  *test:* `TestWebForm_RequiresImageForSubmission`

- **AC-130** (parity) — given the web form in image-only mode, when a valid image and size are submitted, the generation pipeline behaves identically to the multi-mode version (same sourcing, same clue derivation, same solver — only the UI offering changed).
  *test:* `TestWebForm_GeneratesIdenticallyToMultiMode`

## Guardrails

- G-1: No changes to the domain (orchestrator, sourcing, handler logic) — UI-only
- G-2: The urlencoded submission path (used by tests) must still work unchanged
- G-3: All three modes remain equally supported at the CLI level (no regression)

## Architecture context

- **FR:** FR-017 (web UI)
- **NFR:** NFR-003
- **ADR:** ADR-0019 (adapter scope), ADR-0020 (no new deps)
- **Components:** COMP-008 (web UI only)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
