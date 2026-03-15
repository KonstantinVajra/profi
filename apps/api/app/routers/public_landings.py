"""
Public landings router
──────────────────────
GET /public/landings/{slug}

Returns landing_page metadata + landing_content JSON for a given slug.
Used by the Next.js /r/[slug] page to render the public landing.

No auth. No publish gate. No analytics in this step.
404 if slug not found or content missing.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.landing import LandingPageMetadata, LandingPageModel, LandingPublicResponse
from app.repositories.landing_repo import LandingRepository

router = APIRouter()


@router.get(
    "/{slug}",
    response_model=LandingPublicResponse,
    summary="Get landing page content by slug",
)
def get_landing_by_slug(slug: str, db: Session = Depends(get_db)):
    repo = LandingRepository(db)

    page = repo.get_landing_by_slug(slug)

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Landing '{slug}' not found",
        )

    if not page.content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Landing '{slug}' has no content",
        )

    return LandingPublicResponse(
        landing_page=LandingPageMetadata(
            id=page.id,
            project_id=page.project_id,
            slug=page.slug,
            template_key=page.template_key,
            status=page.status,
            is_public=page.is_public,
            created_at=page.created_at,
        ),
        landing_content=LandingPageModel.model_validate(page.content.content_json),
    )
