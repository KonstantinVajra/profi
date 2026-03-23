/**
 * Smoke tests — workspace extraction decision logic.
 *
 * Tests the production helpers from extractionUtils.ts directly.
 * No React rendering, no mocks — pure function calls.
 *
 * Covers:
 *   selectExtractionMethod:
 *     1. text flow selected when text is present
 *     2. image flow selected when only screenshot is present
 *     3. text has priority when both text and file are present
 *     4. null returned when neither text nor file is present
 *
 *   validateScreenshotFile:
 *     5. non-image file returns an error string
 *     6. image file returns null (no error)
 *
 * Run with: npx jest __tests__/workspace-extraction.test.ts
 * Or:       npx vitest __tests__/workspace-extraction.test.ts
 */

import {
  selectExtractionMethod,
  validateScreenshotFile,
} from "../lib/extractionUtils";

// ── Test helper ───────────────────────────────────────────────────────────

function makeFile(name: string, type: string): File {
  return new File([new Uint8Array([0x89, 0x50])], name, { type });
}

// ── selectExtractionMethod ────────────────────────────────────────────────

describe("selectExtractionMethod", () => {
  it("returns 'text' when orderText is present (no file)", () => {
    const result = selectExtractionMethod("Нужен фотограф на свадьбу", null);
    expect(result).toBe("text");
  });

  it("returns 'image' when orderText is empty and screenshotFile is present", () => {
    const file = makeFile("order.png", "image/png");
    const result = selectExtractionMethod("", file);
    expect(result).toBe("image");
  });

  it("returns 'text' when both text and file are present (text has priority)", () => {
    const file = makeFile("order.jpg", "image/jpeg");
    const result = selectExtractionMethod("Нужен фотограф на регистрацию", file);
    expect(result).toBe("text");
  });

  it("returns null when neither text nor file is present", () => {
    const result = selectExtractionMethod("", null);
    expect(result).toBeNull();
  });

  it("returns null when text is only whitespace and no file", () => {
    const result = selectExtractionMethod("   ", null);
    expect(result).toBeNull();
  });
});

// ── validateScreenshotFile ────────────────────────────────────────────────

describe("validateScreenshotFile", () => {
  it("returns an error string for non-image file", () => {
    const pdf = makeFile("document.pdf", "application/pdf");
    const result = validateScreenshotFile(pdf);
    expect(result).toBe("Можно загрузить только изображение");
  });

  it("returns null for a valid jpeg image", () => {
    const jpeg = makeFile("order.jpg", "image/jpeg");
    const result = validateScreenshotFile(jpeg);
    expect(result).toBeNull();
  });

  it("returns null for a valid png image", () => {
    const png = makeFile("order.png", "image/png");
    const result = validateScreenshotFile(png);
    expect(result).toBeNull();
  });
});
