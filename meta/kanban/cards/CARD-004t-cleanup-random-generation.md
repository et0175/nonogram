# CARD-004t: Cleanup - Deprecate/Remove Random Generation (Future)

**Wave**: 4+ (Cleanup/Technical Debt)  
**Size**: 3pt  
**Status**: Pending  
**Priority**: Low (polish, no user-facing impact)

## Summary

After Wave 3 image-based generation is stable and tested, remove random generation logic that was kept for backward compatibility. Clean up test utilities and documentation references.

## Rationale

**Why keep for now?**
- Existing tests rely on random generation for quick unit tests
- Algorithms need revalidation with real images
- Can revert easily if image generation has issues

**When to do this?**
- After Wave 3 testing complete and image workflow stable
- After 2+ weeks of production use
- When we're confident image generation is the primary path

## Acceptance Criteria

- [ ] Remove `create_batch()` method (random generation)
- [ ] Remove `_generate_random_batch()` helper
- [ ] Remove `get_generator()` stub implementation
- [ ] Remove random generation from templates
- [ ] Update tests to use only image-based generation
- [ ] Remove StrategyCounter stub (use real one)
- [ ] Remove "Random" documentation references
- [ ] Update TESTING_WORKFLOW.md to only mention images

## Files to Modify

- `src/nonogram/admin/batch_generator.py`
  - Remove `create_batch()` method
  - Remove `_generate_random_batch()`
  - Remove `get_generator()` stub
  - Remove `StrategyCounter` stub

- `src/nonogram/admin/app.py`
  - Remove `@app.route("/batch/create")` (POST for random)
  - Keep GET handler if needed for info

- `tests/test_wave1_*.py`
  - Update all random generation tests to use images instead
  - Or mark as deprecated and skip

- `docs/TESTING_WORKFLOW.md`
  - Remove random generation instructions
  - Focus on image workflow

- `docs/ADMIN_TESTING_PLAN.md`
  - Remove random generation test cases

## Test Plan

```gherkin
Scenario: Verify no random generation available
  Given: Admin panel loaded
  When: User navigates to batch creation
  Then: Only "From Images" option shown
  And: No "Random" or "Generate Random" option visible

Scenario: Old routes return 404
  Given: Old endpoint /batch/create with random params
  When: User POSTs to old endpoint
  Then: Returns 410 Gone (or 404)
  And: Helpful message: "Random generation removed. Use image-based generation instead."
```

## Commit Message

```
refactor(admin): remove random generation (replaced by image workflow)

- Remove create_batch() and random generation logic
- Remove StrategyCounter stub (use real implementation)
- Update tests to image-based workflow
- Simplify batch generation to single path

This completes the transition to image-based batch generation.
Closes CARD-004t (cleanup).
```

## Notes

- **Not urgent**: Can be done months later
- **Safe**: No breaking changes (users already on image workflow)
- **Test coverage**: Existing tests will catch any issues during removal
- **Documentation**: Update guides to reflect image-only workflow

## Related Cards

- CARD-004r: Image-based generation (replaces random)
- All Wave 3 cards (enable this cleanup)

---

**Do NOT start this card until:**
1. Wave 3 is complete and tested
2. Image workflow is stable for 2+ weeks
3. No active tests using random generation
