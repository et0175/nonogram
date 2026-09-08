# Wave 11 — 2026-08-29   (tag: wave-11)

Single-card wave: CARD-017 closes the loop CARD-016 opened, and is the last card of
Increment 3 and of the whole delivery plan — everything remaining on the board after
this wave is CARD-018, an unscheduled follow-up. Needed one fix cycle.

## Shipped
- CARD-017 (feature): Nudge-count reporting in CLI output — after an image-mode run
  whose conversion required pixel nudges to reach uniqueness, the CLI prints one line
  stating how many cells were altered (`"N cells were nudged to reach a unique
  solution"`), read directly off the `Puzzle.nudge.attempts` counter CARD-016 already
  populated. Zero nudges prints nothing at all — the absence of the line is itself
  the "your picture came through untouched" signal (ADR-0004).   score 9.6 (cycle
  2/3)   FR-014, INV-003, ADR-0004

## Requirements closed
- FR-014 (nudge-count disclosure) — closes Increment 3, and with it the whole
  originally-scoped plan (increments 1-3). All three grid sources, all five export
  formats, difficulty tiering, and both recovery loops (regenerate/resample and
  pixel-nudge) are shipped and disclosed to the user.

## Terminal checkpoint — demonstrated end to end, not just unit-tested
Wave 11 is `terminal_for_increment: true` in the wave plan, with a checkpoint
requiring the whole recovery/disclosure chain to work together on a real conversion.
Verified via the actual `nonogram` CLI rather than only the test suite:
- zero nudges (`wide.png` @ 20x20) → `wrote ...json`, no nudge line;
- recovers within the cap (`bands.png` @ 10x10) → `wrote ...json` followed by
  `2 cells were nudged to reach a unique solution`;
- exhausts the cap (`wide.png` @ 22x22) → exit code 4, a message naming the bound,
  explaining an uploaded image is never auto-redrawn, and suggesting a different
  image or `--size`.

All three checkpoint behaviors held exactly as specified.

## Review process notes — a small card, still caught two real gaps
Cycle 1 scored 8.5 and failed the severity gate on two Important findings, both
test-only (no production code was wrong):
- the singular/boundary case (exactly 1 nudge) had zero coverage — two of the four
  new production lines (`"cell"`, `"was"`) never executed in the suite, and the
  mutant `if nudged > 1:` survived undetected;
- AC-041's own test drove `--mode random` to prove "zero nudges prints nothing", but
  random mode structurally can't reach the nudge branch at all — it was proving the
  counter's zero *default*, not the AC's actual stated scenario (an image conversion
  that reached uniqueness cleanly). The reviewer demonstrated the gap concretely:
  re-introducing the exact bug this test was meant to catch, the random-mode version
  stayed green while a corrected image-mode version caught it immediately.

Both were fixed by pointing at already-pinned scripted/real fixtures from
`tests/test_nudge.py` rather than inventing new ones. Cycle 2 confirmed both fixes by
mutation (re-injecting each named bug and watching the new tests catch it, then
restoring clean code) rather than by re-reading the diff, and passed at 9.6 with zero
new blocking findings — cementing the pattern this whole delivery has followed: a
review's job is to verify claims are true, not to check that a plausible-sounding fix
was applied.

A genuinely useful design ruling came out of this card too: the implementer placed
the nudge-count line after the "wrote {path}" export lines rather than immediately
after generation, reasoning it should be suppressed if export fails. The reviewer
found the real condition narrower than argued (a run with no `--export` flag at all
still prints the line; only an export `OSError` actually suppresses it) and ruled the
placement correct anyway — a failed export leaves no artifact on disk, so there is
nothing to disclose anything about, and the count is fully recoverable via a
deterministic re-run regardless. The card's rationale comment was reworded to match
what's actually implemented rather than the broader claim.

## Convergence
- FR-014 ✓ converged. Increment 3 (image sourcing, pixel-nudge recovery, and its
  disclosure) is now fully shipped end to end.

## Known gaps / escalations
- AC-037 — still tracked via `xfail`, CARD-018 remains the sole unscheduled follow-up
  on the board. This is the only open item from the entire delivery plan.
- Minor, backlogged: one test pins only a substring of the disclosure message rather
  than the full sentence (the plural counterpart to a stronger pattern the fix cycle
  already established for the singular case).
- Two previously-backlogged items resolved this wave: "nudged runs are silent until
  CARD-017 ships" (this card *is* that ship) is checked off, and one Wave-10-surfaced
  observation about disclosure sequencing no longer applies.

## Migrations
- none
