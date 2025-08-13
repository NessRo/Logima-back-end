import os, hmac
from fastapi import Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.database import get_session
from app.security import decode_access_token
from app import models

async def get_current_user(request: Request, db: AsyncSession = Depends(get_session)) -> models.User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_access_token(token)
        uid = UUID(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    q = await db.execute(select(models.User).where(models.User.id == uid))
    user = q.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_csrf(request: Request, x_csrf_token: str = Header(None)):
    cookie = request.cookies.get("csrf_token")
    if not cookie or not x_csrf_token or not hmac.compare_digest(cookie, x_csrf_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")