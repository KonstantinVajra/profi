"use client";

const SHARE_SVG = "M13 9V3H11v6H7l5 5 5-5h-4zm-8 9h14v-2H5v2z";

// Simple upload/share arrow — unambiguous "share" metaphor,
// does not conflict with channel icons in the same CTA row.
const SHARE_ICON_SVG = "M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8M16 6l-4-4-4 4M12 2v13";

async function handleShare() {
  try {
    if (typeof navigator !== "undefined" && navigator.share) {
      await navigator.share({ title: document.title, url: window.location.href });
    } else {
      await navigator.clipboard.writeText(window.location.href);
      alert("Ссылка скопирована");
    }
  } catch (err) {
    // AbortError — user dismissed native share dialog; ignore silently.
    if (err instanceof Error && err.name !== "AbortError") {
      await navigator.clipboard.writeText(window.location.href);
      alert("Ссылка скопирована");
    }
  }
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