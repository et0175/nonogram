# ADR-0003: Random-generation density tolerance

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-004 requires the random-generation mode (FR-001) to accept a requested clue
density as a percentage and produce a grid whose filled-cell density is only
"approximate" to that request — the requirement text does not fix a tolerance
band. The regenerate/resample loop (POL-001) draws a new random grid and
re-checks its density against the request, retrying up to the bound NFR-002
sets, so the width of the acceptance band directly determines how often that
loop has to run: a tighter band means more retries (and, at the extreme, more
runs that exhaust the retry cap and abandon), while a wider band means faster,
more reliable generation but a puzzle whose density can visibly diverge from
what the user asked for.

Grid sizes range from 10x10 to 50x50 (NFR-001), so the tolerance also has to
behave sensibly across nearly an order of magnitude of cell count: a fixed
absolute band is a much smaller fraction of cells at 50x50 than at 10x10,
while a relative band widens in absolute percentage-point terms as the
requested density grows. The choice has to pick one of these two shapes (or
otherwise settle what "approximate" means) before random generation can be
implemented and before its acceptance criteria can be written precisely.

## Decision

We will accept a generated grid's density as satisfying FR-004 when it falls
within ±3 percentage points of the requested density (the `plus_minus_3_points`
alternative). This keeps "density" a meaningful, user-facing number — a
request for 30% density is honored as 27–33%, regardless of grid size — which
is the more literal reading of FR-004's intent than a relative band whose
absolute drift would grow with the requested density. The fixed absolute band
is also simpler to state and to test (a single constant, not a
size-and-density-dependent formula), and it composes cleanly with the
existing POL-001 regenerate loop and its NFR-002 retry bound rather than
requiring a new mechanism.

## Alternatives considered

### plus_minus_10_percent_relative

Accept density within ±10% relative to the requested value (e.g. a 30%
request accepts 27–33%, but a 60% request accepts 54–66%). This scales the
absolute band with grid size in the sense that it scales with the requested
density, which reads well for very low or very high density requests where a
fixed 3-point band might be disproportionately tight or loose relative to the
number of filled cells involved. It was rejected because the resulting
absolute drift grows with the requested density — a 66%-accepted-as-60% grid
drifts twice as far in percentage-point terms as low-density requests would,
which undercuts the sense that "density" means what the user typed. It also
adds a second free parameter (a percentage of a percentage) to reason about
and test, where the chosen fixed-point band needs only one constant.

## Consequences

### Positive

- The requested density stays meaningful to the user: "30%" always means
  27–33%, independent of grid size or how dense the request is, which is easy
  to explain and to state as an acceptance criterion.
- The tolerance is a single constant (3 percentage points), making it trivial
  to test directly and to tune later without touching the regenerate loop's
  mechanics.
- Composes directly with the existing POL-001 regenerate loop and NFR-002's
  retry bound — no new mechanism is introduced, only the numeric acceptance
  check that loop already needs.

### Negative

- A fixed absolute band is proportionally tighter on small grids: at 10x10
  (100 cells), ±3 points is only ±3 cells, so low- and high-density requests
  on small grids may need more regenerate attempts to land in range, pushing
  closer to the NFR-002 retry bound than a relative band would.
- At very high or very low requested densities (e.g. 5% or 95%), the fixed
  3-point band is a large relative swing, which was accepted as a reasonable
  trade-off but is a genuine asymmetry the relative alternative would not
  have had.

### Neutral

- The 3-point constant is a tuning surface, not a load-bearing algorithm — it
  can be revisited (via ADR revision) once real generation-attempt data shows
  whether small grids or extreme densities are hitting the retry bound more
  than expected.
- This decision interacts with DEC-002 (the regenerate/resample retry-count
  default): if empirical retry rates against this ±3-point band turn out too
  high, DEC-002's retry cap — not this tolerance — is the first place to
  revisit.

## References

- DEC-003 (resolved by this ADR)
- FR-004
- CTX-001 (Puzzle Creation)

## History

- 2026-08-27: Created — accepted ±3 percentage points as the random-generation
  density tolerance, in favor of a relative-percentage band, to keep the
  requested density meaningful across the 10x10–50x50 size range.
