/**
 * /r/[slug] — Public micro landing page
 *
 * Fetches LandingPageModel JSON from backend.
 * Renders blocks from JSON via template components.
 * AI never generates HTML — this file is the renderer.
 *
 * Render modes:
 *
 *   MVP mode (c.final_text is present and non-empty):
 *     OrderHeader → FinalTextBlock → StyleGrid → CtaButtons
 *     All legacy structural blocks are suppressed.
 *     Layout: white card on a lightly tinted background.
 *
 *   Legacy mode (c.final_text absent or empty):
 *     hero → personal_block → badges → style_grid → similar_case → price_card
 *     → photographer → work_block → reviews → quick_questions → cta
 *     Unchanged — backward compatible with old landings.
 */

import { notFound } from "next/navigation";
import type { LandingPublicResponse } from "@/types/landing";
import type { ContactInfo } from "@/lib/api";
import {
  Hero,
  Badges,
  StyleGrid,
  SimilarCaseBlock,
  PriceCardBlock,
  PhotographerBlock,
  WorkBlockSection,
  Reviews,
  QuickQuestions,
  CtaButtons,
  PersonalBlockSection,
  FinalTextBlock,
  OrderHeader,
} from "@/components/landing/blocks";
import { RelatedAlbumsBlock } from "@/components/landing/RelatedAlbumsBlock";

// ── Data fetching ─────────────────────────────────────────────────────────

async function getLanding(slug: string): Promise<LandingPublicResponse | null> {
  // SSR: use internal URL directly — Node.js cannot resolve relative /api paths.
  // No nginx rewrite here; fetch goes straight to backend.
  const apiUrl = process.env.INTERNAL_API_URL ?? "http://127.0.0.1:8000";
  try {
    const res = await fetch(`${apiUrl}/public/landings/${slug}`, {
      cache: "no-store",
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
  } catch {
    return null;
  }
}

// Fetch project contact_info for CTA button links.
// Contacts live in Project domain, not in Landing contract.
// Returns null on any failure — CtaButtons renders nothing without contacts.
async function getContactInfo(projectId: string): Promise<ContactInfo | null> {
  // SSR: use internal URL directly — Node.js cannot resolve relative /api paths.
  // No nginx rewrite here; fetch goes straight to backend.
  const apiUrl = process.env.INTERNAL_API_URL ?? "http://127.0.0.1:8000";
  try {
    const res = await fetch(`${apiUrl}/projects/${projectId}`, { cache: "no-store" });
    if (!res.ok) return null;
    const project = await res.json();
    return (project.contact_info as ContactInfo) ?? null;
  } catch {
    return null;
  }
}

// ── Page ──────────────────────────────────────────────────────────────────

export default async function LandingPage({
  params,
}: {
  params: { slug: string };
}) {
  const data = await getLanding(params.slug);

  if (!data) return notFound();

  const c = data.landing_content;
  // contacts live in Project, fetched separately from landing contract
  const contactInfo = await getContactInfo(data.landing_page.project_id);

  // MVP mode: final_text is the primary body copy.
  // Layout: OrderHeader → final_text → photo block → contacts.
  // Legacy blocks are not rendered in this mode.
  const isMvpMode = Boolean(c.final_text?.trim());

  if (isMvpMode) {
    return (
      <div className="min-h-screen bg-stone-50 py-8 px-4">
        <div className="max-w-lg mx-auto bg-white rounded-2xl shadow-sm overflow-hidden">

          <OrderHeader
            templateKey={c.template_key}
            price={c.price_card?.price}
            heroTitleOverride={c.hero_title_override}
          />

          <FinalTextBlock text={c.final_text!.trim()} />

          <StyleGrid grid={c.style_grid} />

          {c.related_block && (
            <RelatedAlbumsBlock categoryKey={c.related_block.category_key} />
          )}

          <CtaButtons cta={c.cta} contactInfo={contactInfo} />

        </div>
      </div>
    );
  }

  // Legacy mode: backward compatible with old landings without final_text.
  return (
    <main className="min-h-screen bg-white max-w-lg mx-auto px-4 pb-32">

      <Hero hero={c.hero} />

      {c.personal_block && <PersonalBlockSection block={c.personal_block} />}

      {c.badges && <Badges badges={c.badges} />}

      <StyleGrid grid={c.style_grid} />

      {c.related_block && (
        <RelatedAlbumsBlock categoryKey={c.related_block.category_key} />
      )}

      {c.similar_case && <SimilarCaseBlock similarCase={c.similar_case} />}

      <PriceCardBlock priceCard={c.price_card} />

      {c.photographer && <PhotographerBlock photographer={c.photographer} />}

      {c.work_block && <WorkBlockSection workBlock={c.work_block} />}

      <Reviews reviews={c.reviews} />

      <QuickQuestions questions={c.quick_questions} />

      <CtaButtons cta={c.cta} contactInfo={contactInfo} />

    </main>
  );
}