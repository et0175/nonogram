# CARD-106: AC-122 through AC-143 each mean two different things

**Status:** review
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** business-analyst
**TDD:** n/a — documentation only; the suite is unchanged at 3,672
**Branch:** card/106-ac-number-collision
**Worktree:** ../PythonProject4-CARD-106
**Source:** measured 2026-09-21 after the collision misled the same reader twice in one session
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** meta/architecture/requirements.yml (a note at the band), meta/kanban/cards/CARD-030.md, 031, 032, 033, 034, 035, 037 (a banner each)
**Review score:** —
**Started:** 2026-09-21
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

**Every number from AC-122 to AC-143 is claimed twice.** Not a stray clash —
two complete numbering runs over the same 22 values, measured 2026-09-21:

| | |
|---|---|
| the registry, `meta/architecture/requirements.yml` | all 22, owned by FR-024, FR-025, FR-027, FR-028 and FR-029 |
| the wave-0 web-UI cards | CARD-030 (122-124), 031 (125-127), 032 (128-130), 033 (131-134), 034 (135-138), 035 (139-142), 037 (143) |

So `AC-125` is *"given an uploaded image… the page shows the image's aspect
ratio"* **and** *"a resized cell whose ink coverage is 49%… the cell is
empty"*. `AC-133` is *"the refined form page displays clear visual grouping"*
**and** *"two random-mode requests at 20x20, one with density 1"*. `AC-138` is
a File API fallback **and** a solver-signal criterion.

This is not hypothetical friction. In a single working session on 2026-09-21 it
misled the same reader twice: once while re-cutting CARD-032, and once while
auditing CARD-031's coverage, where a grep for `AC-125` returned
`tests/test_sourcing_image.py` — a real hit, for the wrong AC-125, which nearly
became a false claim about test coverage in a merged card.

## The decision, taken when the card was written

**Do not renumber.** Both runs are cited by tests and by closed cards.
Renumbering either rewrites trails through merged history for no functional
gain, touches a dozen cards plus test files, and is exactly the kind of large
mechanical edit that introduces a fresh error while fixing a documentation one.

**Say which is which, where a reader hits it.** The registry is the authority:
its criteria carry `given`/`when`/`then`/`test` and are traced to FRs; the
web-UI cards carry prose in their own `## Acceptance criteria` sections and
trace to nothing. That asymmetry is the rule to write down.

## What to implement

1. **A note in `requirements.yml`** at the head of the AC-122..AC-143 band,
   saying that these numbers are also used, with different meanings, by the
   wave-0 web-UI cards; that the registry's are authoritative; and that a bare
   "AC-131" in a commit message or a test docstring is ambiguous unless the
   file it sits in says otherwise.
2. **A one-line banner** on each of CARD-030, 031, 032, 033, 034, 035 and 037,
   directly above its `## Acceptance criteria`, saying that its AC numbers are
   local to the card and collide with the registry's — with the registry's
   meaning named, so a reader does not have to go and look.
3. **Nothing else.** No renumbering, no edits to tests, no changes to the
   registry's own entries.

## Acceptance criteria

- **AC-1** — `requirements.yml` states the collision, its extent (122..143),
  and which side is authoritative.
- **AC-2** — each of the seven cards says its numbers are card-local, and what
  the registry uses the same number for.
- **AC-3** — no AC number is changed anywhere, in any file.
- **AC-4** — a reader who greps for an AC number in that band lands on
  something that tells them there are two answers. (Checked by grepping three
  of them and reading what comes back.)

## Guardrails

- G-1: Do not renumber anything. The point of this card is that renumbering is
  the wrong fix.
- G-2: Do not edit `tests/` — the tests cite whichever AC they were written
  against, and both citations are correct in their own frame.
- G-3: Documentation only; no source changes, so the suite should be untouched
  and unchanged.
- G-4: Commit only your own files — explicit pathspecs.

## Not in scope, and worth saying

Whether the two schemes should ever converge — one registry, every criterion
traced — is a real question and a much larger one. It would mean giving the
web-UI cards' criteria proper registry entries, or accepting that a card may
hold criteria the registry never sees. That is an architecture decision, not a
naming repair, and it wants an ADR rather than this card.

## Architecture context

- **FR:** FR-024, FR-025, FR-027, FR-028, FR-029 (the registry's side of the band)
- **Components:** the requirements registry and the kanban cards
- **Trace:** none

### Delivered 2026-09-21

**A header note in `requirements.yml`** at the top of the band: the extent
(AC-122..AC-143), which cards claim the same numbers, that the registry's are
authoritative and why, and that neither set is renumbered. It names the
concrete case that caused this — a grep for `AC-125` returning a real hit in
`tests/test_sourcing_image.py` for the binarisation criterion, nothing to do
with the aspect ratio CARD-031 calls AC-125.

**A one-line marker above each of the 22 entries**, which is the part that
actually works. The first cut put the note in one place and stopped, and AC-4
was not met: the band is **not contiguous in the file** — it is scattered
across FR-024, FR-025, FR-027, FR-028 and FR-029 — so a reader who greps
`AC-125` lands hundreds of lines from a note above `AC-122` and never sees it.
Now the matching line has the warning directly above it:

```
      # NB CARD-031 uses AC-125 for a different criterion of its own (CARD-106)
      - id: AC-125
```

**A banner on each of the seven cards**, above its `## Acceptance criteria`,
with a table naming what the registry means by each number and which FR owns
it — so a reader does not have to go and look. CARD-033's, for instance, says
its `AC-133` is FR-028's "two random-mode requests at 20x20, one with density
1…".

### Checked rather than asserted

* `requirements.yml` still parses as YAML after 23 insertions.
* The **set of AC ids is byte-identical to `main`** — compared by hash, so
  AC-3 ("no AC number is changed anywhere") is measured, not hoped.
* `tests/` is untouched: `git diff --name-only main -- tests/` is empty (G-2).
* Full suite 3,672 passed — the same number as before, which is what a
  documentation card should do to it.

### What is deliberately still true

The two schemes still exist and still collide. This card makes the collision
**visible at the point of use**; it does not resolve it. Whether the web-UI
cards' criteria should ever get registry entries of their own is the
architecture question the card scoped out, and it still wants an ADR rather
than a naming repair.
