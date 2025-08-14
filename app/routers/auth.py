import os
from fastapi import APIRouter, Depends, HTTPException, Response, status,Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app import models, schemas
from app.security import hash_password, verify_password, make_access_token, make_csrf
from app.deps import get_current_user, require_csrf
from authlib.integrations.starlette_client import OAuth


from app.config import Settings
settings = Settings()


router = APIRouter(prefix="/auth", tags=["auth"])

ENV = settings.ENV
SECURE = (ENV == "prod")  # cookies Secure only in prod (HTTPS)
SAMESITE = "Lax"          # Lax is fine for typical web app flows


# --- Google OAuth (OIDC) ---
oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    api_base_url="https://openidconnect.googleapis.com/v1/",
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/google/start")
async def google_start(request: Request):
    # Authlib manages state/nonce via SessionMiddleware
    return await oauth.google.authorize_redirect(request, settings.GOOGLE_REDIRECT_URL)


@router.get("/google/callback", response_model=schemas.TokenOK)
async def google_callback(request: Request, response: Response, db: AsyncSession = Depends(get_session)):
    # Exchange code -> tokens
    token = await oauth.google.authorize_access_token(request)

    # Prefer verified ID token claims (email, sub, etc.)
    # Authlib parses and verifies via Google’s JWKs
    idinfo = None
    try:
        idinfo = await oauth.google.parse_id_token(request, token)
    except KeyError:
        idinfo = None
    

    if not idinfo:
        resp = await oauth.google.get("userinfo", token=token)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch Google userinfo")
        idinfo = resp.json()

    email = (idinfo.get("email") or "").lower()
    email_verified = idinfo.get("email_verified", False)
    if not email or not email_verified:
        raise HTTPException(status_code=400, detail="Google account email not verified")

    # Upsert user by email
    q = await db.execute(select(models.User).where(models.User.email == email))
    user = q.scalar_one_or_none()
    if not user:
        # Create a local user record. If your model requires password_hash, set None or a random string.
        user = models.User(
            email=email,
            password_hash=None,  # oauth user
            # You can add optional fields if your model supports them:
            # provider="google",
            # provider_sub=idinfo.get("sub"),
            # name=idinfo.get("name"),
            # avatar_url=idinfo.get("picture"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Issue your app token + csrf
    token_jwt = make_access_token(sub=str(user.id))
    csrf = make_csrf()

    redirect = RedirectResponse(url=settings.FRONTEND_ORIGIN, status_code=302)
    redirect.set_cookie("access_token", token_jwt, httponly=True, secure=(settings.ENV=="prod"),
                        samesite="Lax", path="/", max_age=15*60)
    redirect.set_cookie("csrf_token", csrf, httponly=False, secure=(settings.ENV=="prod"),
                        samesite="Strict", path="/", max_age=15*60)
    return redirect


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

