# app/services/s3_service.py
from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

# expects a Settings object in app/config.py (see below)
from app.config import settings  # type: ignore


SSE_ALGO = getattr(settings, "S3_SSE_ALGORITHM", "AES256")  # or "aws:kms"
KMS_KEY_ID = getattr(settings, "S3_KMS_KEY_ID", None)

def _assert_under_prefix(key: str) -> None:
    # ensure uploads stay under the configured prefix
    pref = settings.S3_KEY_PREFIX.rstrip("/") + "/"
    if not key.startswith(pref):
        raise ValueError(f"Key must start with prefix '{pref}'")

@dataclass(frozen=True)
class PresignedPost:
    url: str
    fields: Dict[str, str]
    key: str
    public_url: str


def _client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        config=BotoConfig(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=5,
            read_timeout=60,
        ),
    )


_s3 = _client()


def build_object_key(
    *,
    filename: str,
    prefix: Optional[str] = None,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """
    Generate a safe key like:
      uploads/{project_id}/{user_id}/{uuid}-{filename}
    (no YYYY/MM time component)
    """
    base_prefix = (prefix or settings.S3_KEY_PREFIX).strip("/")

    # basic hardening & cross-platform basename
    safe_name = os.path.basename(filename).replace("\\", "/").split("/")[-1]
    safe_name = safe_name.replace("..", "").replace("/", "")

    segments = [base_prefix]
    if project_id:
        segments.append(project_id.strip("/"))
    if user_id:
        segments.append(user_id.strip("/"))

    key_prefix = "/".join(s for s in segments if s)
    return f"{key_prefix}/{uuid.uuid4().hex}-{safe_name}"


def _public_url(key: str) -> str:
    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{key}"
    return f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


def create_presigned_post(
    *, key: str, content_type: str,
    max_bytes: Optional[int] = None,
    expires_seconds: Optional[int] = None,
    server_side_encryption: str = SSE_ALGO,
) -> PresignedPost:
    if content_type not in settings.S3_ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Disallowed content type: {content_type}")

    _assert_under_prefix(key)

    max_len = max_bytes or settings.S3_MAX_BYTES
    expires = expires_seconds or settings.S3_PRESIGN_EXPIRES

    conditions = [
        {"bucket": settings.S3_BUCKET},
        {"key": key},
        {"Content-Type": content_type},
        ["content-length-range", 1, max_len],
        {"x-amz-server-side-encryption": server_side_encryption},
    ]
    fields = {
        "Content-Type": content_type,
        "x-amz-server-side-encryption": server_side_encryption,
        # "success_action_status": "201",  # optional if you prefer 201 over 204
    }
    if server_side_encryption == "aws:kms" and KMS_KEY_ID:
        conditions.append({"x-amz-server-side-encryption-aws-kms-key-id": KMS_KEY_ID})
        fields["x-amz-server-side-encryption-aws-kms-key-id"] = KMS_KEY_ID

    try:
        resp = _s3.generate_presigned_post(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expires,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"Failed to create presigned POST: {e}") from e

    return PresignedPost(
        url=resp["url"],
        fields=resp["fields"],
        key=key,
        public_url=_public_url(key),
    )

def head_object(*, key: str) -> Dict[str, Any]:
    """
    Fetch object metadata without downloading it.
    Returns { content_length, content_type, etag, last_modified }
    Raises FileNotFoundError if the object doesn't exist.
    """
    try:
        r = _s3.head_object(Bucket=settings.S3_BUCKET, Key=key)
        return {
            "content_length": r.get("ContentLength"),
            "content_type": r.get("ContentType"),
            "etag": r.get("ETag"),
            "last_modified": (
                r.get("LastModified").isoformat() if r.get("LastModified") else None
            ),
        }
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in ("404", "NoSuchKey", "NotFound"):
            raise FileNotFoundError(f"S3 object not found: {key}") from e
        raise RuntimeError(f"HEAD failed for {key}: {e}") from e
