from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import uuid4, UUID
from datetime import  datetime, timezone
from typing import List,Optional
from app.deps import get_current_user, require_csrf
from app.services.openai_service import OpenAIService

from app import schemas, models
from app.database import get_session

oai_service = OpenAIService()

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/api/list", response_model=List[schemas.ProjectOut])
async def get_projects(
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    # Query all projects, newest first
    result = await db.execute(
        select(models.Project)
        .where(
            models.Project.status == "active",
            models.Project.owner_id == user.id)
        .order_by(models.Project.created.desc())  # sort by created timestamp descending
        .options(selectinload("*"))  # optional: eager load relationships if needed
    )
    projects = result.scalars().all()
    return projects

@router.get("/api/{project_id}", response_model=schemas.ProjectOut)
async def get_project_by_id(
    project_id: UUID,
    db: AsyncSession = Depends(get_session)
):
    result = await db.execute(
        select(models.Project)
        .where(
            models.Project.id == project_id,
        )
        .options(selectinload("*"))
    )
    project = result.scalar_one_or_none()
    if project is None:
        # Returning 404 avoids leaking existence of other users' IDs.
        raise HTTPException(status_code=404, detail="Project not found")
    return project



@router.post("/api/create", response_model=schemas.ProjectOut, status_code=201,
             dependencies=[Depends(require_csrf)])
async def create_project(
    payload: schemas.ProjectCreate, 
    db: AsyncSession = Depends(get_session),
    user = Depends(get_current_user),
):
    
    ai_project_outcome = await oai_service.generate_outcome(payload.description or "")

    obj = models.Project(
        id=uuid4(),
        name=payload.name,
        owner_id=user.id,
        status=payload.status,
        description=payload.description,
        project_outcome=ai_project_outcome
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
    ALLOWED_FIELDS = {"name", "status", "project_outcome"}

    data = payload.model_dump(exclude_unset=True)

    data = {k: v for k, v in data.items() if k in ALLOWED_FIELDS}

    if not data:
        raise HTTPException(status_code=400, detail="No fields to update.")
    
    for k, v in data.items():
        setattr(obj, k, v)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Project could not be updated (constraint failed).")

    await db.refresh(obj)
    return obj

# AI focused APIs for high level project
@router.post(
    "/api/{project_id}/ai-refresh",
    response_model=schemas.ProjectOut,
    dependencies=[Depends(get_current_user), Depends(require_csrf)],
)
async def regenerate_project_outcome(
    project_id: UUID,
    payload: Optional[schemas.OutcomeRegenerate] = None,  # optional override
    db: AsyncSession = Depends(get_session),
):
    obj = await db.get(models.Project, project_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Choose description: override if provided, else use current project.description
    source_description = (
        (payload.description if payload and payload.description is not None else obj.description) or ""
    )

    try:
        new_outcome = await oai_service.generate_outcome(source_description)
    except Exception as e:
        # Surface a clean error; you can map specific exceptions as needed
        raise HTTPException(status_code=502, detail=f"AI generation failed: {e}")

    obj.project_outcome = new_outcome
    # Optional: track when/why this changed
    # obj.outcome_updated_at = datetime.utcnow()
    # obj.outcome_update_reason = "ai_refresh"

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Project could not be updated (constraint failed).")

    await db.refresh(obj)
    return obj