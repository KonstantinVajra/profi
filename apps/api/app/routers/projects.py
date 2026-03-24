"""
Projects router
───────────────
POST   /projects               — create project workspace
GET    /projects/{id}          — get project (includes contact_info)
PATCH  /projects/{id}/contacts — save photographer contact links
"""

import logging

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.project import ContactInfo, ProjectContactUpdate, ProjectCreate, ProjectResponse
from app.repositories.order_repo import OrderRepository

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(project) -> ProjectResponse:
    """Map ORM Project to ProjectResponse, hydrating contact_info if present."""
    contact_info = None
    if project.contact_info:
        contact_info = ContactInfo.model_validate(project.contact_info)
    return ProjectResponse(
        id=project.id,
        title=project.title,
        status=project.status,
        created_at=project.created_at,
        contact_info=contact_info,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(request: Request, body: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project workspace. One project = one order."""
    repo = OrderRepository(db)
    project = repo.create_project(title=body.title)
    base = str(request.base_url).rstrip("/")
    logger.warning("DEBUG TRACE: %s/debug/project/%s", base, project.id)
    return _to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    repo = OrderRepository(db)
    project = repo.get_project(project_id)
    return _to_response(project)


@router.patch("/{project_id}/contacts", response_model=ProjectResponse)
def update_project_contacts(
    project_id: str,
    body: ProjectContactUpdate,
    db: Session = Depends(get_db),
):
    """
    Save photographer contact links for a project.
    Replaces the entire contact_info in one write (no partial update).
    Values are trimmed and normalised by ProjectContactUpdate validator.
    """
    repo = OrderRepository(db)
    project = repo.get_project(project_id)  # raises 404 if not found

    project.contact_info = body.contact_info.model_dump()
    db.commit()
    db.refresh(project)

    logger.info("Contacts updated | project=%s", project_id)
    return _to_response(project)
