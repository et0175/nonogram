# Nonogram Generator — Vision

## Problem

Hand-designing a nonogram (picross) puzzle that is guaranteed to have exactly
one, purely-logical solution is tedious and error-prone. A random black/white
grid usually does not have that property — its clues typically admit zero or
many solutions, not one.

## Goal

A small CLI tool that generates nonogram puzzles — either from a random/idea
source (random grid or built-in image library) or from the user's own
uploaded image — at a chosen difficulty level, and guarantees each puzzle it
hands back has exactly one logical solution.

## Primary actor

- **Puzzle Creator** — the developer/user running the CLI. Generates, tunes,
  and exports puzzles for their own use (printing, personal solving, sharing
  the output files with others).

## Business model

Personal/hobby tool, not commercial. No pricing, no other party served —
skipped by explicit user decision (single actor, nothing to monetize).

## Success metrics

- (none agreed yet) — hobby project; no measurable outcome target was set.

## Non-goals

- Multiplayer, user accounts, or persistence beyond local file export.

(Color/multi-value nonograms and an interactive/playable puzzle output are
**not** non-goals — they were deliberately deferred as "later" candidates;
see `meta/kanban/backlog.md`.)

## Context constraints

- Standalone tool: no external systems, no network dependency, local file
  I/O only (reads an optional source image; writes PNG/SVG/JSON/CSV).
- Target interface: CLI (Python 3.14).
- Source material: `docs/monogram.md` (original idea notes), `docs/monogram_idea`
  (flow diagram), `docs/requirements.md` (formalized FR/NFR and 6 resolved
  decisions — interface, grid sizes, difficulty scoring, image conversion,
  ambiguous-image policy, no interactive UI in v1).
