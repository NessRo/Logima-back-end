# app/config.py
from pathlib import Path
from typing import List, Optional, Any
from pydantic import Field, AliasChoices, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import json

# Load .env early so boto3 can see AWS_* env vars
REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

class Settings(BaseSettings):
    # --- App / OAuth ---
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URL: str

    SESSION_SECRET: str
    SECRET_KEY: str

    DATABASE_URL: str
    SQLALCHEMY_ECHO: bool = False
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    ENV: str = "dev"

    # OpenAI — keep your existing attr name but accept either env var casing
    openai_api_key: str = Field(validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"))

    # --- AWS/S3 ---
    AWS_REGION: str = "us-east-2"  # your bucket is in Ohio
    S3_BUCKET: str
    S3_PUBLIC_BASE_URL: Optional[str] = None
    S3_KEY_PREFIX: str = "uploads"
    S3_PRESIGN_EXPIRES: int = 600
    S3_MAX_BYTES: int = 1_000_000_000
    S3_ALLOWED_CONTENT_TYPES: List[str] = [
        "image/png", "image/jpeg", "application/pdf",
        "text/plain", "application/octet-stream",
    ]
    SQS_UPLOADS_QUEUE_URL: str | None = None

    # Local dev creds (optional). Leave unset in prod (EC2 role will be used).
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None
    AWS_PROFILE: Optional[str] = None  # if you prefer profiles locally

    # Accept JSON (preferred) or CSV in .env for content types
    @field_validator("S3_ALLOWED_CONTENT_TYPES", mode="before")
    @classmethod
    def _parse_cts(cls, v: Any) -> Any:
        if isinstance(v, str):
            s = v.strip()
            try:
                j = json.loads(s)
                if isinstance(j, list):
                    return j
            except Exception:
                pass
            return [x.strip() for x in s.split(",") if x.strip()]
        return v

    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

settings = Settings()