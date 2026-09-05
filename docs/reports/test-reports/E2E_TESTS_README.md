# End-to-End Tests for Web UI

This document describes the end-to-end (e2e) tests for the nonogram web UI, implemented using Playwright browser automation.

## Overview

The e2e tests validate the complete user experience of the web interface by driving a real browser (Chromium) against a running web server. They test the full flow from form interaction to puzzle generation and file output.

## Test Coverage

### Test Classes and Scenarios

1. **TestWebE2E_FormPageLoads** (3 tests)
   - Form page loads with title and elements
   - All required form fields are present
   - Export format options are available

2. **TestWebE2E_ImageModeWithSampleImage** (2 tests)
   - Image upload and puzzle generation with JSON export
   - Image upload with custom puzzle name

3. **TestWebE2E_ImageSizeAndSettings** (2 tests)
   - Custom size specification
   - Seed parameter for reproducibility

4. **TestWebE2E_ErrorHandling** (3 tests)
   - Behavior with no image submitted
   - Invalid output directory handling
   - Invalid size input validation

5. **TestWebE2E_FormRepopulation** (2 tests)
   - Form values preserved on success (AC-122)
   - Form values preserved on error for retry (AC-123)

6. **TestWebE2E_ExportOptions** (2 tests)
   - No export format selected
   - Multiple export formats selection

7. **TestWebE2E_SizeInputVariations** (2 tests)
   - Bare number size input (e.g., "16")
   - Rectangular size input (e.g., "20x24")

8. **TestWebE2E_DifficultySelection** (2 tests)
   - Difficulty selector availability
   - Image generation with difficulty selection

9. **TestWebE2E_FileVerification** (2 tests)
   - Generated JSON has valid structure with clues and metadata
   - Generated PNG file exists and has valid PNG magic bytes

## Running the Tests

### Prerequisites

```bash
pip install -e '.[dev]'
playwright install chromium
```

### Run All E2E Tests

```bash
pytest tests/test_web_e2e.py -v
```

### Run Specific Test

```bash
pytest tests/test_web_e2e.py::TestWebE2E_ImageModeWithSampleImage::test_image_upload_and_generation -v
```

### Run with Custom Timeout

```bash
pytest tests/test_web_e2e.py -v --timeout=60
```

## Test Architecture

### Fixtures

- **running_web_server**: Starts the web server on a free port in a background thread
- **sample_image_path**: Creates a simple 16x16 test image with PIL
- **page**: Provided by pytest-playwright for browser interaction

### Key Features

- **Image Mode Focus**: Tests focus on image mode since that's the current web UI implementation
- **Required Fields**: Size field must be provided for image mode to work
- **File Verification**: Tests verify both success/failure messages and actual file generation
- **Error Handling**: Tests cover various error scenarios with proper error message display

## Implementation Notes

1. **Size Field**: The size field is required for image mode. Bare numbers (e.g., "16") specify the longer dimension, while "WxH" format (e.g., "20x24") specifies exact dimensions.

2. **Form Re-population**: After submission, the form is re-rendered with submitted values preserved inline, with a collapsible result section showing success or error (AC-122/AC-123).

3. **Error Display**: Errors are displayed as inline failure sections on the form page, not as separate pages.

4. **File Names**: Generated files use the image filename as the base (e.g., "test" from "test.png" generates "test.json", "test.png", etc.).

## Comparison with Existing Tests

### Existing Tests (test_web_submission.py, etc.)
- Use loopback HTTP servers with direct API calls
- Test backend submission handling and validation
- Support multiple modes (library, random, image)

### E2E Tests (test_web_e2e.py)
- Use real browser automation
- Test the actual UI experience and rendering
- Focus on image mode (current web UI implementation)
- Verify visual feedback and user workflows

Both test types are complementary:
- Unit/integration tests verify the API contract
- E2E tests verify the user experience

## CI/CD Integration

To integrate into CI/CD:

```yaml
- name: Run E2E Tests
  run: |
    pip install -e '.[dev]'
    playwright install chromium
    pytest tests/test_web_e2e.py -v
```

## Known Limitations

1. **Browser**: Tests run on Chromium only (other browsers can be added)
2. **Headless**: Tests run in headless mode by default
3. **Mode**: Tests focus on image mode, which is the current web UI implementation
4. **Timeout**: Some tests have a 15-second timeout for generation; slower systems may need adjustment

## Future Enhancements

1. Add Firefox and WebKit browser support
2. Add visual regression testing
3. Add performance benchmarks
4. Add multi-browser parallel execution
5. Add screenshot captures on failure
6. Expand to test other modes if web UI is updated to support them
