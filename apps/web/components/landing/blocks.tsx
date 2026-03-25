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
import type { ContactInfo } from "@/lib/api";

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
      <section className="px-6 pb-5">
        <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-[0.08em] mb-3">
          Примеры работ
        </p>
        <div className="rounded-xl bg-gray-100 h-48 flex items-center justify-center">
          <span className="text-xs text-gray-400">—</span>
        </div>
      </section>
    );
  }
  // Label above photo grid. StyleGridClient thumbnails go edge-to-edge via overflow-hidden.
  return (
    <section>
      <p className="px-6 pt-1 pb-3 text-[11px] font-semibold text-gray-400 uppercase tracking-[0.08em]">
        Примеры похожей съёмки
      </p>
      <StyleGridClient photoSetId={grid.photo_set_id} />
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

// ── OrderHeader ───────────────────────────────────────────────────────────
// Compact contextual header for MVP mode.
// Data sources: only template_key and price_card.price — no hero fields.
//
//   title    → derived from template_key via TEMPLATE_TITLE map (never hero.title)
//   subtitle → fixed neutral string (never hero.subtitle)
//   chips    → template_key human label + price_card.price if present
//
// hero.title / hero.subtitle are legacy structural fields and must not appear
// in MVP mode to avoid duplicating or conflicting with final_text content.

const TEMPLATE_TITLE: Record<string, string> = {
  registry_small: "Регистрация",
  wedding_full:   "Свадебная съёмка",
  family_session: "Семейная съёмка",
  event_general:  "Съёмка мероприятия",
};

const TEMPLATE_CHIP: Record<string, string> = {
  registry_small: "Регистрация",
  wedding_full:   "Свадьба",
  family_session: "Семейная съёмка",
  event_general:  "Мероприятие",
};

interface OrderHeaderProps {
  templateKey: string;
  price?: string | null;
}

export function OrderHeader({ templateKey, price }: OrderHeaderProps) {
  const title =
    TEMPLATE_TITLE[templateKey] ?? "Персональный отклик";

  // Chips: event type label + price if present. Only non-empty values rendered.
  const chips: string[] = [];
  const chipLabel = TEMPLATE_CHIP[templateKey];
  if (chipLabel) chips.push(chipLabel);
  if (price?.trim()) chips.push(price.trim());

  return (
    <header className="px-6 pt-7 pb-5 border-b border-gray-100">
      <h1 className="text-[17px] font-semibold leading-snug tracking-tight text-gray-900">
        {title}
      </h1>
      <p className="mt-1 text-[13px] text-gray-400 leading-relaxed">
        Персональный отклик по вашему запросу
      </p>
      {chips.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {chips.map((chip, i) => (
            <span
              key={i}
              className="text-[11px] bg-stone-100 text-stone-500 px-2.5 py-1 rounded-full font-medium tracking-wide"
            >
              {chip}
            </span>
          ))}
        </div>
      )}
    </header>
  );
}

// ── FinalText ─────────────────────────────────────────────────────────────
// Primary landing content (MVP). Sole output of Step 1 rendered to client.
// entry_message is NOT rendered here.
// Paragraphs: split on double line breaks → separate <p> tags.
// Single line breaks within a paragraph preserved via whitespace-pre-line.

export function FinalTextBlock({ text }: { text: string }) {
  const paragraphs = text.split(/\n\n+/).filter((p) => p.trim());

  return (
    <section className="px-6 pt-6 pb-6">
      <div className="space-y-4">
        {paragraphs.map((para, i) => (
          <p
            key={i}
            className="text-[15px] leading-[1.8] text-gray-800 whitespace-pre-line"
          >
            {para.trim()}
          </p>
        ))}
      </div>
    </section>
  );
}

// ── CTA ───────────────────────────────────────────────────────────────────

// URL builders for each known channel.
// Unknown channels (not in this map) are silently ignored — no button rendered.
const CONTACT_URLS: Record<string, (v: string) => string> = {
  telegram:  (v) => `https://t.me/${v}`,
  whatsapp:  (v) => `https://wa.me/${v}`,
  phone:     (v) => `tel:${v}`,
  instagram: (v) => `https://instagram.com/${v}`,
  vk:        (v) => `https://vk.com/${v}`,
};

const CHANNEL_LABELS: Record<string, string> = {
  telegram:  "Написать в Telegram",
  whatsapp:  "Написать в WhatsApp",
  phone:     "Позвонить",
  instagram: "Instagram",
  vk:        "ВКонтакте",
};

const CHANNEL_STYLES: Record<string, string> = {
  telegram:  "bg-gray-900 hover:bg-gray-800 text-white",
  whatsapp:  "bg-green-800 hover:bg-green-700 text-white",
  phone:     "bg-amber-900 hover:bg-amber-800 text-white",
  instagram: "bg-gray-900 hover:bg-gray-800 text-white",
  vk:        "bg-blue-800 hover:bg-blue-700 text-white",
};

const TELEGRAM_SVG  = "M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.833.941z";
const WHATSAPP_SVG  = "M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z";
const INSTAGRAM_SVG = "M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z";
const VK_SVG        = "M15.684 0H8.316C1.592 0 0 1.592 0 8.316v7.368C0 22.408 1.592 24 8.316 24h7.368C22.408 24 24 22.408 24 15.684V8.316C24 1.592 22.408 0 15.684 0zm3.692 17.123h-1.744c-.66 0-.864-.525-2.05-1.727-1.033-1-1.49-1.135-1.744-1.135-.356 0-.458.102-.458.593v1.575c0 .424-.135.678-1.253.678-1.846 0-3.896-1.118-5.335-3.202C4.624 10.857 4.03 8.57 4.03 8.096c0-.254.102-.491.593-.491h1.744c.44 0 .61.203.779.677.863 2.49 2.303 4.675 2.896 4.675.22 0 .322-.102.322-.66V9.721c-.068-1.186-.695-1.287-.695-1.71 0-.203.17-.407.44-.407h2.743c.372 0 .508.203.508.643v3.473c0 .372.17.508.271.508.22 0 .407-.136.813-.542 1.253-1.405 2.151-3.574 2.151-3.574.119-.254.322-.491.763-.491h1.744c.525 0 .644.27.525.643-.22 1.017-2.354 4.031-2.354 4.031-.186.305-.254.44 0 .78.186.254.796.779 1.202 1.253.745.847 1.32 1.558 1.473 2.05.17.487-.085.735-.576.735z";
const PHONE_SVG     = "M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z";

// Icon accent colours — only for channels where we want a tinted icon on dark bg.
const CHANNEL_ICON_CLASS: Record<string, string> = {
  telegram:  "text-sky-400",
  instagram: "text-rose-400",
};

const CHANNEL_ICONS: Record<string, string> = {
  telegram:  TELEGRAM_SVG,
  whatsapp:  WHATSAPP_SVG,
  instagram: INSTAGRAM_SVG,
  vk:        VK_SVG,
  phone:     PHONE_SVG,
};

// Fixed display order for all known channels.
// cta.channels (AI-generated) is used as an ordering hint — channels listed
// there appear first. Remaining configured channels follow in CHANNEL_ORDER.
const CHANNEL_ORDER = ["telegram", "whatsapp", "phone", "instagram", "vk"] as const;

// Normalize a raw contact value into a valid href for the given channel.
// Handles usernames, partial URLs (vk.com/x, t.me/x), and full URLs equally.
// Called after the empty-value guard — value is always a non-empty trimmed string here.
function normalizeContactHref(channel: string, value: string): string {
  switch (channel) {
    case "telegram": {
      const v = value.startsWith("@") ? value.slice(1) : value;
      if (v.startsWith("https://") || v.startsWith("http://")) return v;
      if (v.startsWith("telegram.me/")) return `https://${v}`;
      if (v.startsWith("t.me/"))        return `https://${v}`;
      return `https://t.me/${v}`;
    }
    case "vk": {
      if (value.startsWith("https://") || value.startsWith("http://")) return value;
      if (value.startsWith("vk.com/")) return `https://${value}`;
      return `https://vk.com/${value}`;
    }
    case "instagram": {
      if (value.startsWith("https://") || value.startsWith("http://")) return value;
      if (value.startsWith("instagram.com/")) return `https://${value}`;
      return `https://instagram.com/${value}`;
    }
    case "whatsapp": {
      const digits = value.replace(/\D/g, "");
      return `https://wa.me/${digits}`;
    }
    case "phone":
      return `tel:${value}`;
    default:
      return value;
  }
}

export function CtaButtons({
  cta,
  contactInfo,
}: {
  cta: CtaBlock;
  contactInfo?: ContactInfo | null;
}) {
  // Guard: no contacts configured — render nothing rather than dead buttons.
  if (!contactInfo) return null;

  // Build ordered channel list:
  // 1. Start with channels from cta.channels that have a known URL builder (AI ordering hint).
  // 2. Append remaining CHANNEL_ORDER channels not already included.
  // This ensures all configured contacts are shown, not only those AI listed.
  const aiChannels = cta.channels.filter((ch) => CONTACT_URLS[ch]);
  const remaining  = CHANNEL_ORDER.filter((ch) => !aiChannels.includes(ch));
  const orderedChannels = [...aiChannels, ...remaining];

  // Resolve active buttons: channel must be known AND have a non-empty contact value.
  // href is built via normalizeContactHref — handles full URLs, partial URLs, and plain usernames.
  const activeButtons = orderedChannels.flatMap((ch) => {
    if (!CONTACT_URLS[ch]) return []; // unknown channel — ignore
    const value = contactInfo[ch as keyof ContactInfo]?.trim();
    if (!value) return []; // no contact value configured for this channel
    return [{
      channel: ch,
      href:    normalizeContactHref(ch, value),
      label:   CHANNEL_LABELS[ch] ?? ch,
      style:   CHANNEL_STYLES[ch] ?? "bg-gray-900 text-white",
      icon:    CHANNEL_ICONS[ch] ?? null,
      iconClassName: CHANNEL_ICON_CLASS[ch] ?? "text-white",
    }];
  });

  if (activeButtons.length === 0) return null;

  return (
    <section className="px-6 pt-6 pb-8 space-y-3 border-t border-gray-100">
      <p className="text-[14px] text-gray-800 text-center mb-1">
        Если откликается такой формат
      </p>
      <p className="text-[15px] font-semibold text-gray-900 text-center mb-5">
        Напишите мне
      </p>
      {activeButtons.map(({ channel, href, label, style, icon, iconClassName }) => (
        <a
          key={channel}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className={`flex items-center justify-center gap-2 w-full rounded-xl py-3.5 text-sm font-semibold transition-colors ${style}`}
        >
          {icon && (
            <svg className={`w-5 h-5 ${iconClassName}`} viewBox="0 0 24 24" fill="currentColor">
              <path d={icon} />
            </svg>
          )}
          {label}
        </a>
      ))}
    </section>
  );
}