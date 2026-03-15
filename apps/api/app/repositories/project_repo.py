"""
ProjectRepository
─────────────────
Database access layer for projects.
No business logic here — only DB queries.
"""
from sqlalchemy.orm import Session


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, title: str | None = None):
        # TODO: implement
        raise NotImplementedError

    def get_by_id(self, project_id: str):
        # TODO: implement
        raise NotImplementedError
