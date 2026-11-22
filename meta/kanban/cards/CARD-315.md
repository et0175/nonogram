# CARD-315: The kill matrix's plant window is declared for one consumer and unguarded for the other — a concurrent `git` sees the mutant, and the symptom is unreadable

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/315-kill-matrix-plant-window
**Worktree:** ../PythonProject4-card-315
**Source:** Observed 2026-10-29 during CARD-308's implementation round, which flagged it rather than burying it; diagnosed from source by CARD-308's review cycle 1 and confirmed by the orchestrator. Cut on owner decision the same day.
**Idea:** —
**Wave:** 89
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/kill_matrix.py, tests/test_kill_matrix.py
**Review score:** 7.5 (cycle 1/3)
**Started:** 2026-11-22T08:36Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What happened

A CARD-308 round reported one unreproduced failure and refused to tidy it away:

```
tests/kill_matrix.py:1255: LeakedPatch
… and a concurrent `git status` showed   M tests/test_db_engine_lifecycle.py
… while `git diff` was EMPTY
```

It did not reproduce in three later runs and the tree was clean. Its own hypothesis
— that it had run `git add`/`git commit` while the instrument was mid-cycle — is
**correct, and provable from source rather than by racing.**

## Why it is a real finding and not a flake

**The module declares this window itself.** `tests/kill_matrix.py:224-228`:

> *"the mutant sits on disk for the length of that mutant's pytest subprocess, which
> is exactly when the destructive fixtures would run. (The `cp -p` backup names the
> same inode, so the file **is** restored afterwards — **the hazard is the window, not
> a persistent clobber**.)"*

And the mechanism is exactly as described: `_apply` ends in
`path.write_text(source, encoding="utf-8")` — **the real tracked path** — with the
restore a `cp -p` in a `finally`, verified by `diff -q` **and** `shasum -a 256`.

**So the window is known. What is unguarded is who else can look through it.** The
declared consumer is **destructive database fixtures**, and that one *is* guarded —
`_refuse_forbidden_path` refuses an edit landing on either half of the database guard,
in three spellings (`..`/symlinks via `realpath`, and `casefold`-ed because this
board's volume is case-insensitive and `tests/CONFTEST.py` walked straight past a raw
tuple compare).

**The undeclared consumer is `git`.** A concurrent `git add`, `git commit`, `git
status` or `git diff` reads the working tree during the plant, and nothing serialises
against it.

**And the instrument deliberately does not take the board's lock, for a stated and
good reason.** `:88-96`:

> *"every full-suite gate holds one for its whole duration, and a strict reading
> therefore cannot run inside the gate that must certify it. **It never writes a lock
> anywhere**…"*

**That reason is about pytest contention. `git` is a different axis, and the stated
reason does not reach it.** So "just take the full-suite lock" is already correctly
rejected and is not this card's answer.

## The second half of the problem: the symptom is unreadable

`M <file>` with an **empty `git diff`** is a genuinely confusing pair — it is what you
see when the file is caught between plant and restore, but it reads like a corrupted
index. The orchestrator could not tell from it whether the tree was safe, and
`LeakedPatch` at `:1255` fires on *"SHIPPED is not FAIL-free"*, whose message is about
baselines and says nothing about a concurrent writer.

**That ambiguity cost more than the window did.** An operator who sees it has to
decide between "my tree is corrupt" and "something else is mid-cycle", with no
evidence either way.

## What to implement — the decision, with the options measured rather than assumed

**This card decides between three shapes and records why.** None is obviously right
and two have real costs:

1. **Serialise against `git` specifically.** A narrow advisory marker the instrument
   writes for the length of a plant, which **nothing currently checks** — so this is
   only honest if something is made to check it, and inventing a convention nobody
   reads is worse than the window. Say what would check it.
2. **Remove the window.** Plant into a copy and point the subprocess at that copy
   rather than the real path. **Judge this against the module's own design**: it edits
   the real file precisely so the real import happens, and a copy risks measuring a
   tree that is not the one under test — which would be a far worse defect than the
   window. If this is rejected, reject it with the reason.
3. **Declare the bound and make the symptom legible.** Accept the window as
   irreducible, state it where an operator meets it, and make the failure say *"a
   concurrent writer may have seen a planted mutant; the tree restores itself, check
   `git diff` after the run"* rather than only *"SHIPPED is not FAIL-free"*. The
   cheapest and possibly the right answer — the restore **is** verified by two
   independent checks, so the tree's integrity is already guaranteed.

**Whichever is chosen, two things are owed regardless:**

- **The window must be stated where `git` is the reader**, not only where database
  fixtures are. The `:224-228` note names one consumer; a second sentence names the
  other.
- **`:96`'s "It never writes a lock anywhere" must stay true or stop being written.**
  If option 1 is taken, that sentence becomes false and must change in the same
  commit. It is exactly the class of stale self-description this board keeps paying
  for.

## Acceptance criteria

- **AC-1** (the window is stated for both consumers): *Given* the module's own
  documentation, *then* it names **both** the destructive-fixture consumer and a
  concurrent `git` reader, and says which is guarded and which is not.
- **AC-2** (the symptom is legible): *Given* a run in which a concurrent writer could
  have observed a plant, *then* the failure names that possibility and tells the
  operator what to check — distinguishable from a genuine leaked patch. (**A control
  is owed**: the two cases must produce different messages, shown.)
- **AC-3** (the tree's integrity stays proven, not assumed): *Given* any run, *then*
  every registered path is restored and verified by `diff -q` **and**
  `shasum -a 256`, as today, and a restore that does not verify still **keeps** the
  backup. **This card must not weaken that** — it is why the window is survivable.
- **AC-4** (whatever is chosen, the self-description is true): *Given* the module,
  *then* no sentence in it describes behaviour it no longer has — specifically
  `:96`'s lock claim and `:224-228`'s window note.
- **AC-5** (the decision is recorded with its rejected alternatives): *Given* the
  card and the module, *then* the chosen shape is stated **with why the other two were
  not** — because the next person to meet this will otherwise re-derive all three.

## Guardrails

- **G-1: do not take the board's full-suite lock.** `:88-96` rejects it for a stated
  reason — a strict reading must be able to run inside the gate that certifies it —
  and that reasoning is sound. Reopening it needs a measurement, not a preference.
- **G-2: do not weaken `_refuse_forbidden_path`.** Its three spellings each exist
  because one of them walked past a raw tuple compare; the `casefold` arm in
  particular is load-bearing on this board's case-insensitive volume.
- **G-3: do not weaken the restore's double verification** (`diff -q` **and**
  `shasum -a 256`), nor the rule that a path is restored **before** any verification
  failure is raised, nor that a non-verifying restore **keeps** its backup.
- **G-4: do not make the instrument unable to run inside a gate.** That is the
  property `:88-96` protects.
- **G-5: no test deleted, renamed, skipped or merged** — `parametrize` ids included.
  (**gate**: node-id set difference with `-o addopts=''`.)
- **G-6: a skip-related control attaches its marks by ASSIGNING `pytestmark`, never by
  decorator** — `_conditional_silences` (defined at **`tests/test_suite_profile.py:2743`** — *not* `test_guard_integrity.py`, which only mentions it in prose at `:1518`; the orchestrator mis-propagated a correction that was about the sibling functions `_module_scope_silences` and `_check_log_invocations`) reports a
  `skipif` whatever it is keyed on. Verify `== []` for any file you touch.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0039/R3 — an exemption is a claim and carries a control for what it must not absorb (check: review-lens)
- ADR-0006/R1 — the dependency baseline (check: **the ref is a phantom pointer; the RULE is tested at `tests/test_export_pdf.py:1249`** — verify the substance, and see CARD-307 for the pointer)

## Architecture context

- **ADR:** ADR-0039/R1-R3
- **Components:** none in `src/` — this is a test instrument
- **Trace:** nothing is re-stamped; the subject is an instrument, not a requirement.

## Worktree notes

- **The report that found this was right to flag it and right not to chase it.** It
  observed the symptom once, could not reproduce it in three runs, named its own most
  likely cause, and said *"a one-off I cannot explain is not a one-off I should
  bury."* The diagnosis then came from **reading `_apply` and the restore**, not from
  racing — which is the cheaper and more reliable route for a window like this.
- **It was the orchestrator's own commits that surfaced it**, committing card files
  while an impact run was inside the instrument. That is now a routine shape on this
  board: three cards in flight, each with rounds running, and a human or orchestrator
  committing bookkeeping between them. **The window will be looked through again.**

### [Implementation] 2026-11-22: option 3, plus a writer check; the window is kept and stated for both readers

**The premise, re-measured before any change.** The card was written before CARD-396. Today:
- On the real tree (`tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces`, with `git status --porcelain` on its two planted files polled every 0.5 s): with `KILL_MATRIX_WORKERS=1` (serial, in place), **79 of 176 polls** showed `M` on `tests/test_db_engine_lifecycle.py` or `src/nonogram/db/session.py`. With the default (`default_workers()` = 4 on this 11-core host, so lanes), **0 of 68 polls** did. sha256 of both files was unchanged after each run, and `git status` was clean. So the suite's one real-tree anchor no longer opens the window on this host. The window stays open for `workers=1` (the `Runner` default and the README's usage), for a path outside `repo_root`, and on a host with 2 cores or fewer.
- On a scratch git repo under `/private/tmp/claude-501/card315/` with HEAD's code (`window_demo.py`, the git command run inside the mutant's reading):
  - (A) `git status` inside the window printed ` M km_target.py`. After the run, status and diff were both empty. That is CARD-308's pair, from the window alone.
  - (B) A `git add` inside the window left `MM` after the run, with the mutant in `git diff --cached`. The restore does not reach the index.
  - (C) A `git stash push` inside the window: the mutant's cell was **published as PASS** (it is FAIL in A), with no refusal, and the stash held the mutant. This is a silently wrong figure, not only a window.
- **Two runs in one scratch tree** (`two_runs_demo.py`: the second run backs up while the first run's mutant is planted, and ends after it). At HEAD, both published, and the **mutant stayed on disk**. The second run restored its "pristine" backup, which was the mutant, and its verification agreed. So "not a persistent clobber" was false for a second writer.
- CARD-396's `SharedTree` plant (several writers in one tree) raised the plain `SHIPPED is not FAIL-free before any mutant` in 5 of 5 trials at HEAD (`shared_tree_probe.py`). That is the card's unreadable symptom, produced by a concurrent writer.

**Decision (AC-5): option 3, with detection of a writer. The window is kept.**
- **Option 1 (marker) was rejected.** Nothing would read it: no git hook here reads a marker, and an installed hook is per clone, not versioned. A marker file inside the tree is itself what `git status` and `git add -A` pick up. It would also make `It never writes a lock anywhere` false, and it comes close to G-1/G-4. A marker the instrument checks against *itself* (serialising runs per tree) would close case (D). That is a lock, so it needs the owner's decision. It is not taken here.
- **Option 2 (plant in a copy) was rejected as the only mode.** It already exists: `workers > 1` plants into lanes (CARD-396). A lane leaves out `.git`, `.env`, `*.db` and `*.sqlite*`, and CARD-396 declared "use `workers=1`" as the way to measure a target that needs them. Removing the in-place mode would remove the one reading of the real tree, which is the card's own objection.
- **Option 3 was taken, with one mechanism beyond prose.** A reader cannot be detected, but a writer leaves bytes behind. `Runner._expected` records what the runner last put on each registered path: in `_backup_registry` the backup, in `_apply` the mutant, and in `_restore` the backup again. `Runner._measure` calls `_refuse_on_foreign_write` before and after each child pytest. On any difference it raises `ConcurrentWrite`, a `LeakedPatch` subclass, so every existing catch still holds. Its message names the paths, says this is not a leaked patch, says that the restore overwrites what the writer left (and may itself restore another run's mutant), and says to check `git status`, `git diff`, `git diff --cached` and `git stash list`. A genuine leak leaves what the instrument itself wrote, so it keeps its old message.

**What changed, by name.**
- `tests/kill_matrix.py`: a module-docstring bullet "The plant window, and its two readers (CARD-315)" (AC-1, AC-5). `_refuse_forbidden_path`'s window note now names the git reader and the second-writer clobber. Its old "not a persistent clobber" is narrowed to "for this run's own edits" (AC-4). Also: the `LeakedPatch` docstring, the new `ConcurrentWrite`, `__all__`, the `Runner._expected` field, `_refuse_on_foreign_write`, and the two calls in `_measure`. The lock sentence ("It never writes a lock anywhere") stays true, and nothing new spawns a process.
- `tests/test_kill_matrix.py`: `test_ac4_a_leaked_patch_is_caught_by_the_shipped_re_run_between_mutants` is extended, not added to. The genuine leak must not be a `ConcurrentWrite`, and its message must start `SHIPPED is not FAIL-free after LEAKS`. Two writer plants (`WrittenUnder._measure` writes the target as a reading starts) must each raise `ConcurrentWrite`, whose message starts with the label and the path, does not contain `SHIPPED is not FAIL-free`, names `git diff --cached`, and leaves the target pristine. The first plant writes during `SHIPPED after AFTER`; the second puts the pristine text back during `AFTER`, which is the git-stash shape.
- `tests/README.md`: one bullet under Declared bounds that says the same thing.

**After the change (same scripts):** (A) and (B) are unchanged, as declared: a reader and the index cannot be seen. (C) raises `ConcurrentWrite ... before its child pytest started` and no longer publishes a survivor. (D): the second run raises `ConcurrentWrite`. The mutant is **still left on disk**, because the restore is G-3's and is not weakened, but the run now says so and says to read `git diff`. `SharedTree` raised `ConcurrentWrite` in 10 of 10 trials. `test_card_396_two_cells_editing_one_line_do_not_see_each_other` is unchanged: it catches `LeakedPatch` and the subclass goes through it. Its `assert not clean` branch was already unreached at HEAD (5 of 5 raised). That is recorded here and not fixed.

**AC-2 control: the two cases give different messages.** Each control was planted in the real file by `/private/tmp/claude-501/card315/control.py` (a `cp -p` backup, then restore, with the sha256 matched each time). `git diff --stat` afterwards showed only this card's three files.
- C1, both `_refuse_on_foreign_write` calls deleted: the test is RED with `LeakedPatch: SHIPPED is not FAIL-free after AFTER: ... FAIL (13,). A leaked patch and a real kill look identical`. The writer plant then reads exactly like the genuine leak (`... after LEAKS`).
- C2, the check limited to SHIPPED readings: RED, `Failed: DID NOT RAISE ConcurrentWrite`. This is the stash plant, published silently.
- C3, `_apply` no longer recording the mutant: RED, `AFTER: [...] no longer hold what this instrument last wrote there` (a false positive on every mutant reading). The bookkeeping is load-bearing.
- C4, `_restore` no longer recording the backup: `test_ac4_two_sequential_mutants_each_see_a_clean_shipped` RED, `ConcurrentWrite: SHIPPED after MARK-ROT: ...`.

**AC-3 / G-3:** `_restore`, `_verification_failures`, `_discard_workdir` and the keep-on-failure path are untouched apart from one bookkeeping line in `_restore`. A `ConcurrentWrite` is raised inside `run`'s `try`, or inside `_measure_mutant`'s `try`, so every registered path is restored and verified before it surfaces. All G-5 restore tests pass. **G-2:** `_refuse_forbidden_path` changed in its docstring only. **G-1/G-4:** no lock is taken or written. The serial real-tree anchor passed with the check in place (93.97 s, `KILL_MATRIX_WORKERS=1`, under the `git status` poll), so a concurrent git reader does not trip it. **G-6:** `_conditional_silences` returns `[]` for both `tests/test_kill_matrix.py` and `tests/kill_matrix.py`. **G-5:** the node-id set is identical before and after: 10691 and 10691 collected, 0 lines of `comm -3`. **Net test count: 0.**

**Gate** (unarmed, `-rfs`): `tests/test_kill_matrix.py` plus its neighbours `tests/test_wave_close_marker.py`, `tests/test_db_engine_lifecycle.py` (the planted subject) and the README readers `tests/test_db_url_driver.py`, `tests/test_cli.py`, `tests/test_guard_integrity.py`, `tests/test_full_suite_lock.py`, `tests/test_suite_profile.py`. Result: **993 passed, 2 skipped, 0 failed** in 255 s. The skips are `tests/conftest.py:292: Database not reachable: DATABASE_URL is not set`, the expected unarmed reason. There was no armed run: the change touches no DB path. Timing: `tests/test_kill_matrix.py` alone took 104.16 s at HEAD and 105.28 s after (84 passed both times).

**Not established / left open.**
- Case (D), a second kill-matrix run in the same tree leaving a mutant on disk, is now loud but not prevented. Preventing it means serialising runs per tree (a lock), which is the owner's call.
- A write made and undone inside one reading is not seen.
- A lane copied from a real tree that another serial run has planted into would take that mutant for pristine. This was reasoned, not measured.

[Review 1/3] Score: 7.5, two gating findings, not certified. Holds: CARD-516's changes intact; tests/test_kill_matrix.py 84 passed; G-3 restore on every path; no false fire on a concurrent git reader, the instrument's own restore, or `..` paths in copied lanes; C1-C4 red again. F-001 (Important): `_expected` is keyed on the path as written, so a mutant that edits a registered file through another spelling (`..`, or case on this case-insensitive volume) gets an honest run refused as `ConcurrentWrite` (measured on tmp trees at workers=1; the case spelling also at workers=2), contradicting `_refuse_unless_topology_holds`, which supports that route. F-002 (Important, ADR-0039/R1): the after-child check has no control; deleting that call leaves both tests green (2 passed), because both writer plants write before the child starts, while a real in-window `git stash` lands during the child. F-003 (medium): `_expected` is never reset per `run()`, so a reused Runner checks the previous run's paths (measured). F-004 (low, pre-existing): a detected foreign write is overwritten by the restore with no copy kept. F-005 (info): the notes' "does not fire on an honest run" is contradicted by F-001 and F-003.

### [Fix round 1] 2026-11-22: review cycle 1's F-001..F-005

**What changed, by name** (`tests/kill_matrix.py` unless stated):
- **F-001.** `Runner._expected` is now keyed on the file's identity, `(st_dev, st_ino)`, through the new `Runner._expect`. The value keeps the spelling last written through, and that spelling is what gets read back. I chose inode identity over `realpath` + `casefold` because it is exact on both case-sensitive and case-insensitive volumes. A casefolded key would merge two genuinely distinct files on a case-sensitive volume, and here that would mean a false refusal. `cp -p` and `write_text` both write into the existing inode.
- **F-002.** In `test_ac4_a_leaked_patch_is_caught_by_the_shipped_re_run_between_mutants` (`tests/test_kill_matrix.py`), the second writer plant (`AFTER`, which puts the pristine text back: the git-stash shape) now writes in `WrittenUnder._pytest`. That is after the reading's first check, as the child is spawned. Only the check made after the child ends can see it. Each plant asserts which check fired, by its `when` text.
- **F-003.** `run()` now calls `self._expected.clear()` first. That covers lanes too, since they branch off later.
- **F-004.** When it is set for an in-place run (`Runner._keeps_foreign`, set by `run`'s serial branch), `_refuse_on_foreign_write` copies the bytes the foreign writer left to `workdir/foreign.N.<name>` before the restore, and names those copies in the message. `run`'s `finally` then forgets that tree instead of removing it. A lane makes no copy: its tree is private and is removed with the lane. The `_discard_workdir` docstring and the module docstring now say so.
- **The AC-4 test, extended rather than duplicated.** The second plant's kept copy must hold the writer's bytes; the test then removes it. A reused `Runner` makes the honest runs: run 1 mutates `km_leaky.py`, then the caller edits `km_leaky.py` (F-003). Run 2 names the target through `sub/..` and through `KM_SIMPLE_TARGET.PY` (F-001). It must publish a FAIL at the MARK arm for every alias, and so must the same mutants at `workers=2`. The case spelling is added only when the volume folds case (it does here; the C6 message below names it). On a case-sensitive volume, only `..` is measured.

**F-005, the claim corrected.** The previous note said that a genuine leak keeps its old message, and that a git reader does not trip the check. Both are still true. But the round-1 check **did** refuse honest runs: an aliased spelling, and a reused runner (the review measured both). It was not true that it "cannot fire on an honest run". Those two honest shapes are now part of the AC-4 test, with controls C6 and C7.

**Controls.** Each was planted in the real file by `/private/tmp/claude-501/card315/control.py` (a `cp -p` backup, then restore, with sha256 matched every time) and run against the AC-4 test unless stated:
- C1, both checks deleted: RED, `LeakedPatch: SHIPPED is not FAIL-free after AFTER ... FAIL (13,)`.
- C2, the check limited to SHIPPED readings: RED, `DID NOT RAISE ConcurrentWrite`.
- C3, `_apply` not recording: RED, `AFTER: [...] no longer hold what this instrument last wrote there`.
- C4, `_restore` not recording: `test_ac4_two_sequential_mutants_each_see_a_clean_shipped` RED, `ConcurrentWrite: SHIPPED after MARK-ROT`.
- **C5 (F-002), only the after-child call deleted:** RED, `Failed: DID NOT RAISE ConcurrentWrite`.
- **C6 (F-001), keyed on the spelling again:** RED, `ConcurrentWrite: ALIAS-0: ['.../km_simple_target.py', '.../KM_SIMPLE_TARGET.PY'] no longer hold ...`. This run is serial; the `workers=2` arm has no control of its own, because the serial arm reds first.
- **C7 (F-003), `_expected.clear()` deleted:** RED, `ConcurrentWrite: SHIPPED: ['.../km_leaky.py'] no longer hold ...`.
- **C8 (F-004), the copy write deleted:** RED, `FileNotFoundError: ... foreign.0.km_simple_target.py`.

Afterwards, `git diff --stat` showed only `tests/kill_matrix.py` and `tests/test_kill_matrix.py`. I removed the temp trees the C3, C7 and C8 control runs left behind. The green runs leave none.

**Gate** (unarmed, `-rfs`): the same set, `tests/test_kill_matrix.py` plus `tests/test_wave_close_marker.py`, `tests/test_db_engine_lifecycle.py`, `tests/test_db_url_driver.py`, `tests/test_cli.py`, `tests/test_guard_integrity.py`, `tests/test_full_suite_lock.py` and `tests/test_suite_profile.py`. Result: **993 passed, 2 skipped, 0 failed**. Both skips are `tests/conftest.py:292: Database not reachable: DATABASE_URL is not set`. `tests/test_kill_matrix.py` alone: 84 passed in 81.49 s. G-6: `_conditional_silences` returns `[]` for both files. G-5 and net count: 10691 collected, node-id set identical to the pre-card baseline, **net 0**.
