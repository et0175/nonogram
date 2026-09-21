# CARD-032: Restrict web form to image-only mode

**Status:** review
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.25d _(the feature shipped outside the board; what is left is two tests and a naming repair)_
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** n/a — the feature shipped; the work is recovering its two missing tests
**Branch:** card/032-image-only-mode _(the 2026-09-03 branch of the same name is retired as `card/032-superseded-2026-09-03`)_
**Worktree:** ../PythonProject4-CARD-032
**Source:** User feedback post-CARD-021
**Idea:** —
**Wave:** —
**Depends on:** CARD-021
**Touches:** tests/test_web_server.py (the two missing tests), tests/test_export_pdf.py (the citation repair), meta/kanban/cards/CARD-032.md
**Review score:** —
**Started:** 2026-09-21
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

### Delivered 2026-09-21

**The two missing tests were not written — they were recovered.** A branch
named `card/032-image-only-mode` already existed, last touched 2026-09-03,
never merged, and 279 commits divergent from a `main` that had moved 485
commits the other way. It carries `efe55f9 feat(CARD-032): restrict web form
to image-only mode` and a worktree note saying all three criteria passed — and
it was telling the truth. The feature reached `main` by another route; these
two classes did not come with it. `TestWebForm_OnlyOffersImageMode` did, which
is exactly why the gap was invisible: the card looked tested.

Both are restored into `tests/test_web_upload.py`, where they were written,
with a header recording where they came from. The stale branch is renamed
`card/032-superseded-2026-09-03` rather than deleted — the CARD-067 precedent
— and this card's work was started fresh from `main`.

**AC-129 gained a second test.** The recovered one posts an empty file and
checks the failure page mentions the image. That is the symptom; the criterion
says *"the same path as if mode validation had failed in the domain"*, which is
about **where** the refusal happens. So the new test pins that the adapter
builds a request with `image=None` and that the request fails inward with the
identical `UnreadableImage` a bare `--mode image` produces (ADR-0019/R1). The
page test alone would look the same if a well-meaning adapter check were added
in front of it.

**AC-130 gained the comparison it was named for.** The recovered test shows
image mode works; it compares it with nothing, so it would pass equally well
if the adapter had started building a different request. The new test compares
the request the form builds against the one **the CLI actually builds** —
captured on its way inward, because the mapping lives inside `_run_generate`
and rebuilding it in the test would compare the web adapter against a copy of
the CLI rather than against the CLI.

Writing it turned up the one place the two adapters are deliberately *not*
identical: a urlencoded `image=<path>` field is not read as a picture. Only an
uploaded file is. A form that could name a server-side path would be a
file-read primitive rather than a convenience, so the comparison is built the
way `multipart.py` really does it — posted bytes saved to a temp file, that
path handed to `from_fields`. The difference is a security property, and the
test says so.

### Item 3: the citations now point at the decision that authorised the font

The four "CARD-032" mentions in `tests/test_export_pdf.py` meant **ADR-0006's
2026-09-01 revision (DEC-027)**, which admitted a Unicode TTF as package data.
They now say so.

**No card records the font work at all.** Nothing in `meta/kanban/cards/`
cites DEC-027, and no card's `Touches` names a font path, although
`src/nonogram/export/fonts/DejaVuSans.ttf` ships. CARD-014 identified the tofu
problem and explicitly deferred the fix; the ADR says "the implementing card
may subset it" and names no card. So the implementing card is **missing rather
than misnamed**, and the comment in `test_export_pdf.py` says that plainly
rather than leaving a reader to wonder.

### Item 4: the AC numbers collide, and both meanings are live

This card's **AC-128 / AC-129 / AC-130** are ad-hoc numbers from its own text.
**FR-028's AC-128 and AC-130** are registry criteria, implemented by CARD-078
on 2026-09-21 — density 0 and 100 refused, and the verdict made at the
`validate_density` seam. Same numbers, unrelated meanings, both current.

Nothing is renumbered here: FR-028's belong to the registry and this card's
belong to its own prose, and rewriting either would break the other's trail.
The collision is recorded so the next reader of "AC-128" knows to ask which.

**Full suite: 3,613 passed, 0 failed.**
