# app/routers/uploads.py
from dataclasses import asdict
from fastapi import APIRouter, HTTPException, Query, Depends
from app.services.s3_service import build_object_key, create_presigned_post
from app.schemas import PresignedPostOut, PresignedPostResponse
from app.config import settings
from app.database import get_session
from sqlalchemy.orm import Session
from app.models import DiscoveryArtifact
from datetime import datetime, timezone
from app.services.s3_service import head_object
from starlette.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/uploads", tags=["uploads"])

@router.post("/presign-post", response_model=PresignedPostResponse)
async def presign_post(
    filename: str = Query(..., min_length=1, description="Original file name"),
    content_type: str = Query(..., min_length=3, description="Exact MIME type"),
    project_id: str | None = Query(None),
    user_id: str | None = Query(None),
    max_bytes: int | None = Query(None, ge=1, le=settings.S3_MAX_BYTES, description="Optional override <= bucket limit"),
    db: Session = Depends(get_session),
):
    try:
        key = build_object_key(filename=filename, project_id=project_id, user_id=user_id)
        token = create_presigned_post(
            key=key,
            content_type=content_type,
            max_bytes=max_bytes,
        )
        artifact = DiscoveryArtifact(
            s3_key=key,
            project_id=project_id,
            user_id=user_id,
            original_filename=filename,
            content_type=content_type,
            s3_bucket=settings.S3_BUCKET,
            public_url=token.public_url,
            status="pending",
        )
        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)
        return {"upload": PresignedPostOut(**asdict(token))}
    except ValueError as ve:
        # e.g., disallowed content-type or prefix violation → 415 is clearer
        raise HTTPException(status_code=415, detail=str(ve))
    except Exception as e:
        # log `e` if you have a logger
        raise HTTPException(status_code=500, detail="Failed to presign upload")
    
@router.post("/confirm")
async def confirm_upload(
    key: str = Query(..., min_length=3),
    db: AsyncSession = Depends(get_session),
):
    # get by primary key (s3_key)
    artifact = await db.get(DiscoveryArtifact, key)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    try:
        # head_object uses boto3 (blocking). Run in a thread to avoid blocking the event loop:
        meta = await run_in_threadpool(head_object, key=key)
        # If you prefer to call directly, it's usually fine too for small loads:
        # meta = head_object(key=key)
    except Exception:
        # client can retry confirm shortly after if S3 is not yet consistent
        raise HTTPException(status_code=409, detail=f"Object not visible yet for {key}")

    artifact.size_bytes = meta.get("content_length") or artifact.size_bytes
    artifact.etag = meta.get("etag") or artifact.etag
    artifact.status = "uploaded"
    if artifact.uploaded_at is None:
        from datetime import datetime, timezone
        artifact.uploaded_at = datetime.now(timezone.utc)

    await db.commit()
    return {"ok": True, "key": key, "size_bytes": artifact.size_bytes, "etag": artifact.etag, "status": artifact.status}