# ADR-0040: Book production as a composite-capability package

**Status:** Accepted
**Date:** 2026-10-22
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** rewrite
**Pattern:** —
**API-Posture:** —

## Context

Book production (CAP-006 — plan, membership, page spec, proof, answer key, KDP
packaging, book PDF generation) was built inside the admin adapter as
`src/nonogram/admin/book_*.py` plus `print_specs.py` (which `book_manager` and
`book_page_spec` import, and which imports `book_page_spec` back): nine
modules, 13,840 of the package's ~46k source lines (counted 2026-10-22),
including the repo's largest file (`book_pdf_generator.py`, 7,216 lines). ADR-0033 settled the bounded-context question — CAP-006 stays in
CTX-001 — but not where its code sits in ADR-0007's layering. That layering is
enforced by the import guard in `tests/test_cli.py` as a rank table — adapter
(0: `cli`, `web`, `admin`), orchestrator (1), capability (2, the fallthrough
rank where `db/` also lands), shared (3: `errors`, `limits`) — with one rule:
an import must reach a strictly deeper rank than the module making it.

Two facts collide. First, book code composes other capabilities: it imports
`clues`, `difficulty`, `export` (layout, pdf, png) and `db` — verified
2026-10-22; no book module imports the orchestrator, Flask, or any adapter.
At capability rank those imports would be forbidden lateral traffic, which is
why the code accreted in `admin/` where rank 0 may import anything. Second,
that location exempts the repo's largest body of domain logic from the guard
entirely, breaks ADR-0007's one-module-per-capability property for CAP-006,
and makes book code importable by nothing — the reason the shared page
geometry had to be pushed down into `export/layout.py` (ADR-0036). CON-017
keeps book management an admin-panel concern; CON-019 imposes the one-way
rule that book production never feeds back into puzzle generation or
CAP-005's exports.

## Decision

We will carve book production out of the admin adapter into its own package,
`src/nonogram/book/`, sitting at a new **composite-capability rank** between
the orchestrator and the capabilities in ADR-0007's rank table. A composite
may import capability-rank modules (`clues`, `difficulty`, `export`, `db`)
and shared modules (`errors`, `limits`), and nothing shallower — never an
adapter, never the orchestrator, never a sibling composite; adapters may
import it. This legalises exactly the imports book code already has while
naming what the code actually is — a composition layer, like the
orchestrator, rather than an adapter — and it puts ~13k currently-exempt
lines under the guard's import walk. The cheaper alternative (reusing the
orchestrator's rank) was passed over because it buys the same imports by
silently redefining rank 1, which ADR-0007 defines as the single module
owning AGG-001 and POL-001..005.

The context boundary is untouched: CAP-006 and AGG-002 remain in CTX-001 per
ADR-0033, and ADR-0033/R1 (book code writes no puzzle field but
`puzzles.book_id`) continues to govern the moved files. The admin panel
remains the only adapter that uses the package (CON-017); the rank mechanics
would permit the orchestrator to import it, but CON-019's one-way rule
forbids the generation pipeline depending on book production, and that ban is
pinned as a guard edge (see Rules).

## Alternatives considered

### second_module_at_orchestrator_rank

Place `book/` at the existing orchestrator rank (1) beside `orchestrator.py`;
the same imports become legal with a one-line guard change, and the
same-rank rule forbids the two composing modules importing each other for
free. Rejected: rank 1 is defined as *the* module owning the Puzzle aggregate
and the generation policies, and a second resident silently redefines it as
"composition layer" without the ADR trail saying so — which is how the next
misplaced module gets argued in. It would also make `book/` importable by
`cli` and `web`, a legal-but-meaningless surface the composite rank at least
rules out deliberately.

### stay_in_admin_split_files_only

Keep book code at adapter rank and only reorganise internally (an
`admin/book/` subpackage; `app.py` split into blueprints). Rejected: the
blueprint refactor is wanted regardless and needs no decision, but this
alternative leaves CAP-006 the only capability without a module home, keeps
the guard checking nothing book code imports, and preserves the reuse wall —
rank-0 code is importable by nothing, so every future shared piece repeats
ADR-0036's push-it-down-into-`export/` surgery.

## Consequences

### Positive

- The guard starts checking ~13k lines it exempts today: a book module
  importing Flask, the orchestrator, an adapter, or a future sibling
  composite becomes a suite failure instead of a convention.
- CAP-006 finally has a module home, restoring ADR-0007's
  one-module-per-capability property for the repo's largest capability, and
  the component map / trace can point at `book/` instead of "somewhere in
  COMP-009".
- `admin/` shrinks toward an actual adapter (routes, templates, the non-book
  admin flows), which is also the precondition for the `app.py` blueprint
  split to produce small modules rather than re-shuffling 13k lines of book
  logic.
- Book logic becomes importable by any adapter — a future `nonogram book …`
  CLI command would be a thin caller, not a second implementation.

### Negative

- A third tier is new conceptual weight in ADR-0007 and in the guard: the
  rank functions, the degeneration meta-tests and the forbidden-edge pins in
  `tests/test_cli.py` all need the new tier added and pinned.
- A real migration (hence **Migration: rewrite**): nine modules move, every
  admin import path updates, the component-map docstring, the C4 component
  view and `trace.yml` all change — synthesis is stale until re-run after the
  move lands.
- The reuse wall between `book/` and `export/` does not fall: `export/`
  (capability rank) still may not import the composite, so genuinely shared
  rendering/geometry keeps graduating down into `export/` as under ADR-0036.
  This ADR relocates the composition layer; it does not dissolve that
  direction.

### Neutral

- `db/` stays at the capability fallthrough rank; the composite may import it
  like any capability. Whether infrastructure deserves its own rank is left
  undecided — nothing today forces it.
- A new COMP id for `book/` is assigned when synthesis re-runs after the
  move; until then CAP-006 keeps tracing to COMP-009.
- ADR-0033/R1's scope glob widens to cover both the old and new locations for
  the duration of the migration (amended in ADR-0033's History).
- The `admin/app.py` blueprint split proceeds independently as a pure
  refactor; no decision gates it.

## References

- DEC-043 (resolved by this ADR)
- CTX-001 (unchanged context); CAP-006, AGG-002
- ADR-0007 (rank table revised alongside this ADR), ADR-0019, ADR-0033
  (context boundary and R1, both standing), ADR-0036 (geometry precedent)
- CON-017, CON-019
- tests/test_cli.py (the import guard this ADR extends)

## History

- 2026-10-22: Created — book production carved out of the admin adapter into
  `src/nonogram/book/` at a new composite-capability rank, over reusing the
  orchestrator's rank and over staying in `admin/`; Migration: rewrite.

## Rules

```yaml
- id: ADR-0040/R1
  statement: >-
    src/nonogram/book/ sits at the composite-capability rank: it imports only
    capability-rank modules (clues, difficulty, export, db, ...) and shared
    modules (errors, limits); it never imports an adapter, the orchestrator,
    or another composite; only adapters may import it.
  scope: {code: ["src/nonogram/book/**"]}
  check: {kind: test, ref: test_every_import_in_the_package_points_inward}
  severity: mandatory
- id: ADR-0040/R2
  statement: >-
    The generation pipeline never depends on book production: neither
    orchestrator.py nor any capability module imports src/nonogram/book/
    (CON-019's one-way rule expressed as an import ban, pinned as a
    forbidden edge in the guard).
  scope: {code: ["src/nonogram/orchestrator.py", "src/nonogram/book/**"]}
  check: {kind: test, ref: test_the_import_rule_rejects_each_forbidden_edge}
  severity: mandatory
```
