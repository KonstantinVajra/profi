/**
 * extractionUtils.ts
 *
 * Pure decision helpers for order extraction in workspace.
 * Extracted from workspace/page.tsx to be independently testable.
 *
 * No React, no side effects, no API calls — only decisions.
 */

/**
 * Determines which extraction API to use based on available input.
 *
 * Rules:
 *   - "text"  — orderText is present and non-empty (takes priority over screenshot)
 *   - "image" — no text, but screenshotFile is present
 *   - null    — no input at all; caller should not proceed
 *
 * @param orderText     - current value of the order textarea
 * @param screenshotFile - currently selected screenshot file, or null
 */
export function selectExtractionMethod(
  orderText: string,
  screenshotFile: File | null,
): "text" | "image" | null {
  if (orderText.trim()) return "text";
  if (screenshotFile) return "image";
  return null;
}

/**
 * Validates a file selected for screenshot order extraction.
 *
 * Returns null if the file is valid (i.e. is an image).
 * Returns a user-facing error string if invalid.
 *
 * @param file - File object from the file input onChange event
 */
export function validateScreenshotFile(file: File): string | null {
  if (!file.type.startsWith("image/")) {
    return "Можно загрузить только изображение";
  }
  return null;
}
