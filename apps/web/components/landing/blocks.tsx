/**
 * Landing page block components.
 * Each block receives its typed slice of LandingPageModel.
 * Rendering is simple — no state, no interactivity except CTA links.
 */

import type {
  HeroBlock,
  BadgesBlock,
  PriceCard,
  Photographer,
  StyleGrid,
  SimilarCase,
  WorkBlock,
  ReviewItem,
  CtaBlock,
} from "@/types/landing";

// ── Hero ──────────────────────────────────────────────────────────────────

export function Hero({ hero }: { hero: HeroBlock }) {
  return (
    <section className="pt-10 pb-6 px-4">
      <h1 className="text-2xl font-bold leading-snug">{hero.title}</h1>
      {hero.subtitle && (
        <p className="mt-2 text-gray-500 text-sm leading-relaxed">{hero.subtitle}</p>
      )}
    </section>
  );
}

// ── Badges ────────────────────────────────────────────────────────────────

export function Badges({ badges }: { badges: BadgesBlock }) {
  if (!badges.items.length) return null;
  return (
    <section className="px-4 pb-4 flex flex-wrap gap-2">
      {badges.items.map((item, i) => (
        <span key={i} className="text-xs bg-gray-100 text-gray-600 px-3 py-1 rounded-full">
          {item}
        </span>
      ))}
    </section>
  );
}

// ── StyleGrid ─────────────────────────────────────────────────────────────

export function StyleGrid({ grid }: { grid: StyleGrid }) {
  return (
    <section className="px-4 pb-6">
      {/* Photo asset loading not implemented yet — show placeholder with set ID */}
      <div className="rounded-2xl bg-gray-100 h-52 flex items-center justify-center">
        <span className="text-xs text-gray-400">фото: {grid.photo_set_id}</span>
      </div>
    </section>
  );
}

// ── SimilarCase ───────────────────────────────────────────────────────────

export function SimilarCaseBlock({ similarCase }: { similarCase: SimilarCase }) {
  if (!similarCase.title && !similarCase.description) return null;
  return (
    <section className="mx-4 mb-6 bg-gray-50 rounded-2xl p-4">
      <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Похожий кейс</p>
      {similarCase.title && (
        <p className="text-sm font-medium">{similarCase.title}</p>
      )}
      {similarCase.description && (
        <p className="text-sm text-gray-500 mt-1">{similarCase.description}</p>
      )}
    </section>
  );
}

// ── PriceCard ─────────────────────────────────────────────────────────────

export function PriceCardBlock({ priceCard }: { priceCard: PriceCard }) {
  return (
    <section className="mx-4 mb-6 border border-gray-200 rounded-2xl p-5">
      <p className="text-2xl font-bold">{priceCard.price}</p>
      <p className="text-sm text-gray-500 mt-1">{priceCard.description}</p>
    </section>
  );
}

// ── Photographer ──────────────────────────────────────────────────────────

export function PhotographerBlock({ photographer }: { photographer: Photographer }) {
  return (
    <section className="mx-4 mb-6 flex items-center gap-3">
      <div className="w-10 h-10 rounded-full bg-gray-200 flex-shrink-0" />
      <div>
        <p className="text-sm font-medium">{photographer.name}</p>
        <p className="text-xs text-gray-400">{photographer.role}</p>
      </div>
    </section>
  );
}

// ── WorkBlock ─────────────────────────────────────────────────────────────

export function WorkBlockSection({ workBlock }: { workBlock: WorkBlock }) {
  if (!workBlock.steps.length) return null;
  return (
    <section className="mx-4 mb-6">
      <p className="text-xs text-gray-400 uppercase tracking-wide mb-3">Как проходит работа</p>
      <ol className="space-y-2">
        {workBlock.steps.map((step, i) => (
          <li key={i} className="flex gap-3 text-sm">
            <span className="w-5 h-5 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center text-xs flex-shrink-0">
              {i + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

// ── Reviews ───────────────────────────────────────────────────────────────

export function Reviews({ reviews }: { reviews: ReviewItem[] }) {
  const visible = reviews.filter((r) => r.text);
  if (!visible.length) return null;
  return (
    <section className="mx-4 mb-6 space-y-3">
      <p className="text-xs text-gray-400 uppercase tracking-wide">Отзывы</p>
      {visible.map((r, i) => (
        <div key={i} className="bg-gray-50 rounded-xl p-4">
          <p className="text-sm">{r.text}</p>
          {r.author && (
            <p className="text-xs text-gray-400 mt-2">— {r.author}</p>
          )}
        </div>
      ))}
    </section>
  );
}

// ── QuickQuestions ────────────────────────────────────────────────────────

export function QuickQuestions({ questions }: { questions: string[] }) {
  if (!questions.length) return null;
  return (
    <section className="mx-4 mb-6 space-y-2">
      <p className="text-xs text-gray-400 uppercase tracking-wide mb-3">Частые вопросы</p>
      {questions.map((q, i) => (
        <div
          key={i}
          className="border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-700"
        >
          {q}
        </div>
      ))}
    </section>
  );
}

// ── CTA ───────────────────────────────────────────────────────────────────

export function CtaButtons({ cta }: { cta: CtaBlock }) {
  return (
    <section className="mx-4 mb-10 space-y-2">
      {cta.channels.includes("telegram") && (
        <a
          href="#"
          className="flex items-center justify-center w-full bg-black text-white rounded-2xl py-4 text-sm font-medium"
        >
          Написать в Telegram
        </a>
      )}
      {cta.channels.includes("whatsapp") && (
        <a
          href="#"
          className="flex items-center justify-center w-full bg-green-500 text-white rounded-2xl py-4 text-sm font-medium"
        >
          Написать в WhatsApp
        </a>
      )}
    </section>
  );
}
