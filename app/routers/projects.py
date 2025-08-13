from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import uuid4, UUID
from datetime import  datetime, timezone
from typing import List
from app.deps import get_current_user, require_csrf

from app import schemas, models
from app.database import get_session


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/api/list", response_model=List[schemas.ProjectOut])
async def get_projects(
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user)
):
    # Query all projects, newest first
    result = await db.execute(
        select(models.Project)
        .where(models.Project.status == "active")
        .order_by(models.Project.created.desc())  # sort by created timestamp descending
        .options(selectinload("*"))  # optional: eager load relationships if needed
    )
    projects = result.scalars().all()
    return projects



@router.post("/api/create", response_model=schemas.ProjectOut, status_code=201,
             dependencies=[Depends(get_current_user),Depends(require_csrf)])
async def create_project(
    payload: schemas.ProjectCreate, 
    db: AsyncSession = Depends(get_session),
):
    obj = models.Project(
        id=uuid4(),
        name=payload.name,
        created_by=payload.created_by,
        status=payload.status,
        description=payload.description,
    )
    db.add(obj)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Project could not be created (constraint failed).")
    await db.refresh(obj)
    return obj

@router.patch("/api/{project_id}", response_model=schemas.ProjectOut,
              dependencies=[Depends(get_current_user),Depends(require_csrf)])
async def update_project(
    project_id: UUID,
    payload: schemas.ProjectUpdate,
    db: AsyncSession = Depends(get_session),
):
    obj = await db.get(models.Project, project_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Only apply fields that were provided
    fields = ("name", "status")
    changed = False
    for f in fields:
        val = getattr(payload, f)
        if val is not None:
            setattr(obj, f, val)
            changed = True

    if not changed:
        raise HTTPException(status_code=400, detail="No fields to update.")

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Project could not be updated (constraint failed).")

    await db.refresh(obj)
    return obj