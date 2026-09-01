# ADR-0019: Web UI component boundary

**Status:** Accepted
**Date:** 2026-08-30
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** server-rendered

One form page, one POST endpoint, one result page; no JSON API, no separate
consumer to version a contract for (CON-008 already rules out any richer
client). This is what silences the contract-first/OpenAPI gate for this
ADR's scope.

## Context

FR-017 adds a local web UI that presents the same generation options as the CLI and, on submission, drives the same `GenerationRequest`-shaped orchestrator pipeline the CLI uses — CON-007 already states this explicitly: the web UI is "an additional inbound adapter," not a new domain concept, and both interfaces are first-class. ADR-0007 fixed the internal module architecture for the single bounded context CTX-001: a thin `cli.py` adapter (COMP-001) that only parses arguments, a pipeline orchestrator (COMP-002) that owns the Puzzle aggregate and the cross-cutting invariants (INV-002 the export gate, INV-003 the retry/nudge counter), and a set of capability modules that never import `cli.py`, the orchestrator, or each other laterally. That inward-only dependency rule is not just documented — `tests/test_cli.py` enforces it mechanically by walking `src/nonogram/**/*.py` with `ast` and failing on any module that imports outward or sideways; today the adapter rank recognizes exactly one module name, `cli`.

What is not yet settled is where the new HTTP-facing code — routing, form rendering, request parsing, mapping form fields onto `orchestrator.GenerationRequest`, and catching `NonogramError` subclasses to shape them into the structured failure responses EC-003 requires — actually lives in that module graph, and how the structural import guard is made aware of a second adapter without weakening the rule it enforces for every other module. CTX-001 is the project's only bounded context (contexts.yml), covering a single aggregate (AGG-001) and a single actor (ACT-001); BCON-0001 (hard) forbids the tool ever being network-exposed or multi-user, and CON-003 forbids persistence beyond local file export. Whatever this decision settles has to be consistent with those standing constraints rather than working around them.

## Decision

We adopt the parallel adapter component: a new component COMP-008 "Web UI Adapter" (`src/nonogram/web/`), sibling to COMP-001 (`cli.py`), inside CTX-001 and inside the same single container. COMP-008 owns HTTP concerns only — routing, form rendering, request parsing, mapping form fields onto `orchestrator.GenerationRequest`, and catching `NonogramError` subclasses to shape them into EC-003's structured failure responses — and contains zero domain logic and zero validation, mirroring `cli.py`'s "parsing only" rule from ADR-0007. It is launched as a `nonogram serve` subcommand under the existing ADR-0010 argparse tree, which keeps ADR-0008's single console entry point rather than adding a second one; that launch-mechanism question is folded in here as a direct consequence of where the adapter lives, per open.yml's delta notes, rather than surfaced as its own decision. `tests/test_cli.py`'s structural import guard is extended with a narrow, explicit adapter allowlist (today a single name, `cli`, at rank 0) so `web` joins it at the same rank and may import the orchestrator exactly as `cli.py` already may; capability modules remain unable to import either adapter or each other laterally.

This satisfies ADR-0007's inward-only dependency rule literally (adapters depend on the orchestrator, the orchestrator depends on capability modules, nothing points back out or sideways), matches CON-007's own framing of the web UI as "an additional inbound adapter," and requires zero change to COMP-002 through COMP-007 since `GenerationRequest` is already adapter-agnostic (FR-017). It keeps the C4 container view a single container with one more inbound relationship from ACT-001, the smallest possible diff to `containers.puml`, and keeps COMP-008 as testable as `cli.py` — the request-to-`GenerationRequest`-to-orchestrator mapping can be exercised without opening a socket.

## Alternatives considered

### shared_request_assembly_layer

The same COMP-008 adapter as chosen, plus extracting the option surface both adapters share — the field set, its defaults, and the mapping onto `GenerationRequest` — into a small shared inward module both adapters import, so the two interfaces cannot drift apart on which options they expose. This directly addresses the strongest objection to the plain parallel-adapter shape (two adapters now duplicate the same option surface, and nothing structurally prevents them diverging) and would make CON-007's promise that both interfaces expose the *same* options an enforced-by-construction property rather than a review concern. It was rejected as premature over-generalization: today there are exactly two adapters and one option set, and an abstraction built to prevent drift between two call sites is the same kind of speculative generality ADR-0007 already rejected once, in `strategy_plugin_registry` — that ADR turned down entry-point-discoverable sourcing modes and export formats because "entry-point discovery is real machinery solving a problem this tool does not have yet," and a shared assembly module here solves a problem (divergence between two known, fixed adapters) that has not materialized either. It would also introduce a module that fits neither of ADR-0007's two tiers (adapter, capability), forcing the import guard to grow a third category instead of a two-item allowlist, and carries a real risk of the shared module accumulating domain validation — exactly what ADR-0007 and ADR-0010 both deliberately push inward, past the adapters.

### separate_web_context

Model the web UI as its own bounded context (CTX-002) and/or its own deployable container, integrating with CTX-001 across a defined interface instead of an in-process call. This was rejected because no context-boundary signal exists to justify it: contexts.yml already ruled out every signal that would separate a context, and the web UI adds none — same aggregate (AGG-001), same ubiquitous language, same single actor (ACT-001, explicitly "one actor either way"), same lifecycle, same owner. It also directly contradicts two standing constraints rather than merely being unnecessary: BCON-0001 (hard) forbids the tool ever being network-exposed or multi-user, and CON-003 forbids any persistence beyond local file export — the futures a separate context or container would buy optionality for (independent versioning/deployment, network-boundary isolation) are exactly the futures those constraints already forbid. It would turn an in-process function call into an integration with a wire contract, failure modes of its own, and a second deploy unit, for a single-user local hobby tool — cost with no compensating benefit.

## Consequences

### Positive

- Preserves ADR-0007's inward-only dependency rule literally: COMP-008 depends on the orchestrator, the orchestrator depends on the capability modules, nothing points back out or sideways — the rule already proven for COMP-001 is reused rather than re-derived.
- Zero change to COMP-002 through COMP-007: FR-017 already states `GenerationRequest` is adapter-agnostic, so the reuse is real rather than aspirational, and the whole retry/nudge/uniqueness pipeline behind the orchestrator is untouched.
- Keeps the C4 container view a single container (ADR-0008's one local process) with a second inbound relationship from ACT-001 — the smallest possible diff to `containers.puml`, with no new context and no context_map entry.
- COMP-008 stays as testable as `cli.py`: the request-to-`GenerationRequest`-to-orchestrator mapping can be exercised as a plain function call, with no socket needed to cover AC-049 through AC-051.

### Negative

- Requires editing `tests/test_cli.py`'s structural import guard, which is the actual enforcement mechanism for ADR-0007's central rule — a guard with an allowlist is weaker than a guard without one, and the allowlist must stay narrow (adapter packages only, both at the same rank) or the rule erodes as more adapters are imagined.
- Concentrates a second kind of cross-cutting error-mapping concern (EC-003's HTTP structured-failure shaping) next to the CLI's existing exit-code mapping (`exit_code_for`) over the same `NonogramError` hierarchy, with a real risk the two taxonomies drift out of sync as new error types are added.
- Two adapters now duplicate the same option surface (size, density, difficulty, name, export formats); adding a future option means touching both `cli.py` and `web/`, and nothing in this decision structurally prevents them diverging — accepted here as premature to solve now (see `shared_request_assembly_layer`), but a real, named cost.

### Neutral

- Settles only the module/component boundary for the web UI; it does not decide what serves the HTTP layer itself (DEC-020, dependent on this ADR) or how a long-running generation request is handled (DEC-022, which depends on DEC-020) — both build on COMP-008 existing at this location.
- The `nonogram serve` subcommand is a direct, non-architectural consequence of this placement (one console entry point, per ADR-0008/ADR-0010) rather than a separately decided launch mechanism.
- Establishes the precedent that a *second* inbound adapter to the same orchestrator is a cheap, expected extension of ADR-0007's shape — future adapters (if any) are expected to follow the same pattern rather than reopen this question.

## References

- DEC-021 (resolved by this ADR)
- CTX-001 (the single bounded context COMP-008 lives inside)
- COMP-001, COMP-002 (the adapter this decision mirrors, and the orchestrator COMP-008 drives)
- FR-017, CON-007, CON-008 (the web UI capability and its "same pipeline, same options" and no-in-browser-preview constraints)
- EC-003, AC-049, AC-050, AC-051 (the error-surfacing and behavioral contract COMP-008 must satisfy)
- ADR-0007 (internal module architecture and the inward-only dependency rule this ADR extends)
- ADR-0008 (packaging/single console entry point), ADR-0010 (argparse subcommand tree `nonogram serve` attaches to)
- DEC-020, DEC-022 (dependent decisions that build on COMP-008's existence at this location)

## History

- 2026-08-30: Created — adopted the parallel adapter component (COMP-008, `src/nonogram/web/`) over extracting a shared request-assembly layer and over modeling the web UI as a separate bounded context.

## Rules

```yaml
- id: ADR-0019/R1
  statement: >-
    The web UI adapter (src/nonogram/web/) contains HTTP concerns only —
    routing, form rendering, request parsing, and mapping onto
    orchestrator.GenerationRequest — and no domain logic or validation,
    mirroring cli.py; it may import the orchestrator but no capability
    module may import it or cli.py.
  scope: {contexts: [CTX-001], code: ["src/nonogram/web/**", "src/nonogram/cli.py"]}
  check: {kind: test, ref: test_every_import_in_the_package_points_inward}
  severity: mandatory
```
