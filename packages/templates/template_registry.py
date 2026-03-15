"""
Landing page template registry.

Maps template_key → config.
Used by LandingGeneratorService to select the right template
based on event_type from ParsedOrder.
"""

TEMPLATE_REGISTRY = {
    "registry_small": {
        "label": "Регистрация / ЗАГС",
        "default_photo_set": "registry_light",
        "photo_count": 6,
        "blocks": ["hero", "photo_grid", "similar_case", "price", "reviews", "quick_questions", "cta"],
    },
    "wedding_full": {
        "label": "Свадьба",
        "default_photo_set": "wedding_outdoor",
        "photo_count": 8,
        "blocks": ["hero", "photo_grid", "similar_case", "price", "reviews", "quick_questions", "cta"],
    },
    "family_session": {
        "label": "Семейная съёмка",
        "default_photo_set": "family_warm",
        "photo_count": 6,
        "blocks": ["hero", "photo_grid", "price", "reviews", "quick_questions", "cta"],
    },
    "event_general": {
        "label": "Мероприятие / репортаж",
        "default_photo_set": "event_reportage",
        "photo_count": 8,
        "blocks": ["hero", "photo_grid", "price", "quick_questions", "cta"],
    },
}

# Maps common event_type strings → template_key
EVENT_TYPE_MAP = {
    "регистрация": "registry_small",
    "загс": "registry_small",
    "свадьба": "wedding_full",
    "венчание": "wedding_full",
    "семейная": "family_session",
    "дети": "family_session",
    "мероприятие": "event_general",
    "корпоратив": "event_general",
    "репортаж": "event_general",
}


def resolve_template(event_type: str | None) -> str:
    """Pick a template_key from event_type string. Falls back to registry_small."""
    if not event_type:
        return "registry_small"
    lower = event_type.lower()
    for keyword, template_key in EVENT_TYPE_MAP.items():
        if keyword in lower:
            return template_key
    return "registry_small"
