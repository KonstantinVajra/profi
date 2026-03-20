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
import { StyleGridClient } from "@/components/landing/StyleGridClient";

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

export function StyleGrid({ grid }: { grid: StyleGrid }) {
  if (!grid.photo_set_id) {
    return (
      <section className="pb-6">
        <div className="rounded-2xl bg-gray-100 h-48 flex items-center justify-center">
          <span className="text-xs text-gray-400">Примеры работ</span>
        </div>
      </section>
    );
  }
  return <StyleGridClient photoSetId={grid.photo_set_id} />;
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
      <div className="w-11 h-11 rounded-full bg-gray-200 flex-shrink-0 flex items-center justify-center">
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
            <span className="w-6 h-6 rounded-full bg-gray-900 text-white flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
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

// ── Reviews ───────────────────────────────────────────────────────────────

export function Reviews({ reviews }: { reviews: ReviewItem[] }) {
  const visible = reviews.filter((r) => r.text);
  if (!visible.length) return null;

  return (
    <section className="mb-6">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">
        Отзывы
      </p>

      <div className="space-y-3">
        {visible.map((r, i) => (
          <div
            key={i}
            className="bg-gray-50 rounded-xl p-4 border border-gray-100"
          >
            <p className="text-sm text-gray-700 leading-relaxed">{r.text}</p>

            {r.author && (
              <p className="text-xs text-gray-400 mt-2 font-medium">
                — {r.author}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

// ── QuickQuestions ────────────────────────────────────────────────────────

export function QuickQuestions({ questions }: { questions: string[] }) {
  if (!questions.length) return null;

  return (
    <section className="mb-8">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">
        Частые вопросы
      </p>

      <div className="space-y-2">
        {questions.map((q, i) => (
          <div
            key={i}
            className="flex items-center justify-between border border-gray-200 rounded-xl px-4 py-3 bg-white cursor-pointer hover:border-gray-400 transition-colors"
          >
            <span className="text-sm text-gray-800">{q}</span>
            <span className="text-gray-400 ml-2">→</span>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── PersonalBlock ─────────────────────────────────────────────────────────

export function PersonalBlockSection({ block }: { block: PersonalBlock }) {
  return (
    <section className="mb-6 bg-gray-50 rounded-2xl p-5 border border-gray-100 space-y-3">
      <p className="text-sm text-gray-800 leading-relaxed">
        {block.request_match}
      </p>
      <p className="text-sm text-gray-700 leading-relaxed">
        {block.key_feature}
      </p>
      <p className="text-sm text-gray-500 leading-relaxed italic">
        {block.trust_line}
      </p>
      <p className="text-sm font-medium text-gray-900 leading-relaxed">
        {block.hook_line}
      </p>
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
          className="flex items-center justify-center gap-2 w-full bg-gray-900 hover:bg-gray-700 text-white rounded-2xl py-4 text-sm font-semibold transition-colors"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.833.941z" />
          </svg>
          Написать в Telegram
        </a>
      )}

      {cta.channels.includes("whatsapp") && (
        <a
          href="#"
          className="flex items-center justify-center gap-2 w-full bg-green-600 hover:bg-green-700 text-white rounded-2xl py-4 text-sm font-semibold transition-colors"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
          </svg>
          Написать в WhatsApp
        </a>
      )}
    </section>
  );
}