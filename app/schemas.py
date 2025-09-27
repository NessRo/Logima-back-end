from pydantic import BaseModel, EmailStr, constr
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict


class ProjectCreate(BaseModel):
    name: str
    status: str
    description: Optional[str] = None


class ProjectOut(BaseModel):
    id: UUID
    name: str
    created: datetime
    owner_id: UUID
    status: str
    description: Optional[str] = None
    project_outcome: str

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    project_outcome: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=8)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    created: datetime
    class Config:
        from_attributes = True

class TokenOK(BaseModel):
    ok: bool = True

class ProjectList(BaseModel):
    created_by: str

class OutcomeRegenerate(BaseModel):
    description: Optional[str] = None  # if provided, will be used as the AI input

class PresignedPostOut(BaseModel):
    url: str
    fields: Dict[str, str]
    key: str
    public_url: str

class PresignedPostResponse(BaseModel):
    upload: PresignedPostOut