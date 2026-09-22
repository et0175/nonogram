# CARD-056: Formalize an ADR/invariant for admin puzzle uniqueness and quality metrics

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** red first — 7 of 8 tests failed before the fix; 4 mutants, all caught
**Branch:** card/056-adr-admin-generation-guarantees
**Worktree:** ../PythonProject4-CARD-056
**Source:** meta/review/20260910T170025Z.yml#F-009
**Idea:** —
**Wave:** —
**Depends on:** CARD-049, CARD-050, CARD-080 (all done)
**Touches:** meta/architecture/decisions/adr/ (a new ADR), meta/architecture/domain/aggregates.yml; under option B also src/nonogram/admin/puzzle_review.py (the quality_min comparison) and src/nonogram/admin/pdf_generator.py (the "0" default that never fires), plus their tests
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-22
**Closed:** 2026-09-22
**Actual:** 0.5d
**Merge commit:** 4158e4b
**Blocked by:** —

## What to implement

`system_rules.py --scope 'src/nonogram/**'` returns 8 rules today, none of which
constrain `quality_score`, `recognizability`, or uniqueness verification outside
the `orchestrator.Puzzle` aggregate itself (`INV-002`, currently
`scope_unmapped_model` since `trace.yml` doesn't exist). Admin's generation
paths construct puzzle data as plain dicts, never instantiating
`orchestrator.Puzzle`, so even a resolved `INV-002` would not mechanically reach
them. This absence is the structural reason the bugs CARD-049/CARD-050 fix could
ship and persist without any system-contract check ever catching them — the
same pattern as CARD-048 from the previous review round, here for a
substantially more consequential area.

**This card depends on CARD-049 and CARD-050 landing first** — write the rule
against what the fixed behavior actually is, not against a still-hypothetical
fix.

1. Write a new ADR (or extend an existing one — `ADR-0013` difficulty-scoring or
   a new one, implementer's judgment) with a `## Rules` block stating, in the
   project's existing rule-YAML format (see `ADR-0022`'s `## Rules` section for
   the exact shape):
   - A rule that every puzzle stored via `puzzle_review.add_puzzle` must have
     passed a solver-verified uniqueness check, scoped to cover
     `src/nonogram/admin/**` (not just `orchestrator.py`/`sourcing/**` the way
     `ADR-0022/R4` is scoped today).
   - A rule stating what `quality_score`/`recognizability` are actually defined
     as post-CARD-050 (real measurement for image mode; whatever CARD-050 chose
     for random mode — a real metric or explicit `None`), scoped similarly.
2. If `trace.yml` still doesn't exist by the time this card runs, note in the
   ADR's own text that the rule is declared but not yet mechanically checkable
   until synthesis reaches this component — same honesty `ADR-0022/R3`/`R4`
   already model for their own scope gaps (see the previous review's CARD-048).

## Re-cut 2026-09-22 — half the card is already true, and verifying the other half found a live bug

Checked against `main` at `da0581e`. Both dependencies are **done** (CARD-049,
CARD-050), as is CARD-080, which matters more than either.

**Stale counts and a moot clause.**

- "`system_rules.py --scope 'src/nonogram/**'` returns 8 rules today" — it
  returns **37**, and **13** match `src/nonogram/admin/**`, several of them
  admin-specific (CON-015, CON-016, ADR-0031/R2). The scope has been filled in
  substantially since the card was written.
- "`trace.yml` doesn't exist" — **it exists and is tracked.** The
  `scope_unmapped_model` diagnostic is now empty, so INV-002 is mapped. Item 2
  of *What to implement* (declare the rule as not-yet-checkable) is moot;
  a rule written today can carry a real `check:` ref.

**Rule 1 would now record shipped behaviour, not propose a guarantee.**
CARD-080 built exactly the guard this card asks for:
`PuzzleReviewService.add_puzzle` re-derives the clues, asks the solver, and
raises `NotUniquelySolvable` rather than storing an unproven grid. It is
covered by four test classes in `tests/test_admin_uniqueness_boundary.py`
(`TestStorageBoundary_RefusesAnAmbiguousGrid`,
`…_StoresAUniqueGridUnchanged`, `…_AsksTheSolverNotTheCaller`,
`…_RefusesRatherThanStoringAnUnprovenGrid`), so the rule has a check ref
available and does not need the honesty clause. **No ADR mentions
`add_puzzle` at all** — the behaviour is real and the record is absent, which
is a narrower and more useful statement than the card's "this absence is the
structural reason the bugs could ship".

**Rule 2 is genuinely unrecorded.** `quality_score` and `recognizability`
appear in **no ADR and nowhere in `requirements.yml`**. Nothing in the
architecture model says what they mean, what may write them, or what `None`
signifies.

### What that absence has already cost — a reachable defect, found while verifying

`puzzle_review.py:775`:

```python
if filter_opts.quality_min and puzzle["quality_score"] < filter_opts.quality_min:
```

CARD-050 made random-mode `quality_score` **`None`** (`batch_generator.py:390`
writes `quality_score=None`). Comparing `None < int` raises. Reproduced
end-to-end against the real service:

```
stored a random-mode puzzle with quality_score=None
REPRODUCED TypeError: '<' not supported between instances of 'NoneType' and 'int'
```

It is reachable from two routes (`app.py:1717` and `app.py:2034` both read
`quality_min` off the query string and pass it into the filter).

**And the two storage paths disagree about it.** The DB branch of the same
method filters in SQL — `Puzzle.quality_score >= filter_opts.quality_min` —
where `NULL` rows simply fail the predicate and are dropped. So the same user
action gives: an in-memory store → `TypeError`; a Postgres store → random-mode
puzzles silently missing from the results. Neither is a decision anyone
recorded; both follow from nothing saying what `None` means.

**A second, milder one:** `pdf_generator.py:206,227` render
`f"Quality: {puzzle.get('quality_score', 0)}/100"`. The `0` default never
fires, because the key is present with value `None` — a random-mode puzzle in
a book prints **"Quality: None/100"** in the TOC and on the page. Verified by
evaluating the same expression.

### The decision this card now needs

The card's Engineering constraints say "documentation-only, no production code
touched". That was written before the defect above was known.

- **Option A — document only, file the bug.** Write the ADR with both rules,
  and open a separate card for the `None` comparison and the PDF default. Keeps
  this card's shape, and the rule arrives first so the fix has something to cite.
- **Option B — document and fix.** Same ADR, plus the two-line fix and its
  tests, in one card. The rule and the behaviour land together, which is the
  arrangement that stops them drifting apart again — but it amends the
  Engineering constraints.

**Recommended: B**, narrowly scoped to the two sites above. A rule that says
what `quality_score` means, merged while a live path still crashes on the value
the rule blesses, is the drift this card exists to end. The fix is small and
its test is obvious; splitting it costs a card and gains nothing but
bookkeeping. **But it is your call, since it changes what the card promised.**

## Acceptance criteria

- **AC-1** — given the ADR is written, when
  `system_rules.py --root meta/architecture --scope 'src/nonogram/admin/**'` is
  run, then the new rule(s) appear in the matched set (13 rules match today).
- **AC-2** — the ADR's stated rules match what CARD-049, CARD-050 **and
  CARD-080** actually implemented. *(CARD-080 added after the 2026-09-22 re-cut:
  it built the uniqueness guard rule 1 describes, so rule 1 documents shipped
  behaviour and must carry that behaviour's real `check:` ref — one of
  `tests/test_admin_uniqueness_boundary.py`'s `TestStorageBoundary_*` classes —
  rather than the "declared but not checkable" clause the card allowed for.)*
- **AC-3** *(new, 2026-09-22)* — the rule about `quality_score` states what
  `None` means and which modes produce it, because that is the fact the code
  currently disagrees with itself about.
- **AC-4** *(new, 2026-09-22, option B only)* — a random-mode puzzle
  (`quality_score is None`) survives a `quality_min` filter without raising, and
  the in-memory and DB paths agree on what it does; a puzzle with no measured
  quality renders in the book PDF without printing `None/100`. Each has a test
  that fails before the fix.

## Engineering constraints

None — documentation-only change to the architecture model, no production code
touched.

## Worktree notes

### Delivered 2026-09-22 — option B (document and fix)

**ADR-0032** — *What the admin panel guarantees about a stored puzzle* — with
two rules, both carrying live `check:` refs. `system_rules.py --scope
'src/nonogram/admin/**'` now matches **15** rules, including `ADR-0032/R1` and
`/R2` (AC-1). The architecture validator reports the same single error it did
before: CARD-071's known false positive in the forge tool's supersession regex.

**Suite: 3,681 passed, 26 skipped, 1 deselected** — 3,673 plus this card's 8.

### R1 documents; R2 documents *and* corrects

R1 states CARD-080's uniqueness guard, which has been shipping since
2026-09-14. Its check ref is that card's own
`TestStorageBoundary_AsksTheSolverNotTheCaller`. Nothing changed in code.

R2 states what `quality_score` is — and the two consumers that disagreed with
it are fixed here:

- `puzzle_review.py:775` compared `puzzle["quality_score"] < quality_min`,
  raising `TypeError` on the `None` that random mode has written since
  CARD-050, reachable from `app.py:1717` and `app.py:2034`. Now an unmeasured
  puzzle is excluded rather than compared — which is what the DB branch has
  always done via SQL `NULL`, so **the deployed Postgres behaviour does not
  change**; the in-memory path stops raising and starts agreeing with it.
- `pdf_generator.py` printed `Quality: None/100` in a book, its
  `.get("quality_score", 0)` default never firing on a key that exists holding
  `None`. Now both call sites ask `_quality_label`, built in the shape
  `_tier_label` already established in the same class for the same kind of
  problem (CARD-077 F-007).

### Mutation check — 4 mutants, all caught

| Mutant | Caught by |
|---|---|
| both PDF sites back to `.get('quality_score', 0)` | the AST guard |
| `_quality_label` stringifies `None` | both label tests |
| the `is None` check dropped from the filter | 3 filter tests |
| `None` admitted by the filter instead of excluded | 3 filter tests |

### Two things I got wrong and corrected

**A tautological assertion.** The boundary test first compared a filter result
against a comprehension over that same result — true whatever the code does.
Replaced with the real claim: at `quality_min=80` the 80-scoring puzzle passes
(the comparison is `<`, so the boundary belongs to the puzzle), and at
`quality_min=1` the unmeasured one still does not, because `None` is not a
score below 1 — it is no score.

**A source-text guard that tripped on its own documentation.** The check that
no call site uses `.get("quality_score", 0)` was a substring search, and it
failed on the helper's docstring, which quotes the retired expression to
explain what it replaced. Rewritten as an `ast` walk for `.get` calls with two
arguments — the same shape `test_cli.py`'s import guard and `pages.py`'s
escaping guard use, and for the same reason.

### The book wording is the owner's, taken on a rendered page

The first fix printed `Quality: N/A/100`, matching the five templates that
already print `quality_score or 'N/A'`. Rendered to
`~/Documents/nonogram-reviews/CARD-056/quality-na-sample.pdf` and read back
with `pdftotext`, that reads as a typo on paper — 100 of what? The owner chose
`Quality: N/A`, with the denominator suppressed when there is no number, so
the helper carries `73/100` or `N/A` rather than the call site appending
`/100`. The templates are left as they are: a screen carries `N/A/100` and a
printed book does not. Recorded in R2.

**Verification note.** My first attempt to confirm the rendered text decoded
zero characters out of the PDF and still reported "no `None/100`" — a vacuous
pass. Caught it by asserting the extraction saw *anything* first; the real
check uses `pdftotext`, and the current sample reads
`Quality: N/A` on the contents page and the puzzle page, `Quality: 73/100`
for the measured one.

### Left for the owner

The sample PDF is at `~/Documents/nonogram-reviews/CARD-056/`. Nothing in the
image pipeline changed, so no grid needs re-checking — but the two lines above
are book output, and the render is there if you want your own eye on it.
