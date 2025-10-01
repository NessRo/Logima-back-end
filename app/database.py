# app/database.py
import asyncio
from typing import AsyncGenerator, Optional
from urllib.parse import quote_plus

import boto3
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# Globals created lazily
_engine = None
_SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None
_engine_lock = asyncio.Lock()

# boto3 client for IAM auth token
_rds = boto3.client("rds", region_name=settings.AWS_REGION)

def _iam_token() -> str:
    """Create a short-lived DB auth token for IAM login."""
    if not (settings.DB_HOST and settings.DB_USER and settings.DB_PORT):
        raise RuntimeError("DB_HOST/DB_USER/DB_PORT must be set for IAM auth")
    return _rds.generate_db_auth_token(
        DBHostname=settings.DB_HOST,
        Port=int(settings.DB_PORT),
        DBUsername=settings.DB_USER,
    )

def _build_async_url_with_token() -> str:
    pwd = quote_plus(_iam_token())
    host = settings.DB_HOST
    port = int(settings.DB_PORT)
    db   = settings.DB_NAME or ""
    user = settings.DB_USER
    return f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db}"

async def _create_engine_and_factory():
    """Create async engine + sessionmaker. Uses DATABASE_URL if provided, else IAM."""
    global _engine, _SessionLocal

    if settings.DATABASE_URL:
        url = settings.DATABASE_URL
        connect_args = {}
    else:
        url = _build_async_url_with_token()
        # RDS Proxy requires TLS; asyncpg accepts ssl=True
        connect_args = {"ssl": True}

    _engine = create_async_engine(
        url,
        echo=settings.SQLALCHEMY_ECHO,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args=connect_args,
    )

    _SessionLocal = async_sessionmaker(
        bind=_engine, expire_on_commit=False, class_=AsyncSession
    )

async def get_engine():
    global _engine
    if _engine is None:
        async with _engine_lock:
            if _engine is None:
                await _create_engine_and_factory()
    return _engine

async def rotate_engine_every(interval_seconds: int = 600):
    """
    Background task: every N seconds, dispose the engine and recreate it
    so new connections get a fresh IAM token. If DATABASE_URL is set,
    rotation is skipped.
    """
    global _engine
    while True:
        await asyncio.sleep(interval_seconds)
        if settings.DATABASE_URL:
            continue
        async with _engine_lock:
            if _engine is not None:
                await _engine.dispose()
            await _create_engine_and_factory()

# FastAPI dependency (unchanged signature)
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    await get_engine()
    async with _SessionLocal() as session:
        yield session