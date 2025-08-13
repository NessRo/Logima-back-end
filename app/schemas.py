from pydantic import BaseModel, EmailStr, constr
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
