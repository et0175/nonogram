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

- Multiplayer.
- User accounts. *(The `users` and `user_selected_books` tables in the admin
  database are unused scaffolding — see below.)*
- Persistence beyond local file export **in the generation pipeline**: the CLI,
  the web UI and everything inward of them keep no database and no state
  surviving the process.

**Amended 2026-09-22 (CARD-111).** This list read *"Multiplayer, user accounts,
or persistence beyond local file export"* until the admin panel shipped a
Postgres database — six tables, ten migrations, deployed — which made the
persistence clause false of the product while it was still being cited as the
reason the architecture has no database (three C4 diagrams, ADR-0021, and two
decisions in `decisions/open.yml` that were collapsed rather than taken on its
authority). The clause now says which surface it governs. The admin panel keeps
a database of batches, puzzles, books and generation history, and that is the
only exception.

The user-accounts clause stands, and is **contradicted by the schema rather
than by any behaviour**: `users` (with `email`, `subscription_tier`,
`puzzles_generated_month`) and `user_selected_books` are created by migration
`001` and referenced nowhere in the code. They describe a subscription website
that does not exist. Whether that is a direction to keep or scaffolding to drop
is an open product question, not a modelling one; until it is answered, no code
path may read or write them. Formalized as CON-017, superseding CON-003.

(Color/multi-value nonograms and an interactive/playable puzzle output are
**not** non-goals — they were deliberately deferred as "later" candidates;
see `meta/kanban/backlog.md`.)

## Context constraints

- Standalone tool: no external systems, no network dependency, local file
  I/O only (reads an optional source image; writes PNG/SVG/JSON/CSV).
- Target interface: CLI (Python 3.14).
- Source material: this vision was written from three intake documents — the
  original idea notes, a flow diagram, and a formalized requirements document
  carrying the FR/NFRs and 6 resolved decisions (interface, grid sizes,
  difficulty scoring, image conversion, ambiguous-image policy, no interactive
  UI in v1). **None of the three is in this repository**, and the `docs/` paths
  this line used to give for them resolved to nothing (checked 2026-09-22,
  CARD-071). What survives of them is here:
  `meta/architecture/inputs/raw-requirements.md` (the intake log),
  `meta/architecture/requirements.yml` (the FR/NFR registry those decisions
  became) and `meta/architecture/decisions/` (the decisions themselves).
