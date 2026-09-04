/**
 * Client-side image metadata calculation and dimension suggestions (CARD-034).
 *
 * This module provides real-time calculation of image dimensions and puzzle
 * dimension suggestions when a user selects an image file. The algorithm
 * matches the server-side implementation exactly (AC-137).
 *
 * AC-135: Metadata and suggestions appear instantly when file selected
 * AC-136: Clicking suggestion populates size field, file input retains selection
 * AC-137: Client-side calculations match server-side exactly
 * AC-138: Graceful fallback if File API unavailable
 */

(function() {
  "use strict";

  /**
   * Calculate the greatest common divisor of two numbers.
   * Used to simplify aspect ratios.
   */
  function gcd(a, b) {
    return b === 0 ? a : gcd(b, a % b);
  }

  /**
   * Simplify a ratio to its lowest terms.
   * Returns [simplified_width, simplified_height].
   */
  function simplifyRatio(width, height) {
    const divisor = gcd(width, height);
    return [width / divisor, height / divisor];
  }

  /**
   * Format an aspect ratio for display.
   * Returns a string like "4:3 (1.33)".
   */
  function formatAspectRatio(width, height, decimal) {
    return `${width}:${height} (${decimal})`;
  }

  /**
   * Extract metadata from an image file.
   * Returns a Promise that resolves with {width, height, aspectRatio, decimal}
   * or rejects if the image cannot be read.
   *
   * AC-135: Instant metadata calculation when file is selected
   */
  function extractImageMetadata(file) {
    return new Promise((resolve, reject) => {
      // Create a FileReader to read the image
      const reader = new FileReader();

      reader.onload = function(e) {
        // Create an Image object to get dimensions
        const img = new Image();

        img.onload = function() {
          const [simplifiedW, simplifiedH] = simplifyRatio(img.width, img.height);
          const decimal = Math.round((img.width / img.height) * 100) / 100;

          resolve({
            width: img.width,
            height: img.height,
            aspectRatio: {
              width: simplifiedW,
              height: simplifiedH,
              decimal: decimal
            }
          });
        };

        img.onerror = function() {
          reject(new Error("Could not read image dimensions"));
        };

        // Set the image source to trigger loading
        img.src = e.target.result;
      };

      reader.onerror = function() {
        reject(new Error("Could not read file"));
      };

      // Read the file as a data URL
      reader.readAsDataURL(file);
    });
  }

  /**
   * Generate 2-3 suggested puzzle dimensions based on image aspect ratio.
   * Matches the server-side algorithm in metadata.py exactly (AC-137).
   *
   * Returns a list of [width, height] pairs, ordered by how closely they
   * match the aspect ratio. All dimensions are within [minSize, maxSize].
   */
  function suggestDimensions(metadata, minSize = 10, maxSize = 30) {
    const aspectW = metadata.aspectRatio.width;
    const aspectH = metadata.aspectRatio.height;
    const targetRatio = aspectW / aspectH;

    const suggestions = [];

    // Try all combinations within the constraint
    for (let w = minSize; w <= maxSize; w++) {
      for (let h = minSize; h <= maxSize; h++) {
        const gridRatio = w / h;
        // Calculate how close this dimension is to the target aspect ratio
        const ratioError = Math.abs(gridRatio - targetRatio) / targetRatio;
        suggestions.push([ratioError, [w, h]]);
      }
    }

    // Sort by ratio error (closest first)
    suggestions.sort((a, b) => a[0] - b[0]);

    // Return top 2-3 suggestions
    const resultCount = Math.min(3, suggestions.length);
    return suggestions.slice(0, resultCount).map(item => item[1]);
  }

  /**
   * Update the form with metadata and suggestions.
   * AC-135: Display metadata and suggestions in real time
   * AC-136: Clicking suggestion buttons populates the size field
   * AC-158, AC-159: Display image preview with dimensions
   */
  function updateFormWithMetadata(metadata, suggestions) {
    // Format the aspect ratio for display
    const aspectRatioStr = formatAspectRatio(
      metadata.aspectRatio.width,
      metadata.aspectRatio.height,
      metadata.aspectRatio.decimal
    );

    // Display image preview (AC-158, AC-159, AC-160)
    displayImagePreview(metadata);

    // Create metadata section HTML
    const metadataHtml = `
      <div class="metadata">
        <p><strong>Image aspect ratio:</strong> ${escapeHtml(aspectRatioStr)}</p>
      </div>
    `;

    // Create suggestions section HTML
    let suggestionsHtml = "";
    if (suggestions && suggestions.length > 0) {
      const buttons = suggestions
        .map(([w, h]) => {
          const sizeStr = `${w}x${h}`;
          return `
            <button type="button" class="suggestion-button" data-size="${escapeHtml(sizeStr)}">${escapeHtml(sizeStr)}</button>
          `;
        })
        .join("");

      suggestionsHtml = `
        <div class="suggestions">
          <p><small><strong>Suggested dimensions (click to set):</strong></small></p>
          ${buttons}
        </div>
      `;
    }

    // Find the metadata-suggestions-area container
    const container = document.getElementById("metadata-suggestions-area");
    if (container) {
      container.innerHTML = metadataHtml + suggestionsHtml;

      // Attach click handlers to suggestion buttons
      const buttons = container.querySelectorAll(".suggestion-button");
      buttons.forEach(function(button) {
        button.addEventListener("click", function(e) {
          e.preventDefault();
          const sizeStr = this.getAttribute("data-size");
          const sizeInput = document.querySelector('input[name="size"]');
          if (sizeInput) {
            sizeInput.value = sizeStr;
          }
          return false;
        });
      });
    }
  }

  /**
   * Display the image preview thumbnail (AC-158, AC-159, AC-160).
   * Shows a thumbnail (max 150×150 px) with original dimensions label.
   */
  function displayImagePreview(metadata) {
    const previewContainer = document.getElementById("image-preview-container");
    const previewImg = document.getElementById("image-preview");
    const dimensionsDiv = document.getElementById("image-dimensions");

    if (!previewContainer || !previewImg || !dimensionsDiv) {
      return;
    }

    // Use FileReader to get the data URL for preview
    const fileInput = document.querySelector('input[type="file"][name="image"]');
    if (!fileInput || fileInput.files.length === 0) {
      return;
    }

    const file = fileInput.files[0];
    const reader = new FileReader();

    reader.onload = function(e) {
      previewImg.src = e.target.result;
      dimensionsDiv.textContent = `${metadata.width} × ${metadata.height}`;
      previewContainer.classList.add("visible");
    };

    reader.onerror = function() {
      previewContainer.classList.remove("visible");
    };

    reader.readAsDataURL(file);
  }

  /**
   * Simple HTML escape function to prevent XSS.
   * AC-138: Graceful handling - only escape user data
   */
  function escapeHtml(text) {
    if (typeof text !== "string") {
      return "";
    }
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Clear metadata and suggestions from the form.
   */
  function clearMetadata() {
    const container = document.getElementById("metadata-suggestions-area");
    if (container) {
      container.innerHTML = "";
    }

    // Clear preview (AC-160: update when new file selected)
    const previewContainer = document.getElementById("image-preview-container");
    if (previewContainer) {
      previewContainer.classList.remove("visible");
    }
  }

  /**
   * Clear the size field (AC-149: clear size when new image selected).
   * Prevents stale size from previous image being used with new image.
   */
  function clearSizeField() {
    const sizeInput = document.querySelector('input[name="size"]');
    if (sizeInput) {
      sizeInput.value = "";
    }
  }

  /**
   * Initialize the file input listener.
   * AC-135: Set up handler for file selection
   * AC-138: Graceful fallback if File API unavailable
   */
  function initializeFileInputListener() {
    try {
      const fileInput = document.querySelector('input[type="file"][name="image"]');

      if (!fileInput) {
        // File input not found - graceful fallback (AC-138)
        console.log("Image file input not found - metadata calculation unavailable");
        return;
      }

      // Check if File API is available (AC-138)
      if (!window.FileReader || !window.Image) {
        console.log("File API not available - metadata calculation unavailable");
        fileInput.addEventListener("change", function() {
          clearMetadata();
        });
        return;
      }

      // AC-135: Handle file selection and calculate metadata
      fileInput.addEventListener("change", function() {
        try {
          if (this.files.length === 0) {
            clearMetadata();
            clearSizeField(); // AC-149: Clear size field when no image selected
            return;
          }

          const file = this.files[0];

          // Verify it's an image file
          if (!file.type.startsWith("image/")) {
            clearMetadata();
            clearSizeField(); // AC-149: Clear size field for invalid image
            return;
          }

          // AC-149: Clear size field when new image selected (prevents stale size)
          clearSizeField();

          // AC-135: Extract metadata asynchronously
          extractImageMetadata(file)
            .then(function(metadata) {
              // AC-135: Calculate suggestions
              const suggestions = suggestDimensions(metadata);

              // AC-135: Update form with results
              updateFormWithMetadata(metadata, suggestions);
            })
            .catch(function(error) {
              // AC-138: Graceful error handling - clear metadata on error
              console.log("Could not extract image metadata:", error.message);
              clearMetadata();
            });
        } catch (err) {
          // AC-138: Graceful error handling
          console.log("Error processing file change:", err.message);
          clearMetadata();
          clearSizeField(); // AC-149: Clear size on error
        }
      });
    } catch (err) {
      // AC-138: Graceful fallback if initialization fails
      console.log("Could not initialize metadata listener:", err.message);
    }
  }

  // Initialize when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeFileInputListener);
  } else {
    // DOM already loaded
    initializeFileInputListener();
  }
})();
