from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class ProjectCreate(BaseModel):
    name: str
    created_by: str
    status: str
    description: Optional[str] = None


class ProjectOut(BaseModel):
    id: UUID
    name: str
    created: datetime
    created_by: str
    status: str
    description: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
