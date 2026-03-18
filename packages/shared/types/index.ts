/**
 * @deprecated
 *
 * This package is NOT the canonical source of truth for Landing Reply contracts.
 *
 * These types are legacy and may drift from the actual backend/frontend contracts.
 *
 * Canonical sources of truth:
 *   - API / AI contracts: apps/api/app/schemas/*.py
 *   - DB contracts:       apps/api/app/models/*.py
 *   - Landing frontend:   apps/web/types/landing.ts
 *
 * Do not import from this package in active MVP flow.
 * Do not treat these types as authoritative when writing new code.
 */

export type { ParsedOrder } from "./ParsedOrder";
export type { ReplyVariant, ReplyType } from "./ReplyVariant";
export type {
  LandingPageModel,
  HeroBlock,
  PriceCard,
  Photographer,
  StyleGrid,
  SimilarCase,
  Review,
  CtaBlock,
} from "./LandingPageModel";
export type { DialogueSuggestion, FunnelStage } from "./DialogueSuggestion";