# UI Test: Directory Upload Feature

Test the directory upload functionality for batch puzzle generation.

## Test Scenarios

### Scenario 1: Birds Directory Upload
1. Navigate to http://127.0.0.1:5005/batch/create
2. Click "Choose Directory"
3. Select `/silhouette/animals/birds/`
4. Verify:
   - ✓ All 10 bird images appear in preview
   - ✓ Image previews load (200×200px boxes)
   - ✓ No "Failed to load image" errors
   - ✓ File sizes display correctly
   - ✓ Default puzzle size shows (Medium 15-25 cells)

5. Click "Next: Generate Puzzles"
6. Verify generation page loads with puzzles

### Scenario 2: Crabs Directory Upload
1. Navigate to http://127.0.0.1:5005/batch/create
2. Click "Choose Directory"
3. Select `/silhouette/animals/crabs/`
4. Verify:
   - ✓ All 15 crab/sea-creature images appear
   - ✓ Mixed JPG and PNG formats work
   - ✓ File sizes from 16KB to 195KB handled
   - ✓ Preview images display correctly
   - ✓ No file loading errors

5. Click "Next: Generate Puzzles"
6. Verify generation page loads

### Scenario 3: Size Configuration
1. Upload birds directory
2. On preview page, test size modes:
   - **Fixed**: Set to 15, 20, 25
   - **Min**: Should auto-calculate minimum readable size
   - **Max**: Should calculate maximum quality size
3. Verify "Apply to All" button works
4. Click individual image size boxes to verify override works

### Scenario 4: Image Name Customization
1. Upload directory
2. Edit puzzle names:
   - Change "bird1" to "my_bird_1"
   - Change "crab2" to "cool_crab"
3. Verify custom names save
4. Generate puzzles and verify names preserved in results

### Scenario 5: Batch Summary Information
1. Upload directory
2. Check sidebar information:
   - ✓ Image count displays
   - ✓ Total data size calculated (MB)
   - ✓ Size modes explained
   - ✓ Navigation buttons present
   - ✓ "Back to Images" link works

## Expected Results

All scenarios should complete without:
- ❌ "Failed to load image" errors
- ❌ "Failed to load grid" errors
- ❌ Timeout errors
- ❌ File upload failures

All images should:
- ✓ Convert to grids (content-aware crop)
- ✓ Display as 200×200px previews
- ✓ Generate puzzles successfully

## Performance Baseline

- Page load: < 3 seconds
- Image preview render: < 1 second per image
- Preview page: < 5 seconds total
- Generation page: < 10 seconds for 10-15 images

## Cleanup

After testing:
- Verify `/tmp/nonogram_uploads/` contains uploaded files
- Check files persist during batch session
- Verify cleanup after batch completes
