from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import engine
from app.routers import projects

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()  # close pool on shutdown

app = FastAPI(
    title="logima-backed API",
    version="0.1.0",
)

# --- CORS so React can talk to it locally ---
origins = ["http://localhost:5173", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers ---
app.include_router(projects.router)  # this makes /projects/... routes active

# --- Routes -------------------------------------------------
@app.get("/")
def read_root():
    return {"status": "ok"}