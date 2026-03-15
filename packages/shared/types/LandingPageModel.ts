/**
 * LandingPageModel
 *
 * JSON model for a micro landing page.
 * AI generates this structure. The frontend renders it via template.
 *
 * RULE: AI never generates HTML. This JSON is the contract between
 * the AI layer and the template renderer in Next.js.
 *
 * Mirror of backend app/schemas/landing.py :: LandingPageModel
 */

export interface HeroBlock {
  title: string;
  subtitle?: string;
}

export interface PriceCard {
  price: string;
  description: string;
}

export interface Photographer {
  name: string;
  role: string;
}

export interface StyleGrid {
  /** References a photo_set record in the DB. Frontend loads photos from it. */
  photo_set_id: string;
}

export interface SimilarCase {
  case_series_id?: string;
  title?: string;
  description?: string;
}

export interface Review {
  author: string;
  text: string;
}

export interface CtaBlock {
  channels: Array<"telegram" | "whatsapp" | "phone">;
}

export interface LandingPageModel {
  slug: string;
  template_key: string;
  hero: HeroBlock;
  price_card: PriceCard;
  photographer: Photographer;
  style_grid: StyleGrid;
  similar_case?: SimilarCase;
  reviews: Review[];
  quick_questions: string[];
  cta: CtaBlock;
}
