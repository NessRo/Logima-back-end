from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import engine
from app.routers import auth, projects
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type","Authorization","X-CSRF-Token"],
)

# --- Register routers ---
app.include_router(projects.router)  # this makes /projects/... routes active
app.include_router(auth.router) # this makes /auth/ routes active

# --- Routes -------------------------------------------------
@app.get("/")
def read_root():
    return {"status": "ok"}