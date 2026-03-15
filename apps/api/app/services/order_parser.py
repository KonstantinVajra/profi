"""
OrderParserService
──────────────────
Receives raw order text, calls OpenAI, returns ParsedOrder.

Responsibilities:
- clean and normalise raw text
- call AI with structured output prompt
- validate response against ParsedOrder schema
- save to parsed_orders table
"""
from app.schemas.order import ParsedOrder


class OrderParserService:
    def parse(self, raw_text: str) -> ParsedOrder:
        # TODO: implement — call AI, return ParsedOrder
        raise NotImplementedError
