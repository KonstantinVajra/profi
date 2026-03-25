"use client";

// Simple upload/share arrow — unambiguous "share" metaphor,
// does not conflict with channel icons in the same CTA row.
const SHARE_ICON_SVG = "M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8M16 6l-4-4-4 4M12 2v13";

async function handleShare() {
  const url = window.location.href;

  // 1. Native share — best experience on mobile and modern desktop.
  if (typeof navigator !== "undefined" && navigator.share) {
    try {
      await navigator.share({ title: document.title, url });
      return; // success — nothing else needed
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        // User dismissed the native share sheet — not an error, do nothing.
        return;
      }
      // share threw something else — fall through to clipboard
    }
  }

  // 2. Clipboard — works on HTTPS and localhost.
  try {
    await navigator.clipboard.writeText(url);
    alert("Ссылка скопирована");
    return;
  } catch {
    // clipboard unavailable (HTTP, permissions denied) — fall through to prompt
  }

  // 3. Final fallback — always works, lets the user copy manually.
  window.prompt("Скопируйте ссылку:", url);
}

export function SharePageButton() {
  return (
    <button
      type="button"
      onClick={handleShare}
      className="flex items-center justify-center gap-2 w-full rounded-xl py-3.5 text-sm font-semibold transition-colors bg-stone-100 border border-stone-200 text-gray-900 hover:bg-stone-200"
    >
      <svg
        className="w-5 h-5 text-rose-400"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d={SHARE_ICON_SVG} />
      </svg>
      Поделиться страницей
    </button>
  );
}