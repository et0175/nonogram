# CARD-143: Type a puzzle's position in the arrange step, not only up and down

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/143-arrange-type-a-position
**Worktree:** —
**Source:** owner, 2026-09-23 ("sort puzzles inside the difficulty group after adding new puzzles, and manually change ordinal numbers, not only moving up-down")
**Idea:** —
**Wave:** 27
**Depends on:** CARD-140
**Touches:** src/nonogram/admin/templates/book_arrange_puzzles.html, src/nonogram/admin/app.py, tests/test_book_arrange_position.py
**Review score:** 8.5 (1 cycle + 2 fixes)
**Started:** 2026-09-30T19:05:00Z
**Closed:** 2026-10-01T08:40:00Z
**Actual:** 0.5d
**Merge commit:** 2bfd6b8
**Blocked by:** —

## What to implement

The arrange step moves a puzzle one place at a time (`move_up` / `move_down`,
app.py:3241-3248). After adding a batch of new puzzles — which land at the end of their own
level (CARD-126) — putting one near the front of a 50-puzzle level takes dozens of clicks.
The owner asked to type the position instead.

The ordering rule already supports it. `moved_within_level(puzzle_ids, puzzle_id, offset,
tier_of)` (book_plan.py:511) takes **any** integer offset, works on the grouped view, and
returns `None` when the move would leave the puzzle's level. So a typed position is the
existing operation with a computed offset — no new ordering logic, and INV-009 is enforced by
the same function that enforces it today.

1. **A position box per row.** Each puzzle shows its number within its level and accepts a
   new one. Submitting computes `offset = target - current` **inside the level** and calls
   `moved_within_level`; the up/down buttons stay exactly as they are.
2. **Number within the level, not the book.** The owner is sorting inside a difficulty group,
   and a book-wide ordinal would invite exactly the cross-level move INV-009 forbids. Label
   it so this is unambiguous on screen — position 1 means first among that level's puzzles.
3. **Refuse clearly, never silently clamp.** A position below 1 or above that level's count,
   a non-number, or an empty box is refused with a message naming the valid range, and the
   order is unchanged. Do not clamp to the nearest legal value: a typo that silently moves a
   puzzle somewhere else is worse than a refusal.
4. **A position that changes nothing is not an error.** Typing a puzzle's current position
   succeeds and leaves the order untouched.

Out of scope: drag-and-drop, sorting a level by any key (size, title, date), moving puzzles
between levels (INV-009 forbids it and CARD-126 settled it), and any change to where newly
added puzzles land.

## Acceptance criteria

- New: typing 1 against the last puzzle of a level moves it to the front of that level and
  leaves every other level untouched.
  test: TestArrangePosition_TypedPositionMovesWithinTheLevel
- New: a position above the level's count, below 1, or not a number is refused with the
  valid range named, and the stored order is unchanged.
  test: TestArrangePosition_OutOfRangeIsRefusedNotClamped
- New: typing a puzzle's current position succeeds and changes nothing.
  test: TestArrangePosition_NoOpPositionIsAccepted
- New: for any book and any legal position, the result is a permutation of the same ids,
  still grouped by tier.
  test: PropertyTest_ArrangePosition_AlwaysAPermutationGroupedByTier

## Guardrails

- G-1: INV-009 holds — the order stays grouped by tier and no typed position moves a puzzle
  across a level boundary. The move goes through `moved_within_level`; the route must not
  reorder ids itself.
- G-2: The up/down buttons and their tests are unchanged.
- G-3: Do not edit `src/nonogram/export/**` or `tests/fixtures/a4_golden/**` (CON-019).
- G-4: No schema change — the stored order is still a list of ids, not positions.

## Architecture context

- **FR:** FR-036 (arrangement)
- **INV:** INV-009 (grouped by tier, level-confined moves)
- **ADR:** ADR-0033, ADR-0019 (the adapter holds no domain logic)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes
- [Env] forge 2026.8.17
- [Dependency met] CARD-140 merged at 5d54019.
- [Hotspot collision, run anyway on the owner's ruling 2026-09-30] CARD-129 is in flight and
  **both cards edit `src/nonogram/admin/app.py`**, the first entry in `config.yml`'s
  `conflict.hotspots`, whose rule is that two cards predicted to touch one hotspot are
  serialized regardless of their overlap score. The owner chose to run them together with this
  card's `app.py` edit kept **strictly additive and in its own region** near the arrange route —
  append, never reorder or reformat — so the two cards occupy different parts of a 4,500-line
  file and a rebase stays trivial. The orchestrator takes the rebase if it is not. Recorded
  because the rule was overridden deliberately, not overlooked: if this does conflict, the
  hotspot list was right and the next such call should respect it.
- [No other overlap] CARD-129's other files are `book_kdp.py` (new), `book_finalize.html` and
  its own test; this card's are `book_arrange_puzzles.html` and its own test. Only `app.py` is
  shared.

- [Origin] Owner, 2026-09-23, after the first real arranging session on the deployed panel.
- [Why it waits for CARD-140] Both rewrite `book_arrange_puzzles.html` — CARD-140 replaces
  the page-break indicators, this card adds a control to every row. Running them together
  buys a conflict in one template for no gain.
- [Seam] `moved_within_level`'s docstring already says "Any integer works" for the offset, so
  this card should add no arithmetic beyond `target - current` within the level.
- [One ordering rule, not two] `BookManager.move_puzzle_within_level(book_id,
  puzzle_id, offset)` (+32/-0, beside `move_puzzle_down`) is a thin public form
  of the private `_move_within_level` the buttons already use, so the typed
  position reaches `book_plan.moved_within_level` unchanged. The route's whole
  arithmetic is `target - current` inside the level; it never reorders ids and
  never re-derives the grouping (G-1, G-4 — the stored order is still a list of
  ids).
- [SUPERSEDED — see the Requirement defect section and [Fix 1] below. This bullet describes
  the EXCHANGE semantics as originally shipped at 04043df; the owner ruled for insertion on
  2026-09-30 and 55f45b6 changed it. Left in place rather than rewritten, because it is the
  honest record of what the card said and what was built before the ruling.]
- [The semantics this inherits, stated plainly] `moved_within_level` moves by
  **exchanging** the puzzle with whatever sits `offset` places away in its
  level (for the buttons' ±1 that is exactly a one-step move). So typing 1
  against the last of E1,E2,E3 stores E3,E2,E1 — E3 is first, and E1 takes the
  place E3 left, rather than E1,E2 shifting down. That is the card's and the
  brief's explicit instruction (reuse the rule, add no arithmetic beyond
  `target - current`), it satisfies every AC as written, and the tests write the
  resulting orders out by hand so the behaviour is visible rather than implied.
  The screen says so too, in the lede: "position 1 is first among that level's
  puzzles, and it changes places with the puzzle already there". **If the owner
  wanted insertion instead** (the rest of the level shifting down), that is a
  change to `moved_within_level` itself — a swap and an insertion are the same
  operation for ±1, so the buttons and their tests would be unaffected — and it
  belongs in its own card, not in a second rule behind the box.
- [Refusals] Below 1, above the level's count, not a number, or an empty box:
  the order is not touched and the page says, in one page-local
  `alert alert-danger` with `id="position-error"`, e.g. "Position not changed:
  There is no position 9 in the Easy level. Type a whole number from 1 to 3 —
  that is how many puzzles the Easy level holds. The order is unchanged."
  Nothing is clamped. Only the box the refusal named carries `is-invalid`,
  `aria-invalid="true"` and `aria-describedby="position-error"`, and it
  re-renders the owner's own entry (clipped to 20 chars) so the typo can be
  corrected — the FormField rule in `meta/design/components.md`. A position
  another level has (4 in a level of 2) is refused by this level's count, so the
  route never works out an offset that would cross a level boundary.
- [Not an error] Typing the current position flashes "This puzzle is already 2
  of 3 in the Easy level; the order is unchanged." as a success, writes nothing,
  and never sends the store an offset of 0.
- [Design system] No new colour, px or font literal, and no CSS at all: the box
  reuses `form-control form-control-sm num w-auto` with `size="3"` for its
  width, and the refusal follows the Print setup step's `#plan-error` pattern.
  `meta/design/components.md`'s ArrangeRow entry is updated with the box, its
  states and the refusal — and its "page-break divider after every 3 rows"
  clause, stale since CARD-140, is corrected in the same entry.
- [Tests] `tests/test_book_arrange_position.py`, 32 tests, all EXECUTE (none
  skip); the four `[db]` ones run on sqlite through `sqlite_session_scope`, so
  no database was created, dropped or touched. The shelf, panel and text
  helpers are imported from `tests/test_book_level_order.py` rather than copied,
  so the two cards' tests describe one screen. The property's corpus is a seeded
  `random.Random` built by hand (no hypothesis) over 48 drawn books of which 45
  are checked, and every floor is a measured figure with a margin that can
  actually fire (40 books, 30 multi-level, 8 of each of up/down/no-op against
  measured 11/11/23).
- [Suite] `pytest -o addopts=""` with the worktree as cwd: 5443 collected,
  5434 passed, 2 failed, 7 skipped. The two failures are the branch's
  pre-existing ones (`tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`,
  `tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders`).
- [Rendered row, since review.visual is off] A row reads, left to right: the
  book-wide number in accent monospace, the 52px grid thumbnail, then the info
  line "10x10 · [easy] · Position in Easy _1_ of 3", then the title input under
  it, then the up/down/remove buttons in their column on the right. The box is a
  three-character paper-coloured field with the level's label to its left and
  "of 3" to its right, so what the number counts is readable without the lede.
  On a refusal the same box gains the danger border and keeps the typed value,
  and the red-ruled alert above the list carries the sentence quoted earlier —
  the refusal reads as text, not as a colour.

### [Requirement defect] The card never decided swap vs insertion — held before merge

The implementation is faithful to the card; the card is wrong, and its acceptance criteria
cannot catch it. Verified by the orchestrator on a five-puzzle level:

    type position 1 on E5  ->  E5, E2, E3, E4, E1     (E1 flung to the end)
    click up four times    ->  E5, E1, E2, E3, E4     (E1..E4 shift down)

`moved_within_level` moves by **exchanging** the puzzle with whatever sits `offset` places away.
At +/-1 a swap and an insertion coincide, which is why the buttons have always been right — but
composing four one-step swaps IS an insertion, while one four-step swap is not. So the card's
founding premise, "a typed position is the existing operation with a computed offset", holds
only for the case the buttons already covered.

For the owner's stated use case this is the harmful direction: a new puzzle lands at the end of
a 50-puzzle level, the owner types 1, and **the puzzle that was first is flung to position 50** —
a silent scramble of an order arranged by hand. The card's own step 3 argues that a typo which
silently moves a puzzle somewhere else is worse than a refusal; this does that without a typo.

**AC-1 does not discriminate**: "typing 1 against the last puzzle of a level moves it to the
front of that level and leaves every other level untouched" is satisfied by BOTH semantics. The
card never made the choice, so no test could have caught it. That makes this a requirement
defect for the architect/decompose station rather than an implementation defect — routed there
instead of patched in a worktree, and the implementation agent was right to flag it rather than
change `moved_within_level` on its own authority.

Note for whoever resolves it: a swap and an insertion coincide at +/-1, so changing
`moved_within_level` to insert would leave the up/down buttons and all their existing tests
untouched.
### [Fix 1] The typed position inserts — the requirement defect closed, 2026-09-30

- SCOPE+ src/nonogram/admin/book_plan.py — the defect is in the ordering rule
  itself, not in what this card built on top of it. `moved_within_level` is the
  one place the semantics of "move by `offset`" is decided, so insertion could
  only be made true there; making it true anywhere else would have created the
  second ordering rule G-1 forbids.
- [The ruling] Owner, 2026-09-30: typing a position **inserts**. The puzzle
  moves there and the others shift, exactly as clicking the button that many
  times already does. `E1..E5`, type 1 on E5 → `E5, E1, E2, E3, E4`.
- [The change, in one line] `moved_within_level`'s last statement became
  `order.insert(target, order.pop(index))` in place of
  `order[index], order[target] = order[target], order[index]`. Nothing else in
  the function changed: `book_level_order` still supplies the grouped view,
  `None` still answers an offset the book has no position for, and the
  `LevelBoundary` guard is the same line it always was.
- [Why the same guard still enforces INV-009] A level is a **contiguous block**
  of the grouped order, so "the id currently sitting at the destination index
  belongs to my level" is exactly "the insertion stays inside my level" — the
  identical predicate the exchange needed, and it is read before the `pop`, off
  the pre-move list. The out-of-book case still returns `None` and the
  cross-level case still raises `CROSS_LEVEL_REFUSAL` with nothing written;
  both are pinned by tests, at ±1 in `tests/test_book_level_order.py` and now
  at an offset of +3 in the new class below.
- [The buttons were not affected — confirmed, not assumed] With insertion in
  place and before any test was edited, the two files ran 4 failed / 90 passed:
  **all four failures were in this card's own file** and all four were
  multi-step literals. `tests/test_book_level_order.py` — every up/down test,
  AC-257/AC-258/AC-259 included — was **62 passed, 0 failed, unchanged**. The
  equivalence was also checked directly: four one-step ups and one typed 1 both
  produce `E5, E1, E2, E3, E4`, and three one-step downs and one typed 4 both
  produce `E2, E3, E4, E1, E5`.
- [The discriminating test the card should have had]
  `TestArrangePosition_ATypedPositionInsertsRatherThanExchanges` in
  `tests/test_book_arrange_position.py`, 7 tests. Its class docstring states why
  ±1 cannot catch this: at one place the two rules are the same operation, they
  diverge from ±2 on, and AC-1 is satisfied by both because the moved puzzle
  lands where it was told either way — the difference is what happens to
  everything else. Proved by reverting the one line to the exchange and running
  the class: **5 failed, 2 passed**, the failures being the up-equivalence
  (`assert [4, 1, 2, 3, 0] == [4, 0, 1, 2, 3]`), the owner's E1..E5 case, the
  down-equivalence, and the store's offset of -3 in both storage modes. The two
  that passed under exchange are the INV-009 guard test in its two modes, which
  is correct: that guard must hold under either rule and is not there to
  discriminate them. The line restored, the class is 7 passed.
- [Existing literals updated — all four in this card's own file]
  1. `test_typing_one_against_the_last_of_a_level_moves_it_to_the_front`:
     `[e3, e2, e1, m1, m2]` → `[e3, e1, e2, m1, m2]`; its comment now says
     "E3 takes the front and E1, E2 each shift down one".
  2. `test_a_typed_position_inside_a_level_moves_to_that_position`:
     `[e1, e5, e3, e4, e2]` → `[e1, e5, e2, e3, e4]`; its docstring said
     "2 against the fifth easy puzzle is E2 <-> E5" and now says E5 goes to
     position 2 with E2, E3, E4 shifting down one.
  3. `test_the_store_moves_it_by_the_offset_in_either_storage_mode`
     (both modes): `[e3, e2, e1, m1]` → `[e3, e1, e2, m1]`.
  4. The module docstring's paragraph describing the inherited semantics.
  No assertion was weakened and no test was retargeted: each of these three
  tests still has the same subject — "the typed position moves the puzzle
  there" — and each still asserts the whole stored order by hand, so the rule
  is still visible rather than implied. `PropertyTest_ArrangePosition_...`
  needed no change: it grades permutation, grouping, the moved puzzle's landing
  position and the other levels, all of which hold under either rule, and its
  floors (40/30/8) are untouched and still fire.
- [Prose corrected, because a docstring that survives a semantics change is a
  lie with a long half-life]
  * `book_plan.moved_within_level` — the summary now opens on the insertion,
    names the ±1 coincidence, gives the owner's E1..E5 example **and** the
    order an exchange would have produced, and the `Raises:` clause explains
    that the destination is tested rather than the path.
  * `book_manager.move_puzzle_within_level` — "The move that function makes is
    a **swap** … exchange places" → an insertion that shifts the puzzles in
    between, with the ±1 coincidence as the reason the buttons are unaffected.
  * `book_manager._move_within_level` — its summary line ("the swap both move
    buttons make") and the paragraph that twice called the rule a "swap of
    adjacent positions" now describe the insertion in the level order.
  * `templates/book_arrange_puzzles.html`, the lede — "and it changes places
    with the puzzle already there" → "and the rest of the level shifts along to
    make room — the same move as clicking the arrow that many times". This was
    the only place the screen itself stated the old rule.
  * `meta/design/components.md`, ArrangeRow — one clause added stating what
    typing a position does, so the entry cannot outlive the behaviour again.
  * `app.py` carries no statement of the semantics (its comments say only that
    `moved_within_level` decides what the order allows, which is still true),
    so it is **untouched** — the hotspot CARD-129 shares stays byte-identical.
- [Suite] `pytest -o addopts=""` with the worktree as cwd: **5450 collected,
  5441 passed, 2 failed, 7 skipped** (+7 collected and +7 passed against the
  branch's 5443/5434, the seven new tests). The two failures are the branch's
  pre-existing ones
  (`tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`,
  `tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders`).
  `tests/test_admin_design_tokens.py` is green; no colour, px or font literal
  was added and no CSS was written. No database was created, dropped or
  recreated — the `[db]` tests run on sqlite through `sqlite_session_scope`.
- DECLARATIONS Fix-1 — the mechanism that changed is the meaning of a move's
  `offset` (exchange → insertion). Re-derived and corrected: the two
  `book_manager` docstrings, `moved_within_level`'s docstring including its
  `Raises:` clause, the arrange screen's lede, the ArrangeRow design entry, and
  this card's test module docstring. Confirmed still correct and left alone:
  `app.py`'s route comments, `place_in_level` and `book_level_order` (an add and
  the grouping are untouched by this), and `reorder_puzzles`' INV-009 contract.
  No config field, parameter or timeout acquired a second job.

- [Guard] Insertion verified by the orchestrator against the worktree's own module, in both
  directions: typing 1 on E5 of E1..E5 gives `E5, E1, E2, E3, E4`, identical to clicking up four
  times; typing 4 on E1 gives `E2, E3, E4, E1, E5`, identical to clicking down three times. A
  cross-level move still raises `LevelBoundary`, so INV-009 holds. The whole change is **one
  statement** — `order.insert(target, order.pop(index))` in place of the exchange — and the
  level guard is unmoved because a level is a contiguous block, so "the id at the destination
  belongs to my level" is the same predicate either rule needs.
- [Guard] The claim that the buttons are unaffected was **measured before any test was edited**:
  `tests/test_book_level_order.py` stayed at 62 passed / 0 failed, and the only four failures in
  the whole run were multi-step literals inside this card's own new file. The ±1 coincidence
  held exactly.
### [Fix 2] Cycle-1 review findings F-001..F-003 closed, 2026-10-01

Review `meta/review/20260930T202702Z-CARD-143-cycle1.yml`, score **8.5** — one
Important (F-001) and four Minor. F-001, F-002 and F-003 are closed here; F-004
(this card's own `[The semantics this inherits]` bullet) is the orchestrator's,
F-005 (a direct `moved_within_level` unit test beyond ±1) was ruled hygiene and
left, and the four model-wide dead check refs belong to a model-hygiene card.
**No source file changed**: `book_plan.py`, `book_manager.py`, `app.py` and the
arrange template are byte-identical to 55f45b6.

- **F-001 (Important) — `docs/BOOK_WORKFLOW_UA.md`, item 1 of `### Крок 4.
  Arrangement`.** The owner's guide still said «Перетягування немає — порядок
  змінюється кнопками **вгору / вниз**.», which this card made false. The
  orchestrator ruled the file a living guide (item 4 already describes CARD-140's
  page-break indicators), so the line was rewritten rather than dated. It now
  keeps «Перетягування немає», names the typed box (**Position in …** — the
  visible label at `book_arrange_puzzles.html:120`), says the numbering is **в
  межах рівня, а не всієї книги** — the thing a reader could most easily get
  wrong — and says what typing does: it **вставляє**, решта рівня зсувається,
  той самий результат, що й стільки ж натискань на стрілку. Three short
  sentences, the file's own register, **bold** on the UI label and on the verb,
  no English gloss; the list is not restructured and no other line is touched.
- **F-002 (Minor) — `tests/property/test_book_order.py`, `_check_move`.** The
  INV-009 property's oracle built its expectation with the swap formula while
  taking a general `offset`, green only because `_move` draws ±1 where the two
  rules coincide. It is now the insertion:
  `expected = list(sequence); expected.insert(target, expected.pop(index))`.
  The draw is deliberately **not** widened — that is a different card's call —
  but the helper is now correct for every offset its signature admits, with a
  comment saying so. Proven directly against `moved_within_level` on a
  five-puzzle easy level: at `-4` the code and the new oracle both give
  `E5,E1,E2,E3,E4` where the old swap oracle demanded `E5,E2,E3,E4,E1`; same
  disagreement at `-3` (`E1,E5,E2,E3,E4` vs `E1,E5,E3,E4,E2`), `-2`
  (`E1,E2,E5,E3,E4` vs `E1,E2,E5,E4,E3`), `+2` (`E2,E3,E1,E4,E5` vs
  `E3,E2,E1,E4,E5`), `+3` (`E2,E3,E4,E1,E5` vs `E4,E2,E3,E1,E5`) and `+4`
  (`E2,E3,E4,E5,E1` vs `E5,E2,E3,E4,E1`) — **6 of 6 offsets beyond ±1 now agree
  where the old formula disagreed**, and at ±1 the two are byte-identical, so
  nothing the property draws today moves.
- **F-003 (Minor) — `tests/test_book_arrange_position.py`, AC-4's property.**
  The property graded membership, rank-sortedness, the moved puzzle's landing
  position and every *other* level, but never the moved level's **remaining
  members** — exactly where the requirement defect lived, which is why the
  property needed no edit when the semantics changed. One clause added to the
  same loop: `[p for p in groups_after[tier] if p != puzzle_id]` equals the same
  filter over `members`. No existing assertion was weakened, retargeted or
  deleted, and the measured floors (`checked >= 40 >= 24`, `multi_level >= 30 >=
  12`, up/down/no-op `>= 8 >= 5`) stand exactly as they were, so the owner's
  ruling is now carried by all 45 checked books instead of five hand-written
  examples. **The clause bites**: with `moved_within_level` temporarily reverted
  to `order[index], order[target] = order[target], order[index]` the test fails
  at line 690 — `AssertionError: the rest of the hard level was reordered by
  inserting puzzle_000037 at 2: ['puzzle_000032', 'puzzle_000033',
  'puzzle_000036', 'puzzle_000037'] -> ['puzzle_000032', 'puzzle_000037',
  'puzzle_000036', 'puzzle_000033']` — while the **pre-fix** test file passes
  under that same revert (`1 passed`), which is the blindness the finding
  described. The insertion was restored immediately; `git diff` shows no
  `src/` change.
- [Constraints] The ordering rule is still one rule in
  `book_plan.moved_within_level` and nothing was added beside it; INV-009 is
  still enforced by the same destination guard; no dependency was added (no
  `hypothesis` — the new clause is a plain assertion over the existing seeded
  corpus); no colour, px or font literal was written and no CSS was touched, so
  `tests/test_admin_design_tokens.py` stays green. No database was created,
  dropped or recreated; the `[db]` tests ran on sqlite via
  `sqlite_session_scope` and `nonogram_dev` was not opened.
- [Suite] `pytest -o addopts=""` with the worktree as cwd: **5450 collected,
  5441 passed, 2 failed, 7 skipped** in 264s — identical to the branch baseline.
  The two failures are the branch's pre-existing ones
  (`tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`,
  `tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders`).
- DECLARATIONS F-001 — the behaviour declared by `docs/BOOK_WORKFLOW_UA.md` item
  1 was corrected (both ways of reordering, per-level numbering, insertion
  semantics). Re-derived from the shipped code and confirmed still correct, left
  alone: the arrange screen's lede, `moved_within_level`'s docstring, the two
  `book_manager` docstrings, `meta/design/components.md`'s ArrangeRow — Fix 1
  already brought all four to the insertion rule, and a repo-wide grep for
  exchange/swap/"changes places" over `src/nonogram/admin`, `meta/design`,
  `meta/architecture` and `docs/` leaves no other stale claim.
- DECLARATIONS F-002 — none (local branch): a test-internal oracle, no mechanism,
  bound, lifecycle or config meaning changed. The comment beside it now states
  which rule it is the oracle for and that ±1 is why it reads unchanged.
- DECLARATIONS F-003 — none (local branch): one added assertion over the existing
  corpus; the module docstring and the floors' own comments were re-read and are
  still accurate, so neither was edited. No config field, parameter or timeout
  acquired a second job in this fix.

- [Review 1/3] **8.5** · risk LOW · lane FAST ·
  `meta/review/20260930T202702Z-CARD-143-cycle1.yml` · 0 critical, 1 important, 4 minor.
  The Important was `docs/BOOK_WORKFLOW_UA.md:87`; closed in Fix 2, so the card now stands at
  the ~9.5 the reviewer said it would.
- **The riskiest edit turned out to be the safest part of the card, and the reviewer proved it
  rather than accepting the argument.** An exhaustive independent sweep — every book of 1–6
  puzzles × every tier assignment over {easy, medium, hard, ungraded} × every puzzle × every
  offset in [-n, n] — **386,540 cases, 0 violations** of permutation, tier grouping, the moved
  puzzle's landing index, per-level membership, other levels byte-identical, and the insertion
  property. **0 bogus refusals and 0 bogus `None`s.** And the owner's ruling verified as stated:
  one-shot insertion equals composing that many button clicks over **36,712 cases, 0
  differences**.
- **The buttons are safe as a theorem, not a coincidence**: 0 divergences between insertion and
  exchange at ±1 across every case in the sweep, and `tests/test_book_level_order.py` stayed
  62 passed / 0 failed with the file untouched by the diff.
- Mutation: **7 mutants, 7 killed** — the insert statement, the INV-009 destination guard, the
  out-of-book guard, the offset's direction, and both range bounds, plus the no-op branch.
- The reviewer also diagnosed **why the defect got through**, which is worth more than the fix:
  AC-4's property graded membership, grouping, the moved puzzle's landing position and the
  *other* levels — but never the moved level's **remaining members**, which is exactly where
  the two rules differ. Closed as F-003.
- [Orchestrator ruling] F-001 asked whether `docs/BOOK_WORKFLOW_UA.md` is a living guide or a
  dated snapshot. **Living**: item 4 of the same list already describes CARD-140's page-break
  indicators, which landed days earlier, so the file is demonstrably maintained and a false
  sentence in it is a real defect rather than an archival curiosity.
- [Guard] The rewritten Ukrainian line checked by the orchestrator against a literal
  translation: it states there is no drag-and-drop, that the order changes by the up/down
  buttons **or** by a number in the `Position in …` field, that **the numbering is per level,
  not per book**, and that the number **inserts** — the rest of the level shifting to make room,
  the same result as that many presses of the arrow. Accurate to the behaviour, and it keeps the
  file's terse register and its habit of bolding the real English control names.
- [Guard] F-003's proof was three-way, which is the right shape: the clause passes with
  insertion, **fails** with the insert statement reverted, and — the decisive third step — the
  *old* test **passed** under that same revert. The blindness was demonstrated, not asserted.
- [Guard] F-002 was a latent landmine rather than a present bug: INV-009's property helper built
  its oracle with the swap formula while taking a general `offset`, green only because the draw
  is ±1. The next card to widen that draw would have read a correct result as a regression. Now
  correct for any offset; the draw itself deliberately not widened — that is another card's call.
- F-004 closed by the orchestrator: the card's own `[The semantics this inherits]` bullet is
  marked SUPERSEDED in place rather than rewritten, so the record of what was built before the
  ruling survives.
- F-005 (minor, left open) the changed statement has no direct unit test beyond ±1; covered
  transitively by M1 and by the exhaustive sweep.
- [Build gate] PASSED on bd0b015: 5450 collected, 5441 passed, 2 failed, 7 skipped.
- [Review sync] 1 report → meta/review/
