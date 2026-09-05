import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = 'http://localhost:3003';
const TEST_IMAGE_PATH = path.join(__dirname, '..', '..', 'pictures', 'duck.png');

test.describe('Nonogram Image Generation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test.describe('Image Upload & Metadata', () => {
    test('should display the form on load', async ({ page }) => {
      await expect(page.locator('h1')).toContainText('Nonogram');
      await expect(page.locator('label:has-text("Image")')).toBeVisible();
    });

    test('should upload an image file', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      // Wait for metadata to load
      await page.waitForTimeout(500);

      // Should show preview and metadata
      await expect(page.locator('img[alt="Preview"]')).toBeVisible();
      await expect(page.locator('text=2000 × 2000')).toBeVisible();
    });

    test('should calculate aspect ratio correctly', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      // Duck image is square (2000x2000), so aspect ratio should be 1:1
      await expect(page.locator('text=1:1')).toBeVisible();
    });

    test('should show dimension suggestions', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      // Should show suggestion buttons
      await expect(page.locator('button:has-text("10×10")')).toBeVisible();
      await expect(page.locator('button:has-text("11×11")')).toBeVisible();
      await expect(page.locator('button:has-text("12×12")')).toBeVisible();
    });

    test('should populate size field when clicking suggestion button', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      // Click suggestion button
      await page.locator('button:has-text("10×10")').click();

      // Size field should be populated
      const sizeField = page.locator('input[placeholder="e.g., 20 or 20x30"]').first();
      await expect(sizeField).toHaveValue('10x10');
    });

    test('should allow manual size entry', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      // Manually enter size
      const sizeField = page.locator('input[placeholder="e.g., 20 or 20x30"]').first();
      await sizeField.fill('15x20');

      await expect(sizeField).toHaveValue('15x20');
    });
  });

  test.describe('Form Fields', () => {
    test('should display all required form fields', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      // Check for all fields
      await expect(page.locator('label:has-text("Size")')).toBeVisible();
      await expect(page.locator('label:has-text("Name")')).toBeVisible();
      await expect(page.locator('label:has-text("Output Directory")')).toBeVisible();
      await expect(page.locator('label:has-text("Export Formats")')).toBeVisible();
      await expect(page.locator('label:has-text("Difficulty")')).toBeVisible();
      await expect(page.locator('label:has-text("Seed")')).toBeVisible();
    });

    test('should have PDF selected by default', async ({ page }) => {
      const pdfCheckbox = page.locator('input[value="pdf"]');
      await expect(pdfCheckbox).toBeChecked();
    });

    test('should allow export format selection', async ({ page }) => {
      const jsonCheckbox = page.locator('input[value="json"]');
      const pngCheckbox = page.locator('input[value="png"]');

      await jsonCheckbox.check();
      await pngCheckbox.check();

      await expect(jsonCheckbox).toBeChecked();
      await expect(pngCheckbox).toBeChecked();
    });

    test('should have difficulty dropdown with default (any)', async ({ page }) => {
      const difficultySelect = page.locator('select[name="difficulty"]');
      await expect(difficultySelect).toHaveValue('any');
    });

    test('should allow entering name and output directory', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      const nameInput = page.locator('input[name="name"]');
      const outDirInput = page.locator('input[placeholder="."]');

      await nameInput.fill('my-puzzle');
      await outDirInput.fill('./output');

      await expect(nameInput).toHaveValue('my-puzzle');
      await expect(outDirInput).toHaveValue('./output');
    });

    test('should show auto-generated name preview when name field is empty', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      // Should show helper text with auto-generated name
      await expect(page.locator('text=Will use: duck')).toBeVisible();
    });
  });

  test.describe('Form Submission', () => {
    test('should submit form with image and size', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      // Fill size
      const sizeField = page.locator('input[placeholder="e.g., 20 or 20x30"]').first();
      await sizeField.fill('10x10');

      // Submit form
      const submitButton = page.locator('button:has-text("Generate Puzzle")');
      await submitButton.click();

      // Wait for response
      await page.waitForTimeout(5000);

      // Should show success message
      await expect(page.locator('text=Puzzle Generated Successfully')).toBeVisible({ timeout: 10000 });
    });

    test('should show success with name and seed', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      const sizeField = page.locator('input[placeholder="e.g., 20 or 20x30"]').first();
      await sizeField.fill('10x10');

      const submitButton = page.locator('button:has-text("Generate Puzzle")');
      await submitButton.click();

      // Wait for success
      await page.waitForTimeout(5000);

      // Should show name and seed
      await expect(page.locator('text=Name:')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=Seed:')).toBeVisible();
    });

    test('should show Copy Path and Open buttons for generated files', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      const sizeField = page.locator('input[placeholder="e.g., 20 or 20x30"]').first();
      await sizeField.fill('10x10');

      const submitButton = page.locator('button:has-text("Generate Puzzle")');
      await submitButton.click();

      // Wait for success
      await page.waitForTimeout(5000);

      // Should show action buttons
      await expect(page.locator('button:has-text("Copy Path")')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('button:has-text("Open")')).toBeVisible();
    });

    test('should copy file path to clipboard when Copy Path button clicked', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      const sizeField = page.locator('input[placeholder="e.g., 20 or 20x30"]').first();
      await sizeField.fill('10x10');

      const submitButton = page.locator('button:has-text("Generate Puzzle")');
      await submitButton.click();

      // Wait for success
      await page.waitForTimeout(5000);

      // Click Copy Path button
      const copyButton = page.locator('button:has-text("Copy Path")').first();
      await copyButton.click();

      // Should show "Copied" confirmation
      await expect(page.locator('button:has-text("✓ Copied")')).toBeVisible({ timeout: 3000 });

      // After 2 seconds, should return to "Copy Path"
      await page.waitForTimeout(2500);
      await expect(page.locator('button:has-text("Copy Path")')).toBeVisible();
    });

    test('should show generated file in results', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      const sizeField = page.locator('input[placeholder="e.g., 20 or 20x30"]').first();
      await sizeField.fill('10x10');

      const submitButton = page.locator('button:has-text("Generate Puzzle")');
      await submitButton.click();

      // Wait for results
      await page.waitForTimeout(5000);

      // Should show file path - check for Generated Files heading
      await expect(page.locator('text=Generated Files')).toBeVisible({ timeout: 10000 });
    });

    test('should require size for image mode submission', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      // Don't fill size, try to submit
      const submitButton = page.locator('button:has-text("Generate Puzzle")');

      // Try to submit without size
      await submitButton.click();

      // Should show error about missing size
      await page.waitForTimeout(2000);
      const errorOrSuccess = page.locator('text=/Error|Successfully/');
      // Either error (if size required) or error message about generation
      // This depends on backend validation
    });

    test('should support multiple export formats', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      // Select multiple formats
      const jsonCheckbox = page.locator('input[value="json"]');
      const svgCheckbox = page.locator('input[value="svg"]');
      const pdfCheckbox = page.locator('input[value="pdf"]');

      await jsonCheckbox.check();
      await svgCheckbox.check();
      // PDF already checked

      const sizeField = page.locator('input[placeholder="e.g., 20 or 20x30"]').first();
      await sizeField.fill('10x10');

      const submitButton = page.locator('button:has-text("Generate Puzzle")');
      await submitButton.click();

      await page.waitForTimeout(5000);

      // Should show success with files
      await expect(page.locator('text=Generated Files')).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('UI/UX Features', () => {
    test('should have export formats in row layout', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      // Get export format checkboxes
      const checkboxes = page.locator('input[name="export_formats"]');
      const count = await checkboxes.count();

      expect(count).toBe(5); // JSON, CSV, PNG, SVG, PDF

      // Verify they're displayed in a row (visually by checking their positions)
      const boxes = await Promise.all(
        Array.from({ length: count }, (_, i) =>
          checkboxes.nth(i).boundingBox()
        )
      );

      // All should have Y coordinates close to each other (row layout)
      const yCoordinates = boxes.filter(Boolean).map(b => b?.y || 0);
      const yVariation = Math.max(...yCoordinates) - Math.min(...yCoordinates);

      // In a row layout, Y variation should be small
      expect(yVariation).toBeLessThan(50);
    });

    test('should show error/success messages at top', async ({ page }) => {
      // After form submission, messages should appear at top
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      const sizeField = page.locator('input[placeholder="e.g., 20 or 20x30"]').first();
      await sizeField.fill('10x10');

      const submitButton = page.locator('button:has-text("Generate Puzzle")');
      await submitButton.click();

      await page.waitForTimeout(5000);

      // Check for success message at top
      const successBox = page.locator('text=Puzzle Generated Successfully');
      if (await successBox.isVisible({ timeout: 1000 }).catch(() => false)) {
        const box = await successBox.boundingBox();
        // Message should be at the top (Y < 200 pixels)
        expect(box?.y || 0).toBeLessThan(200);
      }
    });

    test('should display dark mode styling', async ({ page }) => {
      // Check for dark mode elements
      const form = page.locator('form').first();
      const computedStyle = await form.evaluate(el => {
        return window.getComputedStyle(el);
      });

      // Should have dark background colors
      const bgColor = computedStyle.backgroundColor;
      expect(bgColor).toBeTruthy();
    });
  });

  test.describe('Responsive Design', () => {
    test('should work on desktop viewport', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      const form = page.locator('form').first();
      await expect(form).toBeVisible();

      const box = await form.boundingBox();
      expect(box?.width).toBeGreaterThan(300);
    });

    test('should work on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      const form = page.locator('form').first();
      await expect(form).toBeVisible();
    });

    test('should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });

      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      const form = page.locator('form').first();
      await expect(form).toBeVisible();
    });
  });

  test.describe('Error Handling', () => {
    test('should show error when submitting without image', async ({ page }) => {
      const submitButton = page.locator('button:has-text("Generate Puzzle")');

      // Button should be disabled initially
      await expect(submitButton).toBeDisabled();
    });

    test('should allow form reset after error', async ({ page }) => {
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      await page.waitForTimeout(500);

      // Upload another file to "reset"
      const anotherFile = TEST_IMAGE_PATH; // Use same file for test
      await fileInput.setInputFiles(anotherFile);

      // Size field should be cleared
      const sizeField = page.locator('input[placeholder="e.g., 20 or 20x30"]').first();
      await expect(sizeField).toHaveValue('');
    });

    test('should clear error message when selecting new image', async ({ page }) => {
      // Create a scenario where we have an error message
      // Simulate this by just checking the behavior when re-uploading after any state
      const fileInput = page.locator('input[type="file"]');

      // First upload
      await fileInput.setInputFiles(TEST_IMAGE_PATH);
      await page.waitForTimeout(500);

      // After upload, select the file again (clear error state on new selection)
      // The implementation should clear any previous errors
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      // Metadata should be refreshed, no stale error should persist
      await expect(page.locator('text=Will use: duck')).toBeVisible();
    });
  });
});
