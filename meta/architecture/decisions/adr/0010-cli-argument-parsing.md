# ADR-0010: CLI argument parsing and validation placement

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

The CLI adapter (CON-001: this tool has no web/GUI, only a command-line
interface) must accept and validate a moderate set of arguments — generation
mode, grid size, requested density, difficulty tier, an image path for
image-sourced puzzles, one or more export formats, and an output path (FR-001,
FR-004, FR-008). Several acceptance criteria are specifically about rejecting
bad input at this boundary: AC-003/AC-004 check that out-of-range sizes are
rejected, AC-011 checks that density outside 0-100 is rejected, AC-021 checks
that an unrecognized difficulty tier is rejected, and AC-006 checks that an
unknown library key is rejected.

This raises two separable questions. The parsing-library question is
low-stakes on its own — stdlib argparse, a third-party CLI framework, and
hand-rolled argv parsing can all technically accept a dozen flags. The
consequential question is where validation logic lives: syntactic parsing
(is this a valid path string? is this an integer?) is naturally a CLI-layer
concern, but the domain-meaningful checks these ACs describe — is this size
within the supported range, is this density a valid percentage, is this tier
one of the known values — are rules about the Puzzle domain, not about
argument syntax. Those checks also need to be exercised directly by the AC
test suite without going through argv or a CLI framework's decorator
machinery, and they need to hold for any future non-CLI caller of the same
domain logic. DEC-006 has already set a lean, dependency-minimal baseline for
this tool, which bears on whether a parsing library is worth adding purely
for argv convenience.

## Decision

We will use stdlib `argparse` for CLI argument parsing (the `stdlib_argparse`
alternative), expressing only purely syntactic constraints — types, choices,
and basic range hints — as argparse-level configuration, while the
domain-meaningful validation that AC-003/AC-004, AC-006, AC-011, and AC-021
actually test (size range, density range, tier membership, library key
membership) is implemented once in the domain layer and duplicated there
rather than left inside the CLI adapter. This keeps the tool free of a
dependency whose only job is argv handling, consistent with DEC-006's lean
baseline, and it keeps the AC tests able to exercise domain validation
directly as pure function calls, without invoking argv or a CLI framework.

## Alternatives considered

### typer_or_click

Adopt Typer (or Click) for declarative command definitions, automatic help
generation, and type-driven coercion — for example an Enum-typed difficulty
argument that gets tier validation almost for free. This would produce nicer
help output and less boilerplate for a tool with a dozen knobs, which is a
real UX advantage. It was rejected because it adds a dependency whose sole
purpose is argument handling to a baseline DEC-006 deliberately kept minimal,
and because these frameworks encourage placing validation logic inside the
CLI decorator itself — exactly where the AC-003/AC-004/AC-006/AC-011/AC-021
tests cannot reach it without going through the CLI entry point, undermining
the goal of testing domain rules as domain rules.

### hand_rolled_sys_argv

Parse `sys.argv` manually with no library at all. This has no dependency and
gives total control over parsing, but it was rejected because it simply
reinvents argparse — poorly — with worse help text and worse error messages,
and offers no advantage over stdlib argparse, which is already
dependency-free and already solves the syntactic parsing problem correctly.

## Consequences

### Positive

- No new dependency is introduced for argument parsing, consistent with
  DEC-006's lean, dependency-minimal baseline.
- Domain validation (size range, density range, tier membership, library key
  membership) lives in one place in the domain layer, so it holds identically
  for the CLI and for any future non-CLI caller (tests, a future
  library-style import), and the AC tests can call it directly without
  invoking argv.
- argparse's built-in mechanisms (choices, type coercion, subcommands) are
  sufficient for roughly a dozen flags, so no custom parsing scaffolding is
  needed for the purely syntactic layer.

### Negative

- Help output and error messages from argparse are plainer than what Typer or
  Click would produce out of the box, which is a genuine UX cost for a tool
  with this many knobs.
- Some boilerplate is required to wire argparse subcommands/flags, since
  argparse's API is lower-level than a declarative framework's.
- Validation logic now exists in two places conceptually — a light syntactic
  check at the CLI layer (e.g. "is this parseable as an integer") and the
  authoritative domain check behind it — which must be kept from drifting
  apart as the domain rules evolve.

### Neutral

- This decision is downstream of DEC-006 (dependency baseline): revisiting
  DEC-006 toward a richer dependency set would reopen whether a CLI framework
  is still disproportionate.
- The domain-layer validation functions introduced here become the natural
  target for EC-style property tests over the argument-validation ACs
  (AC-003, AC-004, AC-006, AC-011, AC-021), independent of how the CLI adapter
  is implemented.

## References

- DEC-010 (resolved by this ADR)
- CTX-001 (Puzzle Creation)
- CON-001, FR-001, FR-004, FR-008
- AC-003, AC-004, AC-006, AC-011, AC-021
- DEC-006 (dependency baseline; this decision depends on it and is not yet
  resolved to an ADR)

## History

- 2026-08-27: Created — accepted stdlib argparse for CLI syntax, with domain
  validation (size, density, tier, library key) duplicated in the domain
  layer so it is testable independent of argv and consistent with DEC-006's
  lean dependency baseline.
