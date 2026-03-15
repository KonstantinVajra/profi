"""
LandingGeneratorService
───────────────────────
Receives ParsedOrder, generates LandingPageModel JSON.

Key rule: AI generates JSON data, not HTML.
Frontend renders HTML from this JSON via template.

Responsibilities:
- select appropriate template_key from event_type
- select photo_set_id from event_type
- generate hero, price_card, quick_questions, cta via AI
- assemble complete LandingPageModel
- save to landing_content table
"""
from app.schemas.order import ParsedOrder
from app.schemas.landing import LandingPageModel


class LandingGeneratorService:
    def generate(self, parsed_order: ParsedOrder, project_id: str) -> LandingPageModel:
        # TODO: implement — call AI, return LandingPageModel
        raise NotImplementedError

    def _build_slug(self, parsed_order: ParsedOrder) -> str:
        # Example: kseniya-registry-11-june
        # TODO: implement slug generation
        raise NotImplementedError
