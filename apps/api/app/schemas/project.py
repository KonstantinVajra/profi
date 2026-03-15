from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    title: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
