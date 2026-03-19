/**
 * Landing page block components.
 * Each block receives its typed slice of LandingPageModel.
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
  PersonalBlock,
} from "@/types/landing";

// ── Hero ──────────────────────────────────────────────────────────────────

export function Hero({ hero }: { hero: HeroBlock }) {
  return (
    <section className="pt-10 pb-5">
      <h1 className="text-2xl font-bold leading-tight tracking-tight text-gray-900">
        {hero.title}
      </h1>
      {hero.subtitle && (
        <p className="mt-3 text-base text-gray-600 leading-relaxed">
          {hero.subtitle}
        </p>
      )}
    </section>
  );
}

// ── Badges ────────────────────────────────────────────────────────────────

export function Badges({ badges }: { badges: BadgesBlock }) {
  if (!badges.items.length) return null;

  return (
    <section className="pb-5 flex flex-wrap gap-2">
      {badges.items.map((item, i) => (
        <span
          key={i}
          className="text-xs bg-gray-100 text-gray-700 px-3 py-1.5 rounded-full font-medium"
        >
          {item}
        </span>
      ))}
    </section>
  );
}

// ── StyleGrid ─────────────────────────────────────────────────────────────

export function StyleGrid({ grid: _ }: { grid: StyleGrid }) {
  return (
    <section className="pb-6">
      <div className="rounded-2xl bg-gray-100 h-48 flex flex-col items-center justify-center gap-2">
        <span className="text-xs text-gray-400">Примеры работ</span>
      </div>
    </section>
  );
}

// ── SimilarCase ───────────────────────────────────────────────────────────

export function SimilarCaseBlock({
  similarCase,
}: {
  similarCase: SimilarCase;
}) {
  if (!similarCase.title && !similarCase.description) return null;

  return (
    <section className="mb-6 bg-gray-50 rounded-2xl p-4 border border-gray-100">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Похожий кейс
      </p>

      {similarCase.title && (
        <p className="text-sm font-semibold text-gray-800">
          {similarCase.title}
        </p>
      )}

      {similarCase.description && (
        <p className="text-sm text-gray-500 mt-1 leading-relaxed">
          {similarCase.description}
        </p>
      )}
    </section>
  );
}

// ── PriceCard ─────────────────────────────────────────────────────────────

export function PriceCardBlock({ priceCard }: { priceCard: PriceCard }) {
  return (
    <section className="mb-6 border border-gray-200 rounded-2xl p-5 bg-white">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Стоимость
      </p>
      <p className="text-3xl font-bold text-gray-900 leading-none">
        {priceCard.price}
      </p>
      <p className="text-sm text-gray-500 mt-2 leading-relaxed">
        {priceCard.description}
      </p>
    </section>
  );
}

// ── Photographer ──────────────────────────────────────────────────────────

export function PhotographerBlock({
  photographer,
}: {
  photographer: Photographer;
}) {
  return (
    <section className="mb-6 flex items-center gap-3 py-4 border-t border-b border-gray-100">
      <div className="w-11 h-11 rounded-full bg-gray-200 flex items-center justify-center">
        <span className="text-lg font-semibold text-gray-500">
          {photographer.name.charAt(0)}
        </span>
      </div>

      <div>
        <p className="text-sm font-semibold text-gray-900">
          {photographer.name}
        </p>
        <p className="text-xs text-gray-500 mt-0.5">{photographer.role}</p>
      </div>
    </section>
  );
}

// ── WorkBlock ─────────────────────────────────────────────────────────────

export function WorkBlockSection({ workBlock }: { workBlock: WorkBlock }) {
  const visibleSteps = workBlock.steps.filter((s) => s.trim());
  if (!visibleSteps.length) return null;

  return (
    <section className="mb-6">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">
        Как проходит работа
      </p>

      <ol className="space-y-3">
        {visibleSteps.map((step, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className="w-6 h-6 rounded-full bg-gray-900 text-white flex items-center justify-center text-xs font-bold">
              {i + 1}
            </span>
            <span className="text-sm text-gray-700 leading-relaxed">
              {step}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

// ── CTA ───────────────────────────────────────────────────────────────────

export function CtaButtons({ cta }: { cta: CtaBlock }) {
  return (
    <section className="pt-2 space-y-3">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider text-center mb-4">
        Напишите мне
      </p>

      {cta.channels.includes("telegram") && (
        <a
          href="#"
          className="flex items-center justify-center w-full bg-gray-900 hover:bg-gray-700 text-white rounded-2xl py-4 text-sm font-semibold"
        >
          Написать в Telegram
        </a>
      )}

      {cta.channels.includes("whatsapp") && (
        <a
          href="#"
          className="flex items-center justify-center w-full bg-green-600 hover:bg-green-700 text-white rounded-2xl py-4 text-sm font-semibold"
        >
          Написать в WhatsApp
        </a>
      )}
    </section>
  );
}