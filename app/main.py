from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from app.database import engine
from app.routers import auth, projects, uploads
from app.config import Settings


settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()  # close pool on shutdown

app = FastAPI(
    title="logima-backed API",
    version="0.1.0",
)



# --- CORS so React can talk to it locally ---
origins = [settings.FRONTEND_ORIGIN]
# CORS first (so browsers can talk to API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
)

# Session middleware for Authlib (stores OAuth state/nonce)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET,
)

# --- Register routers ---
app.include_router(projects.router)  # this makes /projects/... routes active
app.include_router(auth.router) # this makes /auth/ routes active
app.include_router(uploads.router)

# --- Routes -------------------------------------------------
@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/healthz")
def healthz(): return {"ok": True}