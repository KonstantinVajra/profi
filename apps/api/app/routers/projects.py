"""
Projects router
───────────────
POST /projects       — create project workspace
GET  /projects/{id}  — get project
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.repositories.order_repo import OrderRepository

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project workspace. One project = one order."""
    repo = OrderRepository(db)
    project = repo.create_project(title=body.title)
    return ProjectResponse(
        id=project.id,
        title=project.title,
        status=project.status,
        created_at=project.created_at,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    repo = OrderRepository(db)
    project = repo.get_project(project_id)
    return ProjectResponse(
        id=project.id,
        title=project.title,
        status=project.status,
        created_at=project.created_at,
    )
