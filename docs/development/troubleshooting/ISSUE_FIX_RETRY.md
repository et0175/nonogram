# Issue Fix: Image Retry Without Re-Upload (CARD-037 Bug)

## Issue Description

When a user uploads an image and generates a puzzle, then attempts to generate again with different settings (e.g., different size) without re-uploading the image, they would receive an error:

```
cannot read image '/var/folders/.../nonogram-upload-xxxxx': 
[Errno 2] No such file or directory
```

### How to Reproduce

1. Upload an image via web UI
2. Set size to "16" and generate → Success
3. Change size to "20" and press "Generate" again (without uploading a new image)
4. **Expected**: Generation succeeds with new size
5. **Actual**: Error "cannot read image" - file not found

## Root Cause

The CARD-037 retry flow was designed to persist uploaded images across multiple retry attempts. However:

1. Multipart form uploads create temporary files in the system temp directory
2. After each request, the handler's `finally` block deletes the temporary file
3. The next retry attempt tries to use the deleted file path, causing the error

### Code Analysis

**File**: `src/nonogram/web/handler.py`

**Problem**: The `persisted_image_path` stored the path to a temporary file that was deleted after the first request completed.

```python
# Before fix: cleanup deleted all temp files, including persisted ones
finally:
    if image_path is not None and image_path.exists():
        try:
            temp_dir = Path(tempfile.gettempdir())
            try:
                image_path.relative_to(temp_dir)
                image_path.unlink()  # Deletes both new uploads AND persisted files
```

## Solution

Implemented a two-pronged fix:

### 1. Separate Tracking of Newly Uploaded vs Persisted Images

Added `newly_uploaded_image_path` variable to track which file was uploaded in the current request vs which was persisted from a previous request.

### 2. Move Persisted Images to Stable Cache

When an image is uploaded, it's now copied to a persistent cache directory (`~/.cache/nonogram/`) before being used for generation. This ensures:

- Uploaded images survive the cleanup process
- They persist across retry attempts
- Retries don't require re-uploading the same image

### Key Changes

**File**: `src/nonogram/web/handler.py`

1. **Lines 722-743**: Track `newly_uploaded_image_path` separately from the actual `image_path` being used

2. **Lines 792-811**: After receiving an upload, copy the temporary file to stable cache:
   ```python
   # Copy temp file to persistent cache that won't be auto-cleaned
   cache_dir = Path.home() / ".cache" / "nonogram"
   cache_dir.mkdir(parents=True, exist_ok=True)
   session_id = str(uuid.uuid4())[:8]
   cached_image_path = cache_dir / f"{session_id}_{newly_uploaded_image_path.name}"
   shutil.copy2(newly_uploaded_image_path, cached_image_path)
   image_path = cached_image_path  # Use cached copy for persisting
   ```

3. **Lines 868-873**: Cleanup only the original temporary file, not the cached copy:
   ```python
   finally:
       if newly_uploaded_image_path is not None and newly_uploaded_image_path.exists():
           try:
               newly_uploaded_image_path.unlink()  # Delete only the temp file
   ```

## Testing

Added two comprehensive e2e tests in `tests/test_web_e2e.py`:

### Test 1: `test_retry_with_different_size_persists_image`

Verifies that:
- User uploads image and generates (success)
- User changes size and generates again WITHOUT re-uploading
- Second generation succeeds with persisted image

### Test 2: `test_retry_after_error_persists_image`

Verifies that:
- User uploads image with invalid settings (generation fails)
- User fixes settings and generates again WITHOUT re-uploading
- Retry succeeds with persisted image

## Benefits

1. **Better UX**: Users can retry generation with different settings without re-uploading
2. **Bandwidth**: Reduces unnecessary file uploads
3. **Performance**: Cached images are reused across attempts
4. **Reliability**: No more "file not found" errors on retry

## Cache Management

Cached images are stored in `~/.cache/nonogram/` with session IDs to avoid collisions:
- Format: `{session_id}_{original_filename}`
- Example: `375a07f3_nonogram-upload-vuk5km0r`

Note: Cache cleanup could be enhanced in future iterations with:
- Automatic cleanup of old cache files
- Configurable cache location
- Cache size limits

## Test Results

All 22 e2e tests pass, including:
- 20 existing tests (unchanged)
- 2 new retry-specific tests

```
tests/test_web_e2e.py ............................ [100%]
22 passed in 18.63s
```
