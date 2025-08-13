import os, secrets, jwt, hmac
from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext

from app.config import Settings
settings = Settings()

SECRET_KEY = settings.SECRET_KEY
ALGO = "HS256"
ACCESS_MIN = 60
pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(p: str) -> str: return pwd_ctx.hash(p)
def verify_password(p: str, h: str) -> bool: return pwd_ctx.verify(p, h)

def make_access_token(sub: str, minutes: int = ACCESS_MIN) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({"sub": sub, "exp": exp}, SECRET_KEY, algorithm=ALGO)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGO])

def make_csrf() -> str: return secrets.token_urlsafe(32)