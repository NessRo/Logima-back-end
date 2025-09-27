# app/routers/uploads.py
from dataclasses import asdict
from fastapi import APIRouter, HTTPException, Query
from app.services.s3_service import build_object_key, create_presigned_post
from app.schemas import PresignedPostOut, PresignedPostResponse
from app.config import settings

router = APIRouter(prefix="/uploads", tags=["uploads"])

@router.post("/presign-post", response_model=PresignedPostResponse)
def presign_post(
    filename: str = Query(..., min_length=1, description="Original file name"),
    content_type: str = Query(..., min_length=3, description="Exact MIME type"),
    project_id: str | None = Query(None),
    user_id: str | None = Query(None),
    max_bytes: int | None = Query(None, ge=1, le=settings.S3_MAX_BYTES, description="Optional override <= bucket limit"),
):
    try:
        key = build_object_key(filename=filename, project_id=project_id, user_id=user_id)
        token = create_presigned_post(
            key=key,
            content_type=content_type,
            max_bytes=max_bytes,
        )
        return {"upload": PresignedPostOut(**asdict(token))}
    except ValueError as ve:
        # e.g., disallowed content-type or prefix violation → 415 is clearer
        raise HTTPException(status_code=415, detail=str(ve))
    except Exception as e:
        # log `e` if you have a logger
        raise HTTPException(status_code=500, detail="Failed to presign upload")