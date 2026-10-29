# CARD-315: The kill matrix's plant window is declared for one consumer and unguarded for the other — a concurrent `git` sees the mutant, and the symptom is unreadable

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Observed 2026-10-29 during CARD-308's implementation round, which flagged it rather than burying it; diagnosed from source by CARD-308's review cycle 1 and confirmed by the orchestrator. Cut on owner decision the same day.
**Idea:** —
**Wave:** —
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/kill_matrix.py, tests/test_kill_matrix.py
**Review score:** —
**Started:** —
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
  decorator** — `_conditional_silences` (in `tests/test_guard_integrity.py`) reports a
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
