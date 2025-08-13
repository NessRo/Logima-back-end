import os
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app import models, schemas
from app.security import hash_password, verify_password, make_access_token, make_csrf
from app.deps import get_current_user, require_csrf


from app.config import Settings
settings = Settings()


router = APIRouter(prefix="/auth", tags=["auth"])

ENV = settings.ENV
SECURE = (ENV == "prod")  # cookies Secure only in prod (HTTPS)
SAMESITE = "Lax"          # Lax is fine for typical web app flows

@router.post("/register", response_model=schemas.UserOut, status_code=201)
async def register(payload: schemas.UserCreate, db: AsyncSession = Depends(get_session)):
    email = payload.email.lower()
    q = await db.execute(select(models.User).where(models.User.email == email))
    if q.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(email=email, password_hash=hash_password(payload.password))
    db.add(user); await db.commit(); await db.refresh(user)
    return user

@router.post("/login", response_model=schemas.TokenOK)
async def login(payload: schemas.LoginIn, response: Response, db: AsyncSession = Depends(get_session)):
    email = payload.email.lower()
    q = await db.execute(select(models.User).where(models.User.email == email))
    user = q.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = make_access_token(sub=str(user.id))
    csrf = make_csrf()

    response.set_cookie("access_token", token, httponly=True, secure=SECURE, samesite=SAMESITE, path="/", max_age=15*60)
    response.set_cookie("csrf_token", csrf, httponly=False, secure=SECURE, samesite="Strict", path="/", max_age=15*60)
    return {"ok": True}

@router.post("/logout", response_model=schemas.TokenOK)
async def logout(response: Response):
    # clear cookies
    for k in ("access_token", "csrf_token"):
        response.delete_cookie(k, path="/")
    return {"ok": True}

@router.get("/me", response_model=schemas.UserOut)
async def me(user=Depends(get_current_user)):
    return user