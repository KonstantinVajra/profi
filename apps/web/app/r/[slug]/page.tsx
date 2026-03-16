/**
 * /r/[slug] — Public micro landing page
 *
 * Fetches LandingPageModel JSON from backend.
 * Renders blocks from JSON via template components.
 * AI never generates HTML — this file is the renderer.
 *
 * Block render order:
 *   hero → badges → style_grid → similar_case → price_card
 *   → photographer → work_block → reviews → quick_questions → cta
 */

import { notFound } from "next/navigation";
import type { LandingPublicResponse } from "@/types/landing";
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
} from "@/components/landing/blocks";

// ── Data fetching ─────────────────────────────────────────────────────────

async function getLanding(slug: string): Promise<LandingPublicResponse | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/public/landings/${slug}`, {
      cache: "no-store",   // always fresh for MVP — no caching complexity
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
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

  return (
    <main className="min-h-screen bg-white max-w-lg mx-auto px-4 pb-32">

      <Hero hero={c.hero} />

      {c.badges && <Badges badges={c.badges} />}

      <StyleGrid grid={c.style_grid} />

      {c.similar_case && <SimilarCaseBlock similarCase={c.similar_case} />}

      <PriceCardBlock priceCard={c.price_card} />

      {c.photographer && <PhotographerBlock photographer={c.photographer} />}

      {c.work_block && <WorkBlockSection workBlock={c.work_block} />}

      <Reviews reviews={c.reviews} />

      <QuickQuestions questions={c.quick_questions} />

      <CtaButtons cta={c.cta} />

    </main>
  );
}
