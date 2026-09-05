# Architecture Directory

System design, domain model, C4 diagrams, and architectural decision records.

## Purpose

This directory contains the formal architectural documentation for the Nonogram project, including:
- System architecture and component relationships
- Context diagrams (C4 model)
- Domain model and entities
- Architectural Decision Records (ADRs)
- Design principles and patterns

## Key Architectural Concepts

### Layered Pipeline Architecture
The project follows a one-way dependency flow:

```
CLI (COMP-001)
    ↓
Orchestrator (COMP-002)
    ↓
Capabilities (COMP-003 to COMP-008)
    - Sourcing (COMP-003)
    - Clues (COMP-004)
    - Solver (COMP-005)
    - Difficulty (COMP-006)
    - Export (COMP-007)
    - Web UI (COMP-008)
```

### Core Principles

1. **Single Bounded Context** - All related to puzzle generation (CTX-001)
2. **One Dependency Direction** - Capabilities never import each other laterally
3. **Clear Module Boundaries** - Public APIs use `list[list[bool]]` for grids
4. **Domain-Driven Design** - Business logic separate from adapters

### Boundary Types

- **Grid representation:** `list[list[bool]]` for public APIs
- **Clues representation:** `tuple[tuple[int, ...], ...]` for public APIs
- **Request type:** `orchestrator.GenerationRequest` at CLI boundary
- **Error handling:** All errors funnel through `nonogram.errors.NonogramError`

## Contents

### Component Documentation
- COMP-001: CLI (Command-line interface)
- COMP-002: Orchestrator (Puzzle generation workflow)
- COMP-003: Sourcing (Grid sourcing - random, templates, images)
- COMP-004: Clues (Run-length encoding)
- COMP-005: Solver (Constraint propagation + backtracking)
- COMP-006: Difficulty (Heuristic difficulty scoring)
- COMP-007: Export (PNG, SVG, JSON, CSV, PDF)
- COMP-008: Web UI (HTTP request handler, form rendering)

### Diagrams
- C4 Context diagram (system boundaries)
- C4 Container diagram (major components)
- Component diagram (module organization)
- Data flow diagrams
- Sequence diagrams (key workflows)

### Decision Records
- ADRs for major architectural decisions
- Rationale and tradeoffs
- Alternatives considered
- Implementation notes

## Structural Guards

The architecture is enforced programmatically:
- `tests/test_cli.py` walks the codebase with AST
- Detects lateral or inward imports between capabilities
- Fails test suite on architecture violations
- Automatically covers new capability modules

## Dependency Baseline

**Closed dependency set - only stdlib + Pillow + NumPy for runtime**
- Adding third-party dependencies requires architectural review
- Dev dependencies listed in pyproject.toml
- No hypothesis - uses seeded random for property tests

## Key Design Patterns

### Module Import Rules
- Capabilities can only import from:
  - Python stdlib
  - Pillow (PIL)
  - NumPy
  - `nonogram.errors` (shared exception hierarchy)
  - **Never:** cli, orchestrator, or other capabilities

### Solver Correctness
- **Mandatory property:** Must never report false positives
- Uses independent brute-force oracle for verification
- Fast-fail on second solution found
- Performance asymmetric by design (dense grids vs mid-density)

### Test Independence
- Property tests build seeded corpora by hand
- Never use Hypothesis (not in dependency baseline)
- Minimum case count assertions prevent silent corpus shrinkage
- Cross-checks between independent implementations

## Related Documentation

- See ../guides/ for feature implementation
- See ../development/ for contribution guidelines
- See ../tests/ for requirements and test coverage
- See ../deployment/ for production configuration

## Architecture Evolution

When modifying architecture:
1. Document the decision in an ADR
2. Verify no architecture violations in tests
3. Update component documentation
4. Consider backward compatibility
5. Update this README with changes

---
Last updated: 2026-09-05
