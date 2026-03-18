/**
 * Frontend types for LandingPageModel.
 * Mirror of backend app/schemas/landing.py
 * Used by /r/[slug] page and block components.
 */

export interface HeroBlock {
  title: string;
  subtitle?: string;
}

export interface BadgesBlock {
  items: string[];
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
  photo_set_id: string;
}

export interface SimilarCase {
  case_series_id?: string;
  title?: string;
  description?: string;
}

export interface WorkBlock {
  steps: string[];
}

export interface ReviewItem {
  review_id?: string;
  author?: string;
  text?: string;
}

export interface CtaBlock {
  channels: string[];
}

export interface PersonalBlock {
  request_match: string;
  key_feature: string;
  trust_line: string;
  hook_line: string;
}

export interface LandingPageModel {
  slug: string;
  template_key: string;
  // required
  hero: HeroBlock;
  price_card: PriceCard;
  style_grid: StyleGrid;
  quick_questions: string[];
  cta: CtaBlock;
  // optional
  badges?: BadgesBlock;
  photographer?: Photographer;
  similar_case?: SimilarCase;
  work_block?: WorkBlock;
  reviews: ReviewItem[];
  secondary_actions: string[];
  personal_block?: PersonalBlock | null;
}

export interface LandingPageMeta {
  id: string;
  project_id: string;
  slug: string;
  template_key: string;
  status: string;
  is_public: boolean;
  created_at: string;
}

export interface LandingPublicResponse {
  landing_page: LandingPageMeta;
  landing_content: LandingPageModel;
}