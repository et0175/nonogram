# UI Test: Admin Panel Complete Flow

Test the complete admin panel workflow from batch creation through puzzle generation.

## Instructions

1. **Start Admin Console**
   - Run: `./.venv/bin/python -m src.nonogram.admin.app` on port 5005
   - Wait 3 seconds for startup
   - Verify: `curl -s http://127.0.0.1:5005 | head -1` should return HTML

2. **Open Admin Panel**
   - Navigate to http://127.0.0.1:5005 in browser
   - Verify dashboard loads with "Nonogram Admin Panel" header
   - Check "Backend Services" section shows all green ✓

3. **Test Batch Creation Flow**
   - Click "Create Batch" in sidebar
   - Verify page shows "Create Batch from Images"
   - Check all workflow steps visible (1-4)
   - Verify "Choose Image Files" and "Choose Directory" options present

4. **Test Directory Upload**
   - Test with birds directory: `/silhouette/animals/birds/`
   - Verify can select directory
   - Confirm image list appears (should show ~10 bird images)
   - Check no "Failed to load image" errors

5. **Test Image Preview & Sizing**
   - From image preview page, verify:
     - Preview images load (200px boxes)
     - No "Failed to load grid" errors
     - Sizing options work (Fixed/Min/Max)
     - Default size selector works

6. **Test Puzzle Generation**
   - Start generation from preview page
   - Wait for completion
   - Verify "Generated Puzzles" page loads
   - Check puzzle grids display correctly
   - Verify no "Failed to load grid" errors
   - Download buttons should work

7. **Test with Different Directories**
   - Repeat steps 4-6 with:
     - Crabs directory: `/silhouette/animals/crabs/`
     - Single large image
   - All should work without errors

## Success Criteria

- ✓ Admin panel loads on port 5005
- ✓ Batch creation page displays all options
- ✓ Directory upload works for birds and crabs
- ✓ Image previews load without errors
- ✓ Puzzle generation completes successfully
- ✓ Generated puzzles display correctly
- ✓ No "Failed to load" errors anywhere
- ✓ All workflow steps complete without errors

## Failure Scenarios to Test

- Invalid image directory (should show error)
- Very large images (should handle gracefully)
- Mixed image formats (JPG, PNG together - should work)
- Rapid successive uploads (should queue properly)

## Notes

- Port 5005 avoids macOS AirPlay conflict on 5000
- Use incognito mode if Chrome shows 403 errors
- Test data available in `/silhouette/animals/`
- All bird/crab images are ~10-250KB each
