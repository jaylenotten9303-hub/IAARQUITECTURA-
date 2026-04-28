from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from src.db.database import engine
from src.models.models import Base
from src.routes.solve import router as solve_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ArchiSolve AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(solve_router, prefix="/api/v1")

@app.get("/api/v1/health")
def health():
    return {"status": "ok"}

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(static_dir, "index.html"))

    @app.get("/antigravity")
    def antigravity():
        return FileResponse(os.path.join(static_dir, "antigravity.html"))
