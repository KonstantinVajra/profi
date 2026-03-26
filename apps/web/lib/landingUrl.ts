/**
 * buildLandingUrl — single source of truth for public landing page URLs.
 *
 * Source of base URL: NEXT_PUBLIC_BASE_URL env variable (set at build/deploy time).
 * Fallback: window.location.origin — only for local dev convenience, never on production.
 *
 * Trailing slash is stripped from base to prevent double-slash in output.
 *
 * Usage:
 *   buildLandingUrl("my-slug") → "https://evflow.ru/r/my-slug"
 */
export function buildLandingUrl(slug: string): string {
  const raw =
    process.env.NEXT_PUBLIC_BASE_URL ??
    (typeof window !== "undefined" ? window.location.origin : "http://localhost:3000");
  const base = raw.replace(/\/+$/, ""); // strip trailing slash(es)
  return `${base}/r/${slug}`;
}