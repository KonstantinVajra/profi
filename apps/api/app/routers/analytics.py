from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db

router = APIRouter()


class OpenEvent(BaseModel):
    slug: str
    project_id: str


class CtaClickEvent(BaseModel):
    slug: str
    project_id: str
    channel: str


@router.post("/open")
def track_open(body: OpenEvent, db: Session = Depends(get_db)):
    """Track landing page open event."""
    # TODO: implement in Phase 3
    return {"recorded": True}


@router.post("/cta-click")
def track_cta_click(body: CtaClickEvent, db: Session = Depends(get_db)):
    """Track CTA button click event."""
    # TODO: implement in Phase 3
    return {"recorded": True}


@router.get("/projects/{project_id}/analytics")
def get_analytics(project_id: str, db: Session = Depends(get_db)):
    """Get analytics summary for a project."""
    # TODO: implement in Phase 3
    raise NotImplementedError
