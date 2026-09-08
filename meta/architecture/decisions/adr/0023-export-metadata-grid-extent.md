# ADR-0023: Export metadata records width and height, at schema version 2

**Status:** Accepted
**Date:** 2026-08-31
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** rewrite
**Pattern:** —
**API-Posture:** no-http

## Context

ADR-0022 makes a grid's extent a `(width, height)` pair. Both durable export
formats currently record it as a single integer, and this ADR settles what
happens to that field — a question ADR-0022 deliberately left open because it
is a file-format decision rather than a domain one.

The investigation changed the shape of the problem, so the findings matter more
than the options here.

**`size` is provenance, not structure.** In JSON it sits inside the `request`
block beside `mode` and `density` — the three things that were *asked for*. It
plays no part in reconstruction: `decode` rebuilds the puzzle from `grid`,
`clues.rows` and `clues.columns`, reads `size` through `_optional_int`, and
carries it into the payload untouched. The grid's real dimensions have always
been derivable from `grid` itself. EC-002, the fidelity constraint, promises
that decoding "reproduces the exact original solution grid and clues" — `size`
is not in that contract and never was.

**The two formats disagree about strictness, and it matters.** Measured against
the real decoders: JSON accepts unknown keys, so *adding* `width` and `height`
would break no existing JSON reader. CSV rejects them outright — its `#meta`
keys are "all required and no others accepted", and an added key fails with
`#meta: unknown key 'width'`. So the same edit is free in one format and
breaking in the other.

**Backward-readability was never promised, and is already refused.** Both
decoders compare the file's `version` against their own `SCHEMA_VERSION` with
`!=` — an exact match, not a floor — and raise on any mismatch. A v1 file is
already unreadable to a build that has moved on; that is the existing, deliberate
design, documented as "bumped only by a change that an existing reader could not
survive". No requirement anywhere promises that older exports keep loading, and
the project has no released version whose files exist in the wild.

That last finding deflates most of the concern that prompted this ADR. The
question is not "how do we stay compatible" — the format has an explicit
mechanism for not being — but "what shape should the field take now".

## Decision

**Replace `size` with `width` and `height` in the request metadata of both
formats.** In JSON the `request` object gains the two keys and loses `size`. In
CSV the `#meta` key set becomes `version, seed, mode, width, height, density`,
in that order, with the same empty-value-means-`None` convention the existing
optional keys use.

**Bump both `SCHEMA_VERSION`s to 2, independently.** The two numbers are
deliberately separate — the modules' own docstrings say so, on the grounds that
two parsers read them and a change to one is not inherently a change to the
other. Here both formats change for their own reason, and both reach 2 by
coincidence of history rather than by being linked.

**Do not keep `size` as an alias for square grids.** A square puzzle records
`width: 20, height: 20`, not `size: 20`.

**Reading a version-1 export is not supported.** The existing exact-match
version check does this already; it needs no new code, only the bumped constant.
The error it raises names both versions, which is the right diagnosis for a user
holding an old file.

## Alternatives considered

### Keep `size` and add `width`/`height` alongside it
Attractive because it is non-breaking for JSON, and a square puzzle could keep
populating `size` for continuity. Rejected because it creates two sources of
truth for one fact and no rule about which wins when they disagree. A file
carrying `size: 20, width: 30, height: 20` is not hypothetical — it is what a
half-updated writer produces — and every reader would then need a precedence
rule that is pure ceremony. It also does not avoid the CSV break, since CSV
rejects the added keys regardless, so it pays the compatibility cost anyway
while adding the ambiguity.

### Widen `size` to carry a pair — `"size": [30, 20]` or `"size": "30x20"`
Keeps the key name stable, which is worth something. Rejected because changing
an existing field's *type* is a subtler break than renaming it: a reader that
survives the change syntactically may misinterpret the value, and `_optional_int`
would reject the new form with a type error rather than a version error. A
version mismatch tells the user exactly what is wrong; `request.size: expected
an integer, found [30, 20]` does not. Renaming makes the break loud, which for
a durable artifact is the safer failure.

### Drop the field entirely and derive dimensions from `grid`
Genuinely tempting: the dimensions *are* derivable, so the field is redundant
for reconstruction, and removing it would shrink the format. Rejected because
`request` is a coherent record of what was asked for, not of what was produced —
it sits beside `mode` and `density`, both of which are equally derivable from the
grid and equally worth keeping. Someone reading an export a year from now wants
to know what was requested, and reconstructing that from the artifact is not the
same thing.

### Bump JSON only, and leave CSV at version 1
The two versions are independent by design, and JSON's change could be made
non-breaking by addition. Rejected because it would leave the two formats
describing the same puzzle with different field names — `size` in CSV, `width`/
`height` in JSON — which is a worse outcome than either format's version number.
The independence of the two `SCHEMA_VERSION`s exists so they *may* diverge, not
so they must stay in lockstep, and here they should agree on the field's shape.

## Consequences

### Positive

- The metadata says what the grid is, in the same vocabulary the rest of the
  system now uses. A rectangle is no longer inexpressible in an export.
- Removing `size` rather than layering on top of it keeps one fact in one place,
  which is why the format has stayed readable enough to reason about here.
- The failure mode for an old file is a version error naming both versions,
  which is diagnosable, rather than a type or shape error deep in a parser.
- No new compatibility machinery: the version check that makes this safe already
  exists and is already exercised by tests.

### Negative

- **Version-1 exports become unreadable.** Any JSON or CSV file this tool has
  written to date stops loading. That is the format's declared behaviour rather
  than a regression, and nothing in the repository depends on reading one, but
  it is a real loss for anyone holding old files — the puzzle would have to be
  re-generated from its recorded seed and mode.
- Both round-trip test suites change: the fixtures carry `size` in their `#meta`
  and `request` blocks, and every one of them has to move to the new key set.
  This is mechanical but touches a lot of test data.
- `csv_export`'s module docstring documents the `#meta` layout literally,
  including a worked example with `size,4`. Documentation and code must move
  together here or the docstring becomes a lie about the format it defines.
- The CSV `#meta` key set grows from five keys to six, which lengthens every
  exported file by one line. Trivial, noted for completeness.

### Neutral

- The two `SCHEMA_VERSION` constants both become 2 without becoming linked. A
  future change to one still does not imply a change to the other, and the
  docstrings saying so remain accurate.
- `density` stays an optional integer and is untouched, even though it is
  arguably as derivable as `size` was. Consistency of the `request` block is
  worth more than the byte.

## Rules
```yaml
- id: ADR-0023/R1
  statement: Export metadata records a grid's extent as separate width and height fields. No export format writes a scalar "size" field, and no decoder reconstructs a grid's dimensions from one.
  scope: {code: ["src/nonogram/export/**"]}
  check: {kind: review-lens}
  severity: mandatory
- id: ADR-0023/R2
  statement: A decoder accepts only its own SCHEMA_VERSION, by exact comparison, and raises an error naming both the file's version and its own. It never attempts a best-effort read of an older document.
  scope: {code: ["src/nonogram/export/json_export.py", "src/nonogram/export/csv_export.py"]}
  check: {kind: test, ref: TestExport_RejectsSupersededSchemaVersion}
  severity: mandatory
```

## References

- ADR-0022 (grid extent is a width/height pair) — the domain change this serves;
  it explicitly deferred the export-format question to here.
- EC-002 — round-trip fidelity, over "the exact original solution grid and
  clues". The scope of that promise is why `size` could be changed freely.
- FR-012 — JSON/CSV export sufficient to reconstruct the puzzle exactly.
- ADR-0012 — `list[list[bool]]` as the grid boundary type; the `#grid` section
  is that type written cell by cell, and is unaffected.
- `src/nonogram/export/csv_export.py` module docstring — the normative
  description of the `#meta` layout, which changes with this ADR.

## History

- 2026-08-31 — Accepted. Written after establishing four things against the
  running code rather than from the requirement text: that `size` is request
  provenance and plays no part in reconstruction; that JSON accepts unknown keys
  while CSV rejects them, making the same edit free in one format and breaking in
  the other; that both decoders already refuse any version but their own by exact
  comparison; and that EC-002's fidelity promise covers the grid and clues but
  not the request metadata. The compatibility concern that prompted this ADR
  turned out to be much smaller than it appeared for those reasons, and the
  decision is correspondingly simpler than the one anticipated in ADR-0022.
