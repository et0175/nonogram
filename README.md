# Nonogram Generator

A command-line tool that generates nonogram (picross) puzzles guaranteed to have
**exactly one, purely-logical solution** — the property a random black/white grid
usually lacks, and that hand-designing a puzzle around is tedious to get right. It
sources a solution grid (random today; a built-in image library and user-uploaded
images are planned), derives its row/column clues, and verifies uniqueness with a
hand-rolled constraint-propagation solver before exporting it.

## Status

Under active development. `nonogram generate` now runs the full pipeline end to end
(source a grid → derive clues → verify uniqueness, auto-regenerating on an ambiguous
or unsolvable candidate up to a bounded retry cap), for the random grid source. There
is no timeout on the uniqueness check yet and no export writer, so `--export` is
accepted but nothing is written to disk. See `meta/kanban/board.md` for what's shipped
and what's next.

## Usage

```bash
python3.14 -m venv .venv
./.venv/bin/pip install -e '.[dev]'
./.venv/bin/python -m pytest         # run the test suite
./.venv/bin/nonogram --help          # inspect the CLI surface (parsing only, today)
```

## Documentation

- **[Architecture decisions](meta/architecture/decisions/adr/)** — the ADR log
- **[Kanban board](meta/kanban/board.md)** — current delivery status by card and wave
- **[Wave release notes](meta/releases/)** — what shipped in each completed wave
