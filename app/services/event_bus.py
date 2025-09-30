from __future__ import annotations
import json, time
import boto3
from botocore.config import Config as BotoConfig
from app.config import settings

_sqs = boto3.client(
    "sqs",
    region_name=settings.AWS_REGION,
    config=BotoConfig(retries={"max_attempts": 3, "mode": "standard"}),
)

def publish_artifact_uploaded(*, s3_key: str, bucket: str, project_id: str | None,
                              user_id: str | None, original_filename: str,
                              content_type: str, public_url: str):
    if not settings.SQS_UPLOADS_QUEUE_URL:
       
        return  # silently skip in local if not configured
    body = {
        "type": "ArtifactUploaded",
        "version": "1",
        "occurred_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "correlation_id": s3_key,           # use key as correlation/idempotency
        "artifact": {
            "s3_key": s3_key,
            "bucket": bucket,
            "project_id": project_id,
            "user_id": user_id,
            "original_filename": original_filename,
            "content_type": content_type,
            "public_url": public_url,
        },
    }
    _sqs.send_message(
        QueueUrl=settings.SQS_UPLOADS_QUEUE_URL,
        MessageBody=json.dumps(body),
        MessageAttributes={
            "event": {"StringValue": "ArtifactUploaded", "DataType": "String"},
        },
    )