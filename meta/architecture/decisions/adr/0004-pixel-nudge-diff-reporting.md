# ADR-0004: Pixel-nudge diff reporting at export time

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-013 requires that when an uploaded image's converted grid fails the uniqueness check, the tool attempts a bounded number of automatic pixel nudges and re-checks, reporting failure to the user rather than continuing to alter the image silently if uniqueness still cannot be achieved after the capped attempts. When a nudge attempt does succeed, the exported puzzle's solution grid can differ slightly from the user's original picture — a handful of cells may have been flipped to make the puzzle solvable and unique.

docs/requirements.md Section 8 notes this consequence explicitly and suggests surfacing it to the user at export time (for example, a diff count or a visual preview), but this suggestion was never captured as a numbered functional requirement. FR-013 as written governs the nudge mechanism itself; it says nothing about disclosure of the resulting drift to the user. Without such disclosure, a user could export a puzzle whose solution silently no longer matches the picture they uploaded, with no way to know how much (if anything) changed short of comparing the exported grid to their original image by hand.

The tool is a single-process Python CLI (CON-001) with no persistence beyond file export (CON-003) and no GUI — any user-facing signal has to travel through CLI output and/or the export artifacts themselves. The nudge-attempt cap (from DEC-002) bounds how many cells can possibly be altered, but a bound on magnitude is not the same as informing the user how many cells were actually altered for their specific image.

## Decision

We will report the number of pixel-nudged cells as a line in CLI output at export time. When image-mode generation required one or more pixel nudges to reach a unique solution, the export step prints a plain count of how many cells were nudged relative to the user's original converted grid; when zero nudges were needed, no such drift exists to report.

This is the minimal mechanism that closes the disclosure gap docs/requirements.md Section 8 raises for FR-013: it requires no new export file format, no new dependency, and no new persisted artifact — only a count already known internally by the pixel-nudge loop, surfaced through output the CLI already produces. It satisfies the intent behind FR-013 (the user is not left unaware that their image was altered) at a cost proportionate to a hobby tool, per the Occam's-razor tie-break used when alternatives roughly tie on requirement fit but differ sharply in implementation cost.

Because this decision adds new user-facing behavior rather than merely closing a documentation gap, it creates a new requirement rather than resolving an ambiguity as a no-op: a new FR must be added to `requirements.yml` to formalize "report count of nudged cells at export," sourced from FR-013/US-007 and this ADR. See Consequences below.

## Alternatives considered

### side_by_side_preview

Export an additional preview image showing the original picture alongside the nudged grid. This gives the clearest visual confirmation of exactly which cells changed and would likely be the more informative choice for a user who wants to see the drift rather than just count it. It was rejected because it requires meaningfully more implementation work — a second image-rendering path, alignment/scaling logic between the original and the grid, and a new export artifact — for a personal hobby tool where a simple count already satisfies the disclosure concern the requirements note raises. Nothing here forecloses adding a visual preview later if the count proves insufficient in practice.

### no_new_requirement

Leave the drift undocumented as a requirement, relying on the existing nudge-attempt cap to limit how much any single image can be altered. This was rejected because a cap on magnitude does not equal disclosure: a user can still export a puzzle that differs from their picture with no indication that it happened at all. This directly contradicts the concern docs/requirements.md Section 8 itself raises when it suggests surfacing the diff — choosing this alternative would leave that noted concern unaddressed rather than resolved, which is a worse outcome than the minimal cost of reporting a count.

## Consequences

### Positive

- Users are never left unaware that their uploaded image was altered to reach a unique puzzle — the concern docs/requirements.md Section 8 raises is directly addressed.
- Implementation cost is minimal: the pixel-nudge loop already knows how many nudges it performed, so this is a formatting/output change, not new logic, a new dependency, or a new export format.
- Keeps the export pipeline's output surface consistent with the CLI-only interface constraint (CON-001) — no new artifact types, no GUI, no new file to manage.

### Negative

- A bare count is less informative than a visual preview: the user knows *how many* cells changed but not *which* cells or *how much* the resulting picture diverges from their intent.
- This decision creates a new requirement rather than being a documentation-only resolution: `requirements.yml` must gain a new FR ("report count of nudged cells at export," traced to FR-013/US-007 and ADR-0004), with a corresponding acceptance criterion, before this behavior can be considered spec-complete. Until that FR is added, the code implementing this decision has no formal AC to be tested against.

### Neutral

- Establishes CLI-output-at-export-time as the disclosure channel for this class of concern; any future decision to add a richer preview (the rejected side_by_side_preview alternative) would layer on top of this rather than replace it.
- The exact wording/format of the reported line (e.g., "3 cells nudged from the original image") is left to be settled when the new FR and its acceptance criteria are drafted, not fixed by this ADR.

## References

- DEC-004 (resolved by this ADR)
- FR-013, US-007 (source requirement and story)
- Follow-up: a new FR must be added to `meta/architecture/requirements.yml` formalizing "report count of nudged cells at export," traced to FR-013/US-007 and this ADR

## History

- 2026-08-27: Created — resolves DEC-004 by choosing diff_count_only (report nudged-cell count as CLI output at export time) over a visual side-by-side preview or leaving the drift undocumented.
