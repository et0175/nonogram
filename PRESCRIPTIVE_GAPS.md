# Prescriptive Gaps Checklist
**Status:** For resolution during forge:reverse brainstorm  
**Date:** 2026-09-05  
**Phase:** Gap elicitation before forge:architect decision-surfacing

---

## Overview

This checklist identifies **prescriptive unknowns** that the code alone cannot tell us:
- **Why** architectural choices were made (rationale behind ADRs)
- **How much** (NFR thresholds, performance targets, retry limits)
- **When** to give up (timeout bounds, max retries, failure modes)
- **Acceptance criteria** from tests that need formalization

These gaps will be filled during the reverse brainstorm session.

---

## Category 1: NFR Thresholds & Performance

### Timeout & Performance Bounds

| Item | Current Code | Gap | Priority | Notes |
|------|--------------|-----|----------|-------|
| **Solver timeout** | `propagate.py`/`search.py` has timeout hooks | No configured value | HIGH | When to abort uniqueness check? (1s? 5s? 30s?) |
| **Max grid size** | CON-011: 10..30 per side | Aspirational vs enforced? | HIGH | Code allows 30x30 = 900 cells; solver performance at boundary? |
| **Retry/resampling bound** | `GenerateRequest` has retry_attempts | Value not in requirements | HIGH | Max attempts before abandoning generation? (10? 100?) |
| **Difficulty tier scoring** | `difficulty.py` has heuristic | Scoring thresholds unknown | MEDIUM | Easy: 0-30? Medium: 31-65? Hard: 66-100? (hypothetical) |
| **Density tolerance** | ±3 percentage points (ADR-0003) | Rationale missing | MEDIUM | Why ±3 specifically? Tuned empirically or arbitrary? |
| **Image processing** | Floyd-Steinberg dithering, resize | Quality acceptance criteria | MEDIUM | What defines "good" dithering? Contrast threshold? |

### Throughput & Load

| Item | Gap | Priority | Notes |
|------|-----|----------|-------|
| **Concurrent generations** | No capacity documented | MEDIUM | How many simultaneous puzzles can Railway handle? |
| **Average response time** | Not measured | MEDIUM | Target SLA for puzzle generation (10s? 30s? 2min?) |
| **Large grid performance** | Solver is "known-hard" at 40x40+ | MEDIUM | Actual timings needed for 30x30 / 25x25 / 20x20 |

---

## Category 2: ADR Rationale & Alternatives

### Missing Rationale

| ADR | Decision (Code) | Gap | Priority |
|-----|-----------------|-----|----------|
| **ADR-0003** | ±3 point density tolerance | Why not ±5? ±10? Why this specific value? | MEDIUM |
| **ADR-0006** | Pillow + NumPy stack | Were PIL/OpenCV/Scikit-image considered? | LOW |
| **ADR-0007** | Fixed library (no plugin registry) | Why not a plugin pattern for extensibility? | LOW |
| **ADR-0010** | Validation inward of CLI (in domain logic) | Why not in argparse? Trade-offs? | MEDIUM |
| **ADR-0015** | Random seed as optional parameter | Why optional vs. always-seed? When to auto-seed? | MEDIUM |

### Retry/Nudge Strategy

| Item | Code Behavior | Gap | Priority |
|------|---------------|-----|----------|
| **Retry on uniqueness fail** | Regenerate whole grid or nudge pixels | When nudge vs regenerate? | HIGH |
| **Pixel nudge algorithm** | Implementation in `sourcing/` | Why this algorithm? Converge guarantee? | MEDIUM |
| **Backoff strategy** | Unknown | Exponential? Linear? None? | MEDIUM |

---

## Category 3: Test-Mined Acceptance Criteria

### E2E Tests → AC Extraction

The Playwright E2E suite (nonogram-web/e2e/) encodes acceptance criteria that should be formalized:

| Test File | Test Name | Encoded AC | Needs Formalization |
|-----------|-----------|-----------|-------------------|
| `form_submission.spec.ts` | `should generate puzzle with default params` | "Form submits with size=20, density=30" | ✅ FR-001 AC? |
| `form_submission.spec.ts` | `should reject invalid size` | "Sizes outside 10-30 rejected" | ✅ CON-011 AC? |
| `form_submission.spec.ts` | `should handle image upload` | "Image converted via dithering, grid produced" | ✅ FR-003 AC? |
| `file_download.spec.ts` | `should download all formats` | "JSON/CSV/PNG/SVG all generated on request" | ✅ FR-011 AC? |
| `ui_interaction.spec.ts` | `difficulty selector changes` | "Easy/Medium/Hard options functional" | ✅ FR-008 AC? |
| `edge_cases.spec.ts` | `oversized image rejected` | "Images outside aspect-ratio band refused" | ✅ FR-021 AC (CON-012)? |

**Action:** Mine Playwright tests and append ACs to relevant FRs.

---

## Category 4: Invariants & Enforcement

### Code-Enforced vs. Test-Asserted

| Invariant | Where Enforced? | Confidence | Gap |
|-----------|-----------------|-----------|-----|
| **Uniqueness (INV-001)** | Solver returns 0 or 1; export gated on 1 | HIGH | Timeout behavior when solve > threshold? Fail? Wait? |
| **Clue-grid consistency (INV-002)** | RLE encoder checked bidirectionally | HIGH | Is this actually bidirectional verified in code? |
| **Retry bound (INV-003)** | RetryExhausted exception thrown | MEDIUM | Bound value? Configurable? |
| **Aspect ratio (INV-004)** | Image sourcing crop logic | MEDIUM | Exact formula? Where is >2x threshold enforced? |
| **Export consistency** | All export formats use same data | MEDIUM | Verified per format? Or bulk test? |

---

## Category 5: External System Integration

### Next.js / Node.js / Railway

| Component | Gap | Priority | Notes |
|-----------|-----|----------|-------|
| **API request timeout** | Node.js default? | MEDIUM | POST /api/generate timeout? (30s? 60s?) |
| **File download path security** | PYTHONPATH symlink attack? | MEDIUM | Validated? Sandboxed? |
| **Memory limits** | Docker container default | MEDIUM | Per-generation memory bound? |
| **Concurrent requests** | Railway worker pool size | MEDIUM | How many simultaneous puzzles on Railway? |
| **Persistent storage** | No database; temp files cleaned? | MEDIUM | Verify cleanup on error paths |

---

## Category 6: Deployment & Operations

### NFR-ish Constraints

| Item | Documented | Gap | Priority |
|------|-----------|-----|----------|
| **Container startup time** | Unknown | Measure and document | LOW |
| **Cold start (Railway)** | Unknown | Measure and document | LOW |
| **Logging & observability** | Basic to console | Structured logs? Tracing? | MEDIUM |
| **Error messages (user-facing)** | Generic NonogramError | Internationalization? Specific codes? | LOW |
| **Rate limiting policy** | None documented | Needed for Railway? | MEDIUM |

---

## Category 7: Documentation Gaps in Code

### Comments vs. Behavior

| File | Gap | Priority |
|------|-----|----------|
| `solver/propagate.py` | Why "mask_runs" reimplemented vs imported from clues.py? | LOW (documented in CLAUDE.md) |
| `sourcing/image.py` | Floyd-Steinberg rationale? | MEDIUM |
| `difficulty.py` | Scoring formula derivation? | MEDIUM |
| `orchestrator.py` | Retry/nudge decision logic | HIGH |

---

## Resolution Plan

### Phase 1: Reverse Brainstorm (This Session)

**Participants:** Developer (you) + Forge model curator

**Agenda:**
1. **NFR Thresholds** - Go through Category 1, gather actual values/targets
2. **ADR Rationale** - Fill Category 2 gaps with design intent
3. **Test AC** - Formalize Playwright tests as FRs (Category 3)
4. **Invariants** - Verify enforcement patterns (Category 4)
5. **Integration** - Document external system contracts (Category 5)
6. **Ops** - Document deployment constraints (Category 6)

**Output:**
- Updated requirements.yml with AC from tests
- New ADR drafts with rationale + alternatives
- NFR/EC specs with actual thresholds
- Curation status: flip gaps-filled entries to `source: authored`

### Phase 2: Model Validation

After brainstorm:
```bash
forge:architect-validate --phase all --as-built  # Validate as-built entries
forge:status                                      # Check remaining gaps
```

### Phase 3: Decision Surfacing

Once gaps are filled:
```bash
forge:architect-decision-surfacing  # Identify future architectural choices
forge:architect-synthesis            # Generate roadmap
```

---

## Success Criteria

- [ ] All NFR thresholds identified and documented
- [ ] Every ADR has rationale + alternatives (or marked "open decision")
- [ ] Playwright tests formalized as ACs on FRs
- [ ] Invariants verified with code locations
- [ ] External systems (Next.js, Railway, Node) documented in model
- [ ] Deployment constraints captured
- [ ] Model transitions from `as-built` to `authored` (curated)
- [ ] architect-validate --as-built passes with 0 errors

---

## Timeline

- **Now:** Identify gaps (this checklist)
- **Next:** forge:reverse drift completes → drift report available
- **Then:** Reverse brainstorm session (interactively fill gaps)
- **Finally:** Commit curated model to meta/architecture/

---

**Next Action:** Wait for forge:reverse drift to complete, then begin brainstorm with this checklist.
