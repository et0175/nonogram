# Wave 6 — 2026-08-28   (tag: wave-6)

Largest wave yet: 5 cards (4 run concurrently, 1 queued and auto-started via the
conflict graph once a same-wave overlap resolved), one ADR revision, two fix cycles.

## Shipped
- CARD-008 (feature): Built-in image library sourcing — `--mode library --library-key <cat|heart|house|moon>` sources a fixed grid from a small built-in template set instead of `--mode random`.   score 9.2 (cycle 1/3)   FR-002, ADR-0007, ADR-0010
- CARD-009 (feature): Difficulty scoring formula from solver signals — `score = 100 * effort * relief`, `effort` a fixed-weight sum of three solver signals (line-logic/backtracking/solve-time), `relief` a multiplicative discount from size+density. Surfaced and resolved a genuine self-contradiction in ADR-0013 (see below).   score 9.2 (cycle 1/3)   FR-009, CON-004, ADR-0009, ADR-0013
- CARD-011 (feature): Puzzle naming (auto-generated and `--name` override) — `Puzzle.name` (AGG-001), set once at creation: library key verbatim, or `<mode>-<YYYY-MM-DD>-<HHMM>` with a same-minute counter suffix (ADR-0018), or the user's `--name`. Also made `puzzle.name` the single source of truth for export filenames in both directions, so the JSON/CSV/PNG/SVG file a run writes always matches the name reported for it.   score 9.4 (cycle 2/3)   FR-015, ADR-0007, ADR-0010, ADR-0018
- CARD-012 (feature): PNG and SVG export renderers — `--export png` / `--export svg`, both reusing CARD-007's format registry and export-readiness gate (INV-002).   score 9.3 (cycle 1/3)   FR-011, INV-002, CON-002, CON-006
- CARD-013 (feature): CSV export and exact round-trip fidelity — `--export csv`; a decoder that reconstructs grid + clues from a written file and asserts byte-exact round-trip against the source puzzle.   score 9.5 (cycle 2/3)   FR-012 (completion), EC-002, CON-002

## Requirements closed
- FR-002 (built-in library sourcing) — four templates (cat/heart/house/moon), validated against the same uniqueness/export pipeline as random mode.
- FR-009 (difficulty scoring) — closes with a formula that is internally consistent for the first time (see below).
- FR-011 (PNG/SVG export) and FR-012 completion (CSV export + round-trip fidelity) — all four Increment-2 export formats now ship (JSON from wave 5; PNG/SVG/CSV this wave).
- FR-015 (puzzle naming) — auto-generated and `--name`-overridable, with export filenames now derived from the same name.

## A genuine architectural finding, resolved mid-wave
CARD-009's implementation ran into ADR-0013 asserting two incompatible things in its own
Decision section: that all five difficulty signals are combined in "one fixed-weight sum",
and, two sentences later, that size/density are "normalizers, not additive terms" — a
formula cannot be both. This was a self-contradiction in the ADR's prose, not a real
design alternative to weigh, so it was resolved directly (no full DEC dialogue) by revising
ADR-0013 in place: `score = 100 * effort * relief`, where `effort` is the fixed-weight sum
over the three *solver* signals (line-logic-solvable, backtracking-depth, solve-time) and
`relief` is a bounded multiplicative discount from size and density. `Migration: grandfather`;
a History entry records the revision.

## Design decisions worth recording
- **CARD-011's export-stem consolidation.** The card's own guardrail G-3 read "nothing on
  the export path changes for it in this card" — true when written, but the moment a
  puzzle's *name* is the thing files are named after (ADR-0016), a name-only change and an
  export-filename change are the same change. The implementer flagged this explicitly rather
  than deciding it silently; the cycle-1 reviewer ruled it a legitimate in-scope consolidation
  (the guardrail's stated rationale — CARD-012/013 owning `export/**` this wave — was already
  spent by the time CARD-011 reached review, both having merged) and not a scope violation.
  Without it, one run would report two different filenames for the same puzzle (e.g. a
  `library` mode run whose JSON is `library-<timestamp>.json` next to a PDF later named
  `cat-hard.pdf`) — exactly the drift CARD-014 (PDF export) would otherwise inherit.

## Review process notes
- **Conflict-graph queue-and-refill.** CARD-008/009/012/013 predicted low pairwise overlap
  and ran fully in parallel; CARD-011 predicted overlap with CARD-008 and CARD-012's
  `Touches:` above `dispatcher.max_overlap` and was queued rather than started concurrently,
  auto-starting once CARD-008 merged. Its later rebase onto all three already-merged
  siblings (CARD-008/009/012/013) completed with **zero code conflicts** — only the
  usual two-writers card-file conflict, resolved the standard way.
- **CARD-013** needed one fix cycle: a missing grid/clue dimension-consistency check in the
  round-trip decoder (a malformed or hand-edited CSV with mismatched clue counts silently
  decoded instead of being rejected) — closed, then a clean cycle-2 confirmation (9.5).
- **CARD-011** needed one fix cycle: its `_UNSAFE_STEM_CHARACTERS` filename sanitizer was
  ASCII-only, so a non-ASCII `--name` (Cyrillic, accented Latin, CJK) was silently truncated
  into a misleading filename instead of falling back — caught because no test asserted the
  sanitized stem itself, only its parent/suffix. Fixed by widening to a Unicode-aware
  allow-list (verified via a 71-name adversarial corpus plus an exhaustive Unicode-codepoint
  scan that no traversal-unsafe character is ever matched) and pinning explicit `path.stem`
  assertions, certified non-vacuous by a 3-mutant mutation test (all killed). Cycle-2
  confirmation: 9.4, no new findings.
- Merge-conflict pattern held steady: every card's `meta/kanban/cards/CARD-XXX.md` conflicted
  on merge (worktree notes vs. main's synced copy) and was resolved identically each time
  (`git checkout --ours`, main being the fuller synced copy).

## Convergence
- FR-002, FR-009, FR-011, FR-015 ✓ converged.
- FR-012 ✓ fully converged (JSON + CSV + round-trip fidelity; PNG/SVG under FR-011).
- ADR-0013 ✓ converged (was self-contradictory; now internally consistent).

## Known gaps / escalations
- AC-037 (NFR-001's p95 target at 20x20 mid/low density) — still tracked via `xfail`,
  CARD-018 remains queued (unscheduled, depends on CARD-006, done) — untouched this wave.
- CARD-011's Minor findings deferred, not blocking: an NFD-normalized (decomposed) accented
  `--name` still loses its diacritics even after the Unicode-aware fix (same behavior as
  before, not a regression — folds into CARD-014's PDF-header work); the byte-length of a
  long non-ASCII stem is unbounded on filesystems with a 255-*byte* (not 255-character)
  `NAME_MAX`; the card/ADR-0016 record of the name→filename consolidation itself, to be
  added alongside CARD-014.

## Migrations
- none
