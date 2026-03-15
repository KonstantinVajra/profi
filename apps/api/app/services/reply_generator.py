"""
ReplyGeneratorService
─────────────────────
Receives ParsedOrder, generates 3 reply variants.

Responsibilities:
- build prompt from ParsedOrder
- call OpenAI with structured output
- inject landing page link into each variant
- return list[ReplyVariant]
"""
from app.schemas.order import ParsedOrder
from app.schemas.reply import ReplyVariant


class ReplyGeneratorService:
    def generate(self, parsed_order: ParsedOrder, landing_slug: str) -> list[ReplyVariant]:
        # TODO: implement — call AI, return 3 variants
        raise NotImplementedError
